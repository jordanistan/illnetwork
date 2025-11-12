import os
import smtplib
import ssl
from email.message import EmailMessage
import requests

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", ALERT_EMAIL_TO or "alerts@example.local")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "true").lower() == "true"

def send_slack(text: str):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
    except Exception:
        pass  # don't crash on alert failures

def send_email(subject: str, body: str):
    if not (SMTP_HOST and ALERT_EMAIL_TO):
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ALERT_EMAIL_TO
    msg.set_content(body)

    context = ssl.create_default_context()
    if SMTP_STARTTLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls(context=context)
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as s:
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)

def notify(subject: str, body: str):
    send_slack(f"*{subject}*\n{body}")
    send_email(subject, body)
