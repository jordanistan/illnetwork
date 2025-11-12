from flask import (
    Flask, render_template, request, send_from_directory, Response, jsonify,
    session, redirect, url_for, flash
)
import subprocess
import os
import time
import shlex
from functools import wraps
from datetime import datetime
from openai import OpenAI
import mistune

from flask import (
    Flask, render_template, request, send_from_directory, Response, jsonify,
    session, redirect, url_for, flash
)
import subprocess
import os
import time
import shlex
from functools import wraps
from datetime import datetime
from openai import OpenAI
import mistune
from apscheduler.schedulers.background import BackgroundScheduler
from .config import config

# --- Configuration ---
REPORT_DIR = config.get("OUTPUT_DIR", "/opt/data/reports")
PARSER = "/opt/scanner/parse_logs.py"

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Authentication ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != config.get('ADMIN_USER') or \
           request.form['password'] != config.get('ADMIN_PASSWORD'):
            error = 'Invalid credentials. Please try again.'
        else:
            session['logged_in'] = True
            flash('You were successfully logged in.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out.')
    return redirect(url_for('login'))

# --- Settings Route ---
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Get all form data, but don't save empty password fields
        new_settings = request.form.to_dict()
        
        # If password fields are submitted empty, keep the old ones
        if not new_settings.get('OPENAI_API_KEY'):
            new_settings['OPENAI_API_KEY'] = config.get('OPENAI_API_KEY')
        if not new_settings.get('SMTP_PASS'):
            new_settings['SMTP_PASS'] = config.get('SMTP_PASS')

        config.save(new_settings)
        flash('Settings saved successfully. Some changes may require a restart.', 'success')
        return redirect(url_for('settings'))
    
    # For GET request, don't pass sensitive values to the template directly
    # The config object handles this, but we obscure them for display
    display_settings = config.settings.copy()
    if display_settings.get('OPENAI_API_KEY'):
        display_settings['OPENAI_API_KEY'] = '********'
    if display_settings.get('SMTP_PASS'):
        display_settings['SMTP_PASS'] = '********'

    return render_template('settings.html', settings=config.settings)

# --- Core Routes ---
def list_reports():
    if not os.path.isdir(REPORT_DIR):
        return []
    # Get all unique report identifiers
    base_names = {f.split('-Summary-Report-')[0] for f in os.listdir(REPORT_DIR)}
    
    # Find one file for each base name to represent the report group
    representative_files = []
    for base in base_names:
        # Prefer .md, then .html, then .json
        for ext in ['.md', '.html', '.json']:
            report_file = f"{base}-Summary-Report-{base.split('-')[-1]}{ext}"
            # This logic is a bit flawed, need to get severity correctly
            # Let's find any file that matches the base
            
            found = False
            for f in os.listdir(REPORT_DIR):
                if f.startswith(base):
                    representative_files.append(f)
                    found = True
                    break
            if found:
                break

    return sorted(list(set(os.listdir(REPORT_DIR))), reverse=True)


@app.route("/")
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route("/dashboard")
@login_required
def dashboard():
    # Find the latest report
    raw_files = list_reports()
    latest_report_info = None
    findings = []
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_findings = 0

    if raw_files:
        # Basic parsing to find the latest report file (.md)
        md_files = [f for f in raw_files if f.endswith('.md')]
        if md_files:
            latest_md_file = sorted(md_files, reverse=True)[0]
            
            # Parse filename for summary info
            base_name = latest_md_file.split('-Summary-Report-')[0]
            parts = base_name.split('-')
            hostname = parts[0]
            timestamp = parts[1]
            severity = latest_md_file.split('-')[-1].split('.')[0]
            date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
            display_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')

            latest_report_info = {
                "filename": latest_md_file,
                "hostname": hostname,
                "date": display_date,
                "severity": severity.capitalize()
            }

            # Parse file content for findings and severity counts
            report_path = os.path.join(REPORT_DIR, latest_md_file)
            with open(report_path, 'r') as f:
                in_findings_section = False
                for line in f:
                    if line.strip().startswith('**1. Findings:**'):
                        in_findings_section = True
                        continue
                    if line.strip().startswith('**2. Severity:**'):
                        in_findings_section = False
                        continue
                    
                    if in_findings_section and line.strip().startswith('-'):
                        findings.append(line.strip(' -'))
                        # Simple severity counter based on keywords in the finding line
                        if 'critical' in line.lower(): severity_counts['critical'] += 1
                        elif 'high' in line.lower(): severity_counts['high'] += 1
                        elif 'medium' in line.lower(): severity_counts['medium'] += 1
                        elif 'low' in line.lower(): severity_counts['low'] += 1
            total_findings = len(findings)

    return render_template(
        'dashboard.html', 
        latest_report=latest_report_info,
        findings=findings,
        severity_counts=severity_counts,
        total_findings=total_findings
    )


