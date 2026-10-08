import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pytz
import streamlit as st
from database import supabase, get_job_items

IST = pytz.timezone("Asia/Kolkata")


def send_ceo_daily_report():
    """Generates and dispatches daily operations report to the CEO via Gmail SMTP."""
    if "ceo_email" not in st.secrets:
        return False, "Missing [ceo_email] section in Streamlit Secrets."

    secrets = st.secrets["ceo_email"]
    smtp_server = secrets.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(secrets.get("smtp_port", 587))
    sender_email = secrets.get("sender_email")
    sender_password = secrets.get("sender_password")
    ceo_recipient = secrets.get("ceo_recipient")

    if not all([smtp_server, smtp_port, sender_email, sender_password, ceo_recipient]):
        return False, "Incomplete CEO email credentials in Streamlit Secrets."

    # 1. Fetch live jobs data
    try:
        j_res = supabase.table("jobs").select("*").order("job_id", desc=True).execute()
        jobs = j_res.data or []
        i_res = supabase.table("job_items").select("*").execute()
        items = i_res.data or []
    except Exception as e:
        return False, f"Failed to retrieve database records: {e}"

    active_jobs = [j for j in jobs if j.get("current_stage") != "SETTLED"]
    settled_jobs = [j for j in jobs if j.get("current_stage") == "SETTLED"]
    returned_jobs = [j for j in jobs if j.get("is_returned")]
    total_pipeline_val = sum(float(it.get("amount", 0) or 0) for it in items)

    now_str = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p")

    # 2. Build HTML Email Body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #222; }}
            .card {{ background: #f8f9fa; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; font-size: 13px; }}
            th {{ background: #23272d; color: #fff; }}
            .badge-ret {{ color: #d9534f; font-weight: bold; }}
            .metric {{ font-size: 18px; font-weight: bold; color: #0275d8; }}
        </style>
    </head>
    <body>
        <h2>🖨️ AdNet Operations Daily Floor Report</h2>
        <p>Report Generated: <strong>{now_str} IST</strong></p>

        <div class="card">
            <h3>Floor Velocity Snapshot</h3>
            <p>Active Orders on Floor: <span class="metric">{len(active_jobs)}</span></p>
            <p>QC Return / Defect Jobs: <span class="metric">{len(returned_jobs)}</span></p>
            <p>Settled & Closed Orders: <span class="metric">{len(settled_jobs)}</span></p>
            <p>Total Pipeline Value: <span class="metric">₹ {total_pipeline_val:,.2f}</span></p>
        </div>

        <h3>Active Jobs on Floor</h3>
        <table>
            <tr>
                <th>Job #</th>
                <th>Client</th>
                <th>Stage</th>
                <th>Target Due Date</th>
                <th>Booked By</th>
                <th>Status</th>
            </tr>
    """

    for j in active_jobs[:25]:
        ret_tag = f"<span class='badge-ret'>⚠️ RETURN ({j.get('return_reason')})</span>" if j.get("is_returned") else "Normal"
        html_body += f"""
            <tr>
                <td>{j.get('job_no')}</td>
                <td>{j.get('client_name')}</td>
                <td>{j.get('current_stage')}</td>
                <td>{j.get('due_date')}</td>
                <td>{j.get('order_taken_by') or 'N/A'}</td>
                <td>{ret_tag}</td>
            </tr>
        """

    html_body += """
        </table>
        <p style="margin-top: 25px; font-size: 12px; color: #777;">Sent automatically by AdNet Operations ERP Portal.</p>
    </body>
    </html>
    """

    # 3. Send Email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AdNet Operations Summary — {datetime.now(IST).strftime('%d %b %Y')}"
    msg["From"] = sender_email
    msg["To"] = ceo_recipient
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [ceo_recipient], msg.as_string())
        server.quit()
        return True, f"Report sent to {ceo_recipient} successfully."
    except Exception as e:
        return False, f"SMTP delivery failed: {e}"