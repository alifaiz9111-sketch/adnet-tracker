import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pytz
import streamlit as st
from database import supabase

IST = pytz.timezone("Asia/Kolkata")


def send_ceo_daily_report():
    """Generates and dispatches daily operations report to the CEO via Gmail SMTP."""
    if "ceo_email" not in st.secrets:
        return False, "Missing [ceo_email] section in Streamlit Secrets."

    secrets = st.secrets["ceo_email"]
    smtp_server = secrets.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(secrets.get("smtp_port", 587))
    sender_email = secrets.get("sender_email")
    sender_password = str(secrets.get("sender_password", "")).replace(" ", "").strip()
    ceo_recipient = secrets.get("ceo_recipient")

    if not all([smtp_server, smtp_port, sender_email, sender_password, ceo_recipient]):
        return False, "Incomplete CEO email credentials in Streamlit Secrets."

    try:
        j_res = supabase.table("jobs").select("*").order("job_id", desc=True).execute()
        jobs = j_res.data or []
        i_res = supabase.table("job_items").select("*").execute()
        items = i_res.data or []
    except Exception as e:
        return False, "Failed to retrieve database records: " + str(e)

    active_jobs = [j for j in jobs if j.get("current_stage") != "SETTLED"]
    settled_jobs = [j for j in jobs if j.get("current_stage") == "SETTLED"]
    returned_jobs = [j for j in jobs if j.get("is_returned")]
    total_val = sum(float(it.get("amount", 0) or 0) for it in items)

    ret_color = "#d9534f" if len(returned_jobs) > 0 else "#28a745"
    now_str = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p")

    # Table rows generator
    table_rows = ""
    for j in active_jobs[:30]:
        status_tag = '<span style="color:#d9534f;font-weight:bold;">RETURN: ' + str(j.get("return_reason", "")) + '</span>' if j.get("is_returned") else "Normal"
        table_rows += (
            "<tr>"
            "<td><strong>#" + str(j.get("job_no", "")) + "</strong></td>"
            "<td>" + str(j.get("client_name", "")) + "</td>"
            "<td>" + str(j.get("current_stage", "")) + "</td>"
            "<td>" + str(j.get("due_date", "")) + "</td>"
            "<td>" + str(j.get("order_taken_by", "N/A")) + "</td>"
            "<td>" + status_tag + "</td>"
            "</tr>"
        )

    if not active_jobs:
        table_html = "<p><em>No active jobs currently on the floor.</em></p>"
    else:
        table_html = (
            "<table border='1' cellpadding='8' cellspacing='0' style='border-collapse:collapse;width:100%;margin-top:15px;font-size:13px;'>"
            "<tr style='background:#1a1e24;color:#ffffff;text-align:left;'>"
            "<th>Job #</th><th>Client</th><th>Stage</th><th>Due Date</th><th>Order Taken By</th><th>Status</th>"
            "</tr>"
            + table_rows +
            "</table>"
        )

    html_content = (
        "<html><body style='font-family:Arial,sans-serif;color:#222;padding:15px;'>"
        "<h2>AdNet Operations Floor Report</h2>"
        "<p>Generated: <strong>" + now_str + " IST</strong></p>"
        "<div style='background:#f4f6f9;border:1px solid #dcdfe6;padding:15px;border-radius:8px;margin-bottom:20px;'>"
        "<h3 style='margin-top:0;'>Floor Velocity Snapshot</h3>"
        "<p>Active Orders on Floor: <strong>" + str(len(active_jobs)) + "</strong></p>"
        "<p>QC Defect / Returns: <strong style='color:" + ret_color + ";'>" + str(len(returned_jobs)) + "</strong></p>"
        "<p>Settled Orders: <strong>" + str(len(settled_jobs)) + "</strong></p>"
        "<p>Total Pipeline Value: <strong>₹ " + f"{total_val:,.2f}" + "</strong></p>"
        "</div>"
        "<h3>Active Jobs on Floor</h3>"
        + table_html +
        "<p style='margin-top:25px;font-size:11px;color:#888;'>Sent automatically by AdNet Operations ERP Portal.</p>"
        "</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "AdNet Floor Operations Summary — " + datetime.now(IST).strftime("%d %b %Y")
    msg["From"] = sender_email
    msg["To"] = ceo_recipient
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.ehlo()
        if smtp_port == 587:
            server.starttls()
            server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [ceo_recipient], msg.as_string())
        server.quit()
        return True, "Floor report delivered to " + ceo_recipient + " successfully!"
    except Exception as e:
        return False, "SMTP delivery failed: " + str(e)


def send_new_jobsheet_alert(job_payload, items_data):
    """Sends an instant alert to the CEO whenever a new jobsheet is created."""
    if "ceo_email" not in st.secrets:
        return False, "Missing [ceo_email] section."

    secrets = st.secrets["ceo_email"]
    smtp_server = secrets.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(secrets.get("smtp_port", 587))
    sender_email = secrets.get("sender_email")
    sender