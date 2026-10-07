import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

def send_ceo_order_alert(job_no, client_name, job_items, total_est_amount, user_name):
    """Dispatches order commercial details directly to the CEO via Gmail SMTP."""
    try:
        cfg = st.secrets.get("ceo_email", {})
        sender_email = cfg.get("sender_email")
        sender_password = cfg.get("sender_password")
        smtp_server = cfg.get("smtp_server", "smtp.gmail.com")
        smtp_port = int(cfg.get("smtp_port", 587))
        recipient_email = cfg.get("ceo_recipient")

        if not all([sender_email, sender_password, recipient_email]):
            return False, "SMTP configuration missing in secrets.toml"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 [New Order Alert] Job #{job_no} - {client_name}"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        items_table_rows = "".join([
            f"""<tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('item_name', '')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item.get('quantity', 0)} {item.get('unit', '')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">₹ {float(item.get('rate', 0)):,.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">₹ {float(item.get('amount', 0)):,.2f}</td>
            </tr>"""
            for item in job_items
        ])

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <h2 style="color: #E10600;">AdNet Print Tracker - Order Confirmation</h2>
                <p>A new job sheet has been logged by <strong>{user_name}</strong>.</p>
                <hr style="border: 0; border-top: 1px solid #eee;" />
                <table style="width: 100%; margin-bottom: 20px;">
                    <tr><td><strong>Job Number:</strong> #{job_no}</td></tr>
                    <tr><td><strong>Client:</strong> {client_name}</td></tr>
                    <tr><td><strong>Total Order Value:</strong> ₹ {float(total_est_amount):,.2f}</td></tr>
                </table>
                <h3>Commercial Item Breakdown:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f8f8f8;">
                            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Item</th>
                            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Qty</th>
                            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Rate</th>
                            <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_table_rows}
                    </tbody>
                </table>
                <br>
                <p style="font-size: 12px; color: #777;">This is an automated notification from AdNet Print ERP.</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

        return True, "Alert sent successfully"
    except Exception as e:
        return False, str(e)