import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st
from database import supabase, get_job_items

# 1. Resolve credentials directly from [ceo_email] in st.secrets
if "ceo_email" in st.secrets:
    SMTP_SERVER = st.secrets["ceo_email"].get("smtp_server", "smtp.gmail.com")
    SMTP_PORT = int(st.secrets["ceo_email"].get("smtp_port", 587))
    SMTP_EMAIL = st.secrets["ceo_email"].get("sender_email", "")
    SMTP_PASSWORD = st.secrets["ceo_email"].get("sender_password", "")
    CEO_RECIPIENT = st.secrets["ceo_email"].get("ceo_recipient", "")
else:
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "alifaiz.adnetprint@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "afacdfhhbaqgduyg")
    CEO_RECIPIENT = os.getenv("CEO_RECIPIENT", "khalikhussain80@gmail.com")

DEFAULT_RECIPIENTS = [CEO_RECIPIENT] if CEO_RECIPIENT else []


def send_email(subject: str, html_body: str, recipient: str = None) -> tuple[bool, str]:
    """Dispatches HTML emails via SMTP and returns status with diagnostic feedback."""
    target = recipient or CEO_RECIPIENT

    if not SMTP_EMAIL:
        return False, "Sender email missing in [ceo_email]."
    if not SMTP_PASSWORD:
        return False, "App password missing in [ceo_email]."
    if not target:
        return False, "Recipient email address missing."

    try:
        msg = MIMEMultipart()
        msg["From"] = f"AdNet Operations <{SMTP_EMAIL}>"
        msg["To"] = target
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_EMAIL.strip(), SMTP_PASSWORD.strip())
        
        targets = [t.strip() for t in target.split(",") if t.strip()]
        server.sendmail(SMTP_EMAIL.strip(), targets, msg.as_string())
        server.quit()
        return True, f"Digest sent successfully to {target}."
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP Authentication Failed: Check your Google App Password."
    except Exception as e:
        return False, f"SMTP Connection Error: {str(e)}"


def send_daily_jobsheet_digest(recipient_email: str = None) -> tuple[bool, str]:
    """Compiles all jobsheets logged/updated today into an HTML table and emails them."""
    try:
        today_str = str(date.today())
        res = (
            supabase.table("jobs")
            .select("*")
            .gte("created_at", f"{today_str}T00:00:00")
            .order("job_id", desc=True)
            .execute()
        )
        jobs = res.data or []

        if not jobs:
            fallback_res = (
                supabase.table("jobs")
                .select("*")
                .order("job_id", desc=True)
                .limit(25)
                .execute()
            )
            jobs = fallback_res.data or []

        if not jobs:
            return False, "No jobs found in database to compile."

        rows_html = ""
        total_day_value = 0.0

        for j in jobs:
            items = get_job_items(j["job_id"])
            j_val = sum(float(it.get("amount", 0) or 0) for it in items)
            total_day_value += j_val
            items_desc = ", ".join([f"{it.get('item_name')} ({it.get('quantity')} {it.get('unit')})" for it in items]) or "No items"

            rows_html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><b>#{j.get('job_no')}</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{j.get('client_name')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{items_desc}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{j.get('current_stage')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{j.get('due_date')}</td>
                <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">₹ {j_val:,.2f}</td>
            </tr>
            """

        html_content = f"""
        <div style="font-family: Arial, sans-serif; color: #1E293B;">
            <h2 style="color: #E11D48; margin-bottom: 4px;">AdNet Operations Digest</h2>
            <p style="margin-top: 0; color: #64748B;">Date: <b>{today_str}</b> | Total Floor Orders: <b>{len(jobs)}</b></p>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 14px;">
                <thead>
                    <tr style="background-color: #F8FAFC; color: #475569; text-align: left;">
                        <th style="padding: 8px; border: 1px solid #CBD5E1;">Job #</th>
                        <th style="padding: 8px; border: 1px solid #CBD5E1;">Client</th>
                        <th style="padding: 8px; border: 1px solid #CBD5E1;">Items & Description</th>
                        <th style="padding: 8px; border: 1px solid #CBD5E1;">Stage</th>
                        <th style="padding: 8px; border: 1px solid #CBD5E1;">Due Date</th>
                        <th style="padding: 8px; border: 1px solid #CBD5E1; text-align: right;">Total Value</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            <h3 style="text-align: right; margin-top: 16px; color: #0F172A;">Total Value: ₹ {total_day_value:,.2f}</h3>
        </div>
        """

        target = recipient_email or CEO_RECIPIENT
        return send_email(f"AdNet Daily Jobsheet Digest [{today_str}]", html_content, target)

    except Exception as e:
        return False, f"Digest compile error: {str(e)}"