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

def notify_ceo_new_job(job_no, client_name, total_val, order_taker, due_date, items, main_delivery_address):
    subject = f"🔔 [NEW JOB] #{job_no} created for {client_name}"

    # Build the HTML Table for Items & Commercials
    items_rows = ""
    for it in items:
        item_addr = it.get("delivery_address", "Same As The Main Address")
        items_rows += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
          <td style="padding: 8px; text-align: center;">{it['item_no']}</td>
          <td style="padding: 8px;"><b>{it['description_spec']}</b><br><small style="color:#6b7280;">Material: {it['material']}</small><br><small style="color:#2563eb;">Delivery: {item_addr}</small></td>
          <td style="padding: 8px; text-align: center;">{it['qty']}</td>
          <td style="padding: 8px; text-align: right;">₹ {it['rate']:,.2f}</td>
          <td style="padding: 8px; text-align: right;"><b>₹ {it['amount']:,.2f}</b></td>
        </tr>
        """

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #1f2937;">
        <div style="background-color: #2563eb; color: #ffffff; padding: 16px; border-radius: 6px 6px 0 0;">
          <h2 style="margin: 0;">New Job Sheet Created: #{job_no}</h2>
          <p style="margin: 4px 0 0 0; font-size: 14px;">Client: <b>{client_name}</b></p>
        </div>
        
        <div style="padding: 16px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 6px 6px;">
          <table style="width: 100%; margin-bottom: 16px; font-size: 14px;">
            <tr>
              <td style="width: 50%;"><b>Order Taken By:</b> {order_taker}</td>
              <td style="width: 50%;"><b>Due Date:</b> {due_date}</td>
            </tr>
            <tr>
              <td colspan="2" style="padding-top: 6px;"><b>Main Delivery Address:</b> {main_delivery_address}</td>
            </tr>
          </table>

          <h3 style="color: #111827; border-bottom: 2px solid #2563eb; padding-bottom: 6px; margin-top: 20px;">Job Specifications & Commercials</h3>
          <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
              <tr style="background-color: #f3f4f6; text-align: left;">
                <th style="padding: 8px; text-align: center;">#</th>
                <th style="padding: 8px;">Description & Specs</th>
                <th style="padding: 8px; text-align: center;">Qty</th>
                <th style="padding: 8px; text-align: right;">Rate</th>
                <th style="padding: 8px; text-align: right;">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items_rows}
            </tbody>
            <tfoot>
              <tr style="background-color: #f9fafb; font-size: 14px;">
                <td colspan="4" style="padding: 10px; text-align: right;"><b>Total Booking Value:</b></td>
                <td style="padding: 10px; text-align: right; color: #2563eb;"><b>₹ {total_val:,.2f}</b></td>
              </tr>
            </tfoot>
          </table>

          <p style="margin-top: 25px; font-size: 12px; color: #6b7280; text-align: center;">
            Adnet Advertising Workflow ERP • Automated Alert
          </p>
        </div>
      </body>
    </html>
    """
    return send_ceo_email(subject, html)