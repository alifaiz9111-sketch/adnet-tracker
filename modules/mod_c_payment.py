from datetime import datetime
import pytz
import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, return_job_to_stage

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("💳 Module 3: Advance & Commercial Clearance")
    st.caption("Record advance payments or authorize credit terms for MNC corporate accounts.")

    jobs = get_jobs_by_stage("PAYMENT")
    if not jobs:
        st.info("No jobs awaiting payment clearance.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
                st.caption(f"Due: `{job['due_date']}`")
                st.markdown(f"**Total Estimated Commercial: ₹ {total_val:,.2f}**")
            with c2:
                st.markdown("**Ordered Items:**")
                for it in items:
                    st.write(f"- {it['item_name']} (Qty: {it['quantity']})")
            with c3:
                with st.popover("↩️ Return to Design"):
                    reason = st.text_area("Reason", key=f"ret_pay_{job['job_id']}")
                    if st.button("Confirm Return", key=f"btn_ret_p_{job['job_id']}", type="primary"):
                        if reason.strip():
                            return_job_to_stage(job["job_id"], "DESIGN", reason, user["full_name"])
                            st.rerun()

            st.markdown("---")
            with st.form(f"pay_form_{job['job_id']}"):
                col_x, col_y = st.columns(2)
                with col_x:
                    clearance_type = st.radio("Clearance Method", ["Advance Received", "Approved Corporate Credit (Portal Billing)"])
                    advance_amount = st.number_input("Advance Token Amount (₹)", min_value=0.0, value=0.0, step=500.0)
                with col_y:
                    payment_ref = st.text_input("Transaction ID / PO Reference Number")
                    approval_note = st.text_input("Remarks")

                if st.form_submit_button("Release to Production Floor", type="primary", use_container_width=True):
                    note = f"Mode: {clearance_type} | Adv: ₹{advance_amount} | Ref: {payment_ref} | {approval_note}"
                    update_job_stage(job["job_id"], "PRODUCTION", user["full_name"], note)
                    st.success(f"Job #{job['job_no']} released to Production Floor.")
                    st.rerun()