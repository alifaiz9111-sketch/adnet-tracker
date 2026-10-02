import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

def send_ceo_email(subject, html_content):
    try:
        conf = st.secrets["ceo_email"]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = conf["sender_email"]
        msg["To"] = conf["ceo_recipient"]

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(conf["smtp_server"], int(conf["smtp_port"])) as server:
            server.starttls()
            server.login(conf["sender_email"], conf["sender_password"])
            server.sendmail(conf["sender_email"], conf["ceo_recipient"], msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def notify_ceo_new_job(job_no, client_name, total_val, order_taker, due_date):
    subject = f"🔔 [NEW JOB] #{job_no} created for {client_name}"
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2563EB;">New Job Sheet Created</h2>
        <p>A new job card has just been entered into the system:</p>
        <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Job Number:</b></td><td style="padding: 8px; border: 1px solid #ddd;">#{job_no}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Client:</b></td><td style="padding: 8px; border: 1px solid #ddd;">{client_name}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Total Booking Value:</b></td><td style="padding: 8px; border: 1px solid #ddd;">₹ {total_val:,.2f}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Order Taken By:</b></td><td style="padding: 8px; border: 1px solid #ddd;">{order_taker}</td></tr>
          <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Due Date:</b></td><td style="padding: 8px; border: 1px solid #ddd;">{due_date}</td></tr>
        </table>
        <p style="margin-top: 20px; font-size: 12px; color: #777;">Adnet Workflow ERP Automated Notification</p>
      </body>
    </html>
    """
    return send_ceo_email(subject, html)