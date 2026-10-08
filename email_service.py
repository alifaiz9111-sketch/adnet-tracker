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
    sender_password = secrets.get("sender_password", "").replace(" ", "").strip()
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

    ret_color = "#d9534f" if len(returned_jobs) > 0 else "#28a745"
    now_str = datetime.now(IST).strftime("%d-%b-%Y %I:%M %p")

    # 2. Build HTML Email Body
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; color: #222; margin: 0; padding: 15px; }}
            .card {{ background: #f4f6f9; border: 1px solid #dcdfe6; padding: 16px; border-radius: 8px; margin-bottom: 20px; }}
            .metric-box {{ display: inline-block; width: 45%; margin-bottom: 10px; }}
            .metric-val {{ font-size: 20px; font-weight: bold; color: #1f6feb; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
            th, td {{ border: 1px solid #dcdfe6; padding: 10px; text-align: left; font-size: 13px; }}
            th {{ background: #1a1e24; color: #ffffff; }}
            tr:nth-child(even) {{ background-color: #f9fafb; }}
            .badge-ret {{ color: #d9534f; font-weight: bold; }}
            .badge-stage {{ background: #e1ecf4; color: #0c5460; padding: 3px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>🖨️ AdNet Operations Floor Report</h2>
        <p>Generated: <strong>{now_str} IST</strong></p>

        <div class="card">
            <h3 style="margin-top: 0;">Floor Velocity Snapshot</h3>
            <div class="metric-box">
                <div>Active Floor Orders</div>
                <div class="metric-val">{len(active_jobs)}</div>
            </div>
            <div class="metric-box">
                <div>QC Defect / Returns</div>
                <div class="metric-val" style="color: {ret_color};">{len(returned_jobs)}</div>
            </div>
            <div class="metric-box">
                <div>Settled Orders</div>
                <div class="metric-val">{len(settled_jobs)}</div>
            </div>
            <div class="metric-box">
                <div>Total Pipeline Value</div>
                <div class="metric-val">₹ {total_pipeline_val:,.2f}</div>
            </div>
        </div>

        <h3>Active Jobs on Floor</h3>
    """

    if not active_jobs:
        html_body += "<p><em>No active jobs currently on the floor.</em></p>"
    else:
        html_body += """
        <table>
            <thead>
                <tr>
                    <th>Job #</th>
                    <th>Client Name</th>
                    <th>Stage</th>
                    <th>Due Date</th>
                    <th>Order Taken By</th>
                    <th>Notes / Status</th>
                </tr>