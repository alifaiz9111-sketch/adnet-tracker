import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database import supabase, get_job_items

# Configure SMTP parameters via environment or fallback
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DEFAULT_RECIPIENT = os.getenv("DEFAULT_MANAGEMENT_EMAIL", SMTP_EMAIL)


def send_email(subject: str, html_body: str, recipient: str = None) -> bool:
    """Standard utility function to dispatch HTML emails via SMTP."""
    target = recipient or DEFAULT_RECIPIENT
    if not SMTP_EMAIL or not SMTP_PASSWORD or not target:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = target
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, target, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False


def send_new_jobsheet_alert(header_payload: dict, line_items: list):
    """Sends immediate dispatch alert to production/management when order is created."""
    job_no = header_payload.get("job_no", "N/A")
    client = header_payload.get("client_name", "N/A")
    due = header_payload.get("due_date", "N/A")
    desk = header_payload.get("current_stage", "N/A")

    rows = ""
    total = 0.0
    for it in line_items:
        amt = float(it.get("amount", 0.0) or 0.0)
        total += amt
        rows += f"<tr><td>{it.get('item_name')}</td><td>{it.get('quantity')}</td><td>₹ {amt:,.2f}</td></tr>"

    html = f"""
    <h2>New Jobsheet Logged: #{job_no}</h2>
    <p><b>Client:</b> {client} | <b>Due:</b> {due} | <b>Target Desk:</b> {desk}</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
        <thead><tr><th>Item</th><th>Qty</th><th>Amount</th></tr></thead>
        <tbody>{rows}</tbody>
    </table>
    <h3>Total: ₹ {total:,.2f}</h3>
    """
    send_email(f"New Order #{job_no} - {client}", html)


def send_daily_jobsheet_digest(recipient_email=None):
    """Compiles all jobsheets logged/updated today into a table and emails them."""
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

        # Fallback to fetching all active jobs if created_at timestamp is null
        if not jobs:
            fallback_res = supabase.table("jobs").select("*").order("job_id", desc=True).limit(20).execute()
            jobs = fallback_res.data or []

        if not jobs:
            return False, "No jobsheets found to compile."

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
        <h3>📅 Daily Jobsheet Digest — {today_str}</h3>
        <p>Total orders listed: <b>{len(jobs)}</b> | Total Value: <b>₹ {total_day_value:,.2f}</b></p>
        <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 13px;">
            <thead>
                <tr style="background-color: #f2f2f2;">
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Job #</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Client</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Items</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Current Stage</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Due Date</th>
                    <th style="padding: 8px; border: 1px solid #ddd; text-align: right;">Total Value</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """

        target = recipient_email or DEFAULT_RECIPIENT
        success = send_email(f"Daily Jobsheet Digest [{today_str}]", html_content, target)
        if success:
            return True, f"Digest sent successfully ({len(jobs)} jobs included)."
        else:
            return False, "SMTP configuration missing or mail server unreachable."

    except Exception as e:
        return False, str(e)