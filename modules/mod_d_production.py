from datetime import datetime
import pytz
import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, return_job_to_stage

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("⚙️ Module 4: Production Floor")
    st.caption("Assign machines, track media/roll usage, and log manufacturing runs.")

    jobs = get_jobs_by_stage("PRODUCTION")
    if not jobs:
        st.info("No active print jobs on the production floor.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
                st.caption(f"Due Date: `{job['due_date']}`")
                if job.get("is_returned"):
                    st.error(f"⚠️ Returned by {job.get('returned_by')}: {job.get('return_reason')}")
            with c2:
                st.markdown("**Print Specifications:**")
                for it in items:
                    st.write(f"- **{it['item_name']}**: {it.get('specifications', 'Standard')} (Qty: {it['quantity']} {it['unit']})")
            with c3:
                with st.popover("↩️ Return to Accounts"):
                    reason = st.text_area("Reason", key=f"ret_prod_{job['job_id']}")
                    if st.button("Confirm Return", key=f"btn_ret_pr_{job['job_id']}", type="primary"):
                        if reason.strip():
                            return_job_to_stage(job["job_id"], "PAYMENT", reason, user["full_name"])
                            st.rerun()

            st.markdown("---")
            with st.form(f"prod_form_{job['job_id']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    machine = st.selectbox("Machine Assigned", ["Solvent 10ft", "Eco-Solvent", "UV Flatbed", "Plotter / Cutter", "Fabrication / Handwork"])
                    operator = st.text_input("Floor Operator", value=user["full_name"])
                with col_b:
                    media_used = st.text_input("Substrate / Vinyl / Media Used")
                    notes = st.text_input("Production Notes")

                if st.form_submit_button("Complete Run & Move to QC", type="primary", use_container_width=True):
                    audit_msg = f"Machine: {machine} | Operator: {operator} | Media: {media_used} | Notes: {notes}"
                    update_job_stage(job["job_id"], "QC", user["full_name"], audit_msg)
                    st.success(f"Job #{job['job_no']} moved to Quality Check.")
                    st.rerun()