import os
import datetime
import json
import re
import sys
from openai import OpenAI

from alerts import notify

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REPORT_DIR = os.environ.get("OUTPUT_DIR", "/opt/data/reports")
ALERT_SEVERITY_THRESHOLD = os.getenv("ALERT_SEVERITY_THRESHOLD", "high").lower()  # low|medium|high|critical

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

def extract_simple_indicators(scan_text: str):
    # ClamAV infections
    infected = len(re.findall(r"\bFOUND\b", scan_text))
    # rkhunter warnings
    rk_warn = len(re.findall(r"\bWarning\b", scan_text, flags=re.IGNORECASE))
    # Credential hits (we prefixed with CRED:)
    cred_hits = len(re.findall(r"^CRED:", scan_text, flags=re.MULTILINE))
    return infected, rk_warn, cred_hits

def gpt_summary(scan_text: str):
    if not OPENAI_API_KEY:
        return "OpenAI API key not set. Skipping GPT summary."
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""
You are an expert cybersecurity analyst creating a clear, actionable security report.
Analyze the following scan results and generate a detailed report with the five sections below.

**1. Findings:**
A bulleted list of all discovered issues (e.g., open ports, outdated software, vulnerabilities).

**2. Severity:**
A severity rating for each finding (Low, Medium, High, Critical).

**3. How to Fix (Actionable Steps):**
For each finding, provide specific, copy-pasteable shell commands to fix the issue. Assume the user has sudo privileges.
- **OS Context:** Base your commands on the operating system detected in the scan log (e.g., Ubuntu, CentOS). If the OS is not specified, provide commands for Ubuntu/Debian as a default.
- **Example for an outdated package:**
  ```
  # To update Apache on Ubuntu/Debian:
  sudo apt-get update
  sudo apt-get install --only-upgrade apache2
  ```

**4. How to Prevent:**
Recommend policies or configuration changes to prevent these issues from recurring.

**5. High-Level Summary:**
A brief, non-technical summary for managers or non-technical users.

**Scan Log to Analyze:**
```
{scan_text}
```
"""
    resp = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content

def save_reports(summary: str, base_filename: str):
    md_file = os.path.join(REPORT_DIR, base_filename + ".md")
    html_file = os.path.join(REPORT_DIR, base_filename + ".html")
    json_file = os.path.join(REPORT_DIR, base_filename + ".json")

    with open(md_file, "w") as f:
        f.write(summary)

    html_content = f"<html><head><meta charset='utf-8'></head><body><pre>{summary}</pre></body></html>"
    with open(html_file, "w") as f:
        f.write(html_content)

    with open(json_file, "w") as f:
        json.dump({"report": summary}, f, indent=2)

    return md_file, html_file, json_file

def derive_overall_severity(summary_text: str, infected: int, rk_warn: int) -> str:
    # Use heuristics + summary keywords
    sev = "low"
    if infected > 0 or rk_warn > 0:
        sev = "high" if infected == 0 else "critical"
    # Try to upgrade based on GPT text
    if re.search(r"\bCritical\b", summary_text, re.IGNORECASE):
        sev = "critical"
    elif re.search(r"\bHigh\b", summary_text, re.IGNORECASE):
        sev = max(sev, "high", key=lambda s: SEVERITY_ORDER[s])
    elif re.search(r"\bMedium\b", summary_text, re.IGNORECASE):
        sev = max(sev, "medium", key=lambda s: SEVERITY_ORDER[s])
    return sev

if __name__ == "__main__":
    hostname = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    report_file = sys.argv[2] if len(sys.argv) > 2 else ""
    
    scan_text = sys.stdin.read()
    
    if not scan_text:
        print("Scan log was empty. Aborting analysis.")
        exit(1)

    infected, rk_warn, cred_hits = extract_simple_indicators(scan_text)
    summary = gpt_summary(scan_text)
    
    # Derive severity before creating the filename
    overall = derive_overall_severity(summary, infected, rk_warn)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base_filename = f"{hostname}-{timestamp}-Summary-Report-{overall}"
    
    md_file, html_file, json_file = save_reports(summary, base_filename)

    threshold_ok = SEVERITY_ORDER.get(overall, 1) >= SEVERITY_ORDER.get(ALERT_SEVERITY_THRESHOLD, 3)

    if threshold_ok:
        body = (
            f"Overall severity: {overall.upper()}\n"
            f"Infected files: {infected}\n"
            f"rkhunter warnings: {rk_warn}\n"
            f"Credential hits: {cred_hits}\n\n"
            f"Scan log: {report_file}\n"
            f"Reports:\n- {md_file}\n- {html_file}\n- {json_file}\n"
        )
        notify(f"Homelab Security Alert [{hostname}]", body)

    print(f"Reports saved:\n- {md_file}\n- {html_file}\n- {json_file}")
    print(f"Overall severity: {overall}")
