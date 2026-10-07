from datetime import datetime, timedelta
import pytz
import streamlit as st
from database import create_job_sheet, get_next_job_no
from email_service import send_ceo_order_alert

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("📝 Module 1: Order Intake & Sales")
    st.caption("Create and initiate new client job sheets.")

    next_no = get_next_job_no()

    with st.form("new_order_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            job_no = st.text_input("Job Sheet #", value=next_no, disabled=True)
            client_name = st.text_input("Client / Company Name *")
        with c2:
            contact_person = st.text_input("Contact Person")
            contact_phone = st.text_input("Phone Number")
        with c3:
            due_date = st.date_input("Target Delivery Date", min_value=datetime.now(IST).date(), value=datetime.now(IST).date() + timedelta(days=3))
            order_taken_by = st.text_input("Order Taken By", value=user["full_name"], disabled=True)

        st.markdown("##### Line Items Specification")
        num_items = st.number_input("Number of Items", min_value=1, max_value=20, value=1, step=1)
        
        items_data = []
        for i in range(int(num_items)):
            with st.container(border=True):
                st.markdown(f"**Line Item #{i+1}**")
                col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 2])
                with col_a:
                    item_name = st.text_input(f"Item Description *", key=f"name_{i}")
                    remarks = st.text_input(f"Print Specs / Dimensions", key=f"rem_{i}")
                with col_b:
                    qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
                    unit = st.selectbox("Unit", ["Pcs", "Sq.Ft", "Sets", "Rolls"], key=f"unit_{i}")
                with col_c:
                    rate = st.number_input("Rate (₹)", min_value=0.0, value=0.0, step=10.0, key=f"rate_{i}")
                    amount = qty * rate
                    st.markdown(f"Total: **₹ {amount:,.2f}**")
                with col_d:
                    delivery_address = st.text_area("Delivery Address / Branch", key=f"addr_{i}", height=90)
                
                items_data.append({
                    "item_name": item_name,
                    "specifications": remarks,
                    "quantity": qty,
                    "unit": unit,
                    "rate": rate,
                    "amount": amount,
                    "delivery_address": delivery_address,
                    "is_delivered": False
                })

        submit = st.form_submit_button("Submit & Dispatch to Design Desk", type="primary", use_container_width=True)

        if submit:
            if not client_name.strip():
                st.error("Client name is required.")
                return

            total_val = sum(it["amount"] for it in items_data)
            job_payload = {
                "job_no": next_no,
                "client_name": client_name.strip(),
                "contact_person": contact_person.strip(),
                "contact_phone": contact_phone.strip(),
                "due_date": str(due_date),
                "order_taken_by": user["full_name"],
                "current_stage": "DESIGN",
                "is_billed": False,
                "created_at": datetime.now(IST).isoformat()
            }

            success, res = create_job_sheet(job_payload, items_data)
            if success:
                st.success(f"Job Sheet #{next_no} registered successfully.")
                send_ceo_order_alert(next_no, client_name, items_data, total_val, user["full_name"])
                st.rerun()
            else:
                st.error(f"Error registering job sheet: {res}")