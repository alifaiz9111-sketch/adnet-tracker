from datetime import datetime
import pytz
import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, return_job_to_stage

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("🎨 Module 2: Design & Client Proof Approval")
    st.caption("Verify artwork and proof sign-offs before advancing to commercial clearance.")

    jobs = get_jobs_by_stage("DESIGN")
    if not jobs:
        st.info("No job sheets currently waiting at the Design Desk.")
        return

    for job in jobs:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
                st.caption(f"Due: `{job['due_date']}` | Taken By: {job['order_taken_by']}")
                if job.get("is_returned"):
                    st.error(f"⚠️ Returned by {job.get('returned_by')}: {job.get('return_reason')}")
            with c2:
                items = get_job_items(job["job_id"])
                st.markdown("**Items Specification:**")
                for it in items:
                    st.write(f"- {it['item_name']} ({it['quantity']} {it['unit']}) | Specs: {it.get('specifications','')}")
            with c3:
                with st.popover("↩️ Return to Sales"):
                    reason = st.text_area("Return Reason", key=f"ret_rsn_{job['job_id']}")
                    if st.button("Confirm Return", key=f"btn_ret_{job['job_id']}", type="primary"):
                        if reason.strip():
                            return_job_to_stage(job["job_id"], "SALES", reason, user["full_name"])
                            st.rerun()

            st.markdown("---")
            with st.form(f"design_approval_{job['job_id']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    designer = st.text_input("Designer Assigned", value=user["full_name"])
                    approval_mode = st.selectbox("Proof Approval Mode", ["WhatsApp Confirmation", "Client Signed PDF", "Email Approval", "Verbal Confirmation"])
                with col_b:
                    approved_by = st.text_input("Approved By (Client Rep Name)")
                    notes = st.text_input("Design Specs / Artwork Link")

                if st.form_submit_button("Approve Design & Send to Advance Clearance", type="primary", use_container_width=True):
                    if not approved_by.strip():
                        st.error("Please provide the name of the person who approved the artwork.")
                    else:
                        audit_text = f"Approved by {approved_by} via {approval_mode}. Designer: {designer}. Notes: {notes}"
                        update_job_stage(job["job_id"], "PAYMENT", user["full_name"], audit_text)
                        st.success(f"Job #{job['job_no']} forwarded to Advance Desk.")
                        st.rerun()