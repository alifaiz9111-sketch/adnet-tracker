import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pytz
import streamlit as st
from database import supabase

IST = pytz.timezone("Asia/Kolkata")

def send_ceo_daily_report():
    """Diagnostic SMTP test with verbose logs."""
    # 1. Check Secrets
    if "ceo_email" not in st.secrets:
        return False, "❌ Missing [ceo_email] header in Streamlit Secrets."

    secrets = st.secrets["ceo_email"]
    smtp_server = secrets.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(secrets.get("smtp_port", 587))
    sender_email = secrets.get("sender_email")
    sender_password = secrets.get("sender_password", "").replace(" ", "").strip()
    ceo_recipient = secrets.get("ceo_recipient")

    # Diagnostic credential check
    if not sender_email or not sender_password or not ceo_recipient:
        return False, f"❌ Incomplete secrets: sender={bool(sender_email)}, pwd={bool(sender_password)}, recipient={bool(ceo_recipient)}"

    # 2. Test Connection & Authentication Step-by-Step
    try:
        # Step A: Connect to host
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()

        # Step B: Secure connection
        if smtp_port == 587:
            server.starttls()
            server.ehlo()

        # Step C: Login
        server.login(sender_email, sender_password)

        # Step D: Compose Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"AdNet Test Report — {datetime.now(IST).strftime('%d %b %Y, %I:%M %p')}"
        msg["From"] = sender_email
        msg["To"] = ceo_recipient

        body_html = f"""
        <html>
            <body>
                <h2 style="color: #2b74da;">🖨️ AdNet Live SMTP Test Successful</h2>
                <p>Connected via: <code>{smtp_server}:{smtp_port}</code></p>
                <p>Sender: <code>{sender_email}</code></p>
                <p>Recipient: <code>{ceo_recipient}</code></p>
                <p>Timestamp: <strong>{datetime.now(IST).strftime('%d-%b-%Y %I:%M:%S %p')} IST</strong></p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body_html, "html"))

        # Step E: Send
        server.sendmail(sender_email, [ceo_recipient], msg.as_string())
        server.quit()
        return True, f"✅ Test email successfully delivered to {ceo_recipient}!"

    except smtplib.SMTPAuthenticationError as auth_err:
        return False, f"❌ Authentication Failed: {auth_err.smtp_error.decode('utf-8', errors='ignore')}. Ensure you are using a 16-character Google App Password (not your normal Gmail account password)."
    except smtplib.SMTPConnectError as conn_err:
        return False, f"❌ Failed to connect to SMTP server: {conn_err}"
    except Exception as e:
        return False, f"❌ Unexpected Mail Error: {type(e).__name__} - {e}"