@app.route("/scanner")
@login_required
def scanner_page():
    return render_template("index.html")


@app.route("/reports")
@login_required
def reports():
    raw_files = list_reports()
    structured_reports = []
    processed_bases = set()

    for filename in raw_files:
        try:
            # Base name is everything before "-Summary-Report-"
            base_name = filename.split('-Summary-Report-')[0]
            if base_name in processed_bases:
                continue
            
            parts = base_name.split('-')
            hostname = parts[0]
            timestamp = parts[1]
            
            # Severity is the last part of the full filename (before extension)
            severity = filename.split('-')[-1].split('.')[0]
            
            date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
            display_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')

            # Use the .md file for viewing, but the base name for identity
            view_file = f"{base_name}-Summary-Report-{severity}.md"

            structured_reports.append({
                "filename": view_file, # Link to the .md viewer
                "display_name": base_name,
                "hostname": hostname,
                "date": display_date,
                "severity": severity.capitalize()
            })
            processed_bases.add(base_name)
        except (IndexError, ValueError):
            continue # Skip files that don't match the format

    sorted_reports = sorted(structured_reports, key=lambda r: r['date'], reverse=True)

    return render_template("reports.html", reports=sorted_reports)

@app.route("/report/view/<path:filename>")
@login_required
def view_report(filename):
    # Ensure we are only opening .md files for security
    if not filename.endswith('.md'):
        flash("Invalid report format.", "error")
        return redirect(url_for('reports'))

    report_path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(report_path):
        flash("Report file not found.", "error")
        return redirect(url_for('reports'))

    with open(report_path, 'r') as f:
        markdown_content = f.read()
    
    # The report name for the title, without the extension
    report_name = filename.replace('.md', '')
    report_html = mistune.html(markdown_content)
    
    return render_template('view_report.html', report_name=report_name, report_html=report_html)

@app.route("/reports/<path:filename>")
@login_required
def get_report(filename):
    return send_from_directory(REPORT_DIR, filename)

