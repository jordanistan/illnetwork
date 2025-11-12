from flask import (
    Flask, render_template, request, send_from_directory, Response, jsonify,
    session, redirect, url_for, flash
)
import subprocess
import os
import time
import shlex
from functools import wraps
from openai import OpenAI

REPORT_DIR = os.environ.get("OUTPUT_DIR", "/opt/data/reports")
SCANNER = "/opt/scanner/scan.sh"
PARSER = "/opt/scanner/parse_logs.py"
...
def api_reports():
    return jsonify(list_reports())

def generate_remediation_script(report_content: str) -> str:
    """Calls OpenAI API to generate a remediation script from a report."""
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        return "# OpenAI API key not set. Cannot generate script."

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""
You are an expert system administrator and security professional.
Based on the following security report findings, generate a comprehensive shell script that will attempt to remediate the issues.

**Guidelines for the script:**
1.  **Idempotent:** The script should be safe to run multiple times. Use checks like `if ! command -v ...` before installing packages.
2.  **Non-Interactive:** The script must run without any user prompts. Use flags like `-y` for package managers.
3.  **Error Checking:** Use `set -e` to stop the script if a command fails.
4.  **Comments:** Add comments to explain each remediation step.
5.  **OS Specific:** Use the operating system mentioned in the report to generate the correct commands (e.g., `apt-get` for Ubuntu).

**Security Report Findings:**
```
{report_content}
```

**Output:**
Provide ONLY the shell script, starting with `#!/bin/bash` and nothing else.
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"# Error generating script: {e}"

@app.route('/report/<path:filename>/remediate', methods=['POST'])
@login_required
def remediate_report(filename):
    """Generates a remediation script for a given report."""
    report_path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(report_path):
        flash("Report file not found.", "error")
        return redirect(url_for('reports'))

    with open(report_path, 'r') as f:
        report_content = f.read()
    
    remediation_script = generate_remediation_script(report_content)
    
    return render_template('remediation.html', script=remediation_script, report_name=filename)


if __name__ == "__main__":
    os.makedirs(REPORT_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, threaded=True)
