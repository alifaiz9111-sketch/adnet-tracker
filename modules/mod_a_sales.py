import streamlit as st
from database import supabase, update_job_stage
from email_service import notify_ceo_new_job
from datetime import date

def render(user):
    st.title("📝 1. Order Intake & Client Specification")
    st.caption("Fill all details to create a new Job Sheet card.")

    with st.form("new_job_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            job_no = st.text_input("Job No. *", placeholder="e.g. 101")
            client_name = st.text_input("Client Name *", placeholder="e.g. RTIICS Hospital")
            contact_phone = st.text_input("Contact / Phone", placeholder="98XXXXXXXX")
        with col2:
            date_received = st.date_input("Date Received", value=date.today())
            due_date = st.date_input("Due Date *")
            priority = st.selectbox("Priority", ["Normal", "Urgent", "Low"])
        with col3:
            po_order_ref = st.text_input("PO / Order Ref.", placeholder="e.g. PO-889")
            gst_no = st.text_input("GST No.", placeholder="19AAAAA0000A1Z5")
            order_taken_by = st.text_input("Order Taken By", value=user["full_name"])

        delivery_address = st.text_area("Delivery Address")

        st.markdown("#### 📦 Job Specifications & Commercials")
        st.caption("Enter up to 3 items below:")

        items = []
        for i in range(1, 4):
            with st.expander(f"Item #{i}", expanded=(i == 1)):
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                desc = c1.text_input(f"Description / Size / Spec #{i}", key=f"desc_{i}")
                mat = c2.text_input(f"Material #{i}", key=f"mat_{i}")
                qty = c3.number_input(f"Qty #{i}", min_value=0.0, step=1.0, key=f"qty_{i}")
                rate = c4.number_input(f"Rate (Rs) #{i}", min_value=0.0, step=1.0, key=f"rate_{i}")
                rem = st.text_input(f"Remarks #{i}", key=f"rem_{i}")
                if desc and qty > 0:
                    items.append({
                        "item_no": i,
                        "description_spec": desc,
                        "material": mat,
                        "qty": qty,
                        "rate": rate,
                        "amount": qty * rate,
                        "remarks": rem
                    })

        total_amount = sum(item["amount"] for item in items)
        st.markdown(f"### **Total Amount: ₹ {total_amount:,.2f}**")

        submit = st.form_submit_button("✅ Create Job Sheet & Notify CEO", type="primary")

    if submit:
        if not job_no or not client_name or not due_date or not items:
            st.error("Please fill in Job No, Client Name, Due Date, and at least 1 item.")
            return

        job_data = {
            "job_no": job_no,
            "date_received": str(date_received),
            "due_date": str(due_date),
            "priority": priority,
            "client_name": client_name,
            "contact_phone": contact_phone,
            "po_order_ref": po_order_ref,
            "gst_no": gst_no,
            "order_taken_by": order_taken_by,
            "delivery_address": delivery_address,
            "current_stage": "DESIGN",
            "holding_employee_role": "Employee B (Design)",
            "created_by": user["user_id"]
        }

        try:
            res = supabase.table("jobs").insert(job_data).execute()
            created_job_id = res.data[0]["job_id"]

            for it in items:
                it["job_id"] = created_job_id
                supabase.table("job_items").insert(it).execute()

            # Initialize stage records
            supabase.table("job_artwork").insert({"job_id": created_job_id}).execute()
            supabase.table("job_payments_advance").insert({"job_id": created_job_id, "balance_amount": total_amount}).execute()

            # Send Instant CEO Email
            notify_ceo_new_job(job_no, client_name, total_amount, order_taken_by, str(due_date))

            st.success(f"Job #{job_no} successfully created! Task dispatched to Design Team.")
        except Exception as e:
            st.error(f"Error creating job: {e}")