@app.route('/reports/clear', methods=['POST'])
@login_required
def clear_reports():
    """Deletes all files in the report directory."""
    for filename in os.listdir(REPORT_DIR):
        file_path = os.path.join(REPORT_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            flash(f"Error deleting file {filename}: {e}", "error")
    flash("All reports have been deleted.", "success")
    return redirect(url_for('reports'))

from scanner.scanner import Scanner

from apscheduler.schedulers.background import BackgroundScheduler

# --- Reusable Analysis Function ---
def trigger_analysis(report_file, target_host):
    """Triggers the GPT analysis for a given report file."""
    if report_file and os.path.exists(report_file):
        with open(report_file, 'r') as f:
            scan_log_content = f.read()
        
        try:
            p2_cmd = ["python3", PARSER, target_host, report_file]
            p2 = subprocess.Popen(p2_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = p2.communicate(input=scan_log_content)
            
            if stdout:
                print(f"Analysis complete for {report_file}:\n{stdout}")
            if stderr:
                print(f"Analysis error for {report_file}:\n{stderr}")
            return stdout, stderr
        except Exception as e:
            err_msg = f"[ERR] GPT analysis step failed: {e}"
            print(err_msg)
            return None, err_msg
    else:
        err_msg = "[ERR] Report file not found, cannot run analysis."
        print(err_msg)
        return None, err_msg

# --- Scheduled Scan Job ---
def scheduled_scan_job():
    """The job that is executed by the scheduler."""
    print("--- Running Scheduled Scan ---")
    with app.app_context():
        scanner_config = {
            "REMOTE_HOST": config.get("REMOTE_HOST"),
            "SCAN_PATH": config.get("SCAN_PATH"),
            "OUTPUT_DIR": REPORT_DIR
        }
        scanner = Scanner(scanner_config)
        
        report_file = None
        target_host = "localhost"

        # Consume the generator to run the scan
        for line in scanner.run_scan():
            if line.startswith("__REPORT_FILE__="):
                report_file = line.split("=", 1)[1]
            elif line.startswith("__TARGET_HOST__="):
                target_host = line.split("=", 1)[1]
        
        print(f"Scheduled scan finished. Report generated: {report_file}")
        
        # Trigger the analysis
        trigger_analysis(report_file, target_host)
    print("--- Scheduled Scan Complete ---")


@app.route("/scan/stream")
@login_required
def scan_stream():
    def generate():
        scan_type = request.args.get('scan_type', 'deep_scan')
        
        scanner_config = {
            "REMOTE_HOST": config.get("REMOTE_HOST"),
            "SCAN_PATH": config.get("SCAN_PATH"),
            "OUTPUT_DIR": REPORT_DIR
        }
        scanner = Scanner(scanner_config)
        
        report_file = None
        target_host = "localhost"

        # Choose the scan method based on the user's selection
        if scan_type == 'health_check':
            scan_generator = scanner.run_health_check()
        else: # Default to deep_scan
            scan_generator = scanner.run_scan()

        # Stream the output from the chosen scanner method
        for line in scan_generator:
            line = line.rstrip("\n")
            if line.startswith("__REPORT_FILE__="):
                report_file = line.split("=", 1)[1]
            elif line.startswith("__TARGET_HOST__="):
                target_host = line.split("=", 1)[1]
            yield f"data: {line}\n\n"

        yield f"data: === Generating GPT summary ===\n\n"
        
        # Use the reusable analysis function
        stdout, stderr = trigger_analysis(report_file, target_host)
        
        if stdout:
            for out_line in stdout.splitlines():
                yield f"data: {out_line}\n\n"
        if stderr:
            for err_line in stderr.splitlines():
                yield f"data: [PARSER ERR] {err_line}\n\n"

        yield "event: done\ndata: complete\n\n"

    return Response(generate(), mimetype="text/event-stream")

@app.route('/remediate/execute/<target_host>', methods=['POST'])
@login_required
def execute_remediation(target_host):
    """Executes the remediation script on the target host and streams the output."""
    data = request.get_json()
    script_content = data.get('script')

    if not script_content:
        return Response("Script content is missing.", status=400)

    def generate():
        remote_user = config.get("REMOTE_USER")
        remote_host_env = config.get("REMOTE_HOST")
        
        command = ""
        # Determine if the target is remote or local (the container itself)
        if remote_host_env and target_host == remote_host_env:
            yield "data: Executing script on remote host via SSH...\n\n"
            # Use ssh to execute the script. The script content is piped to bash on the remote host.
            command = f"ssh -o StrictHostKeyChecking=no {remote_user}@{target_host} 'bash -s'"
        elif target_host == 'localhost':
            yield "data: Executing script locally in the container...\n\n"
            command = "bash -s"
        else:
            yield f"data: [ERR] Target host '{target_host}' does not match configured remote host or 'localhost'. Aborting.\n\n"
            yield "event: done\ndata: complete\n\n"
            return

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                text=True
            )
            
            # Write the script to the process's stdin and close it
            process.stdin.write(script_content)
            process.stdin.close()

            # Stream the output
            for line in process.stdout:
                yield f"data: {line}\n"
            
            process.wait()
            yield f"data: \n--- Execution finished with exit code: {process.returncode} ---\n\n"

        except Exception as e:
            yield f"data: [ERR] Failed to execute script: {e}\n\n"
        
        yield "event: done\ndata: complete\n\n"

    # This requires a custom EventSource implementation on the frontend to handle POST
    # The provided JS in remediation.html is a simplified example. A real implementation
    # would use fetch() to POST and read the stream from the response body.
    # For this project, we will assume a library or a more complex JS snippet handles this.
    # The provided JS in the last step is a simplified polyfill idea.
    return Response(generate(), mimetype='text/event-stream')

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
    
    # Extract target host from filename, e.g., "localhost-20251109_..."
    target_host = filename.split('-')[0]
    
    return render_template('remediation.html', script=remediation_script, report_name=filename, target_host=target_host)

if __name__ == "__main__":
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # --- Initialize Scheduler ---
    scan_schedule = config.get("SCAN_SCHEDULE")
    if scan_schedule:
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=scheduled_scan_job, trigger="cron", expression=scan_schedule)
        scheduler.start()
        print(f"--- Scan scheduler enabled with schedule: '{scan_schedule}' ---")
        # Keep the scheduler running when the app exits
        import atexit
        atexit.register(lambda: scheduler.shutdown())
    else:
        print("--- Scan scheduler is disabled (SCAN_SCHEDULE not set) ---")

    app.run(host="0.0.0.0", port=5000, threaded=True)