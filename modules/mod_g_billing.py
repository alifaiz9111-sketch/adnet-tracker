import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, return_job_to_stage

def render(user):
    st.subheader("🧾 Module 7: Billing Review")
    st.caption("Verify physical delivery checklists and authorize for GST tax invoicing.")

    jobs = get_jobs_by_stage("BILLING_REVIEW")
    if not jobs:
        st.info("No jobs pending billing review.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])
        delivered_count = sum(1 for it in items if it.get("is_delivered"))
        total_items = len(items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
                st.caption(f"Target Delivery Date: `{job['due_date']}`")
            with c2:
                st.markdown(f"**Delivery Completion:** `{delivered_count}/{total_items} items delivered`")
            with c3:
                with st.popover("↩️ Return to Dispatch"):
                    reason = st.text_area("Reason", key=f"ret_bill_{job['job_id']}")
                    if st.button("Confirm Return", key=f"btn_ret_b_{job['job_id']}", type="primary"):
                        if reason.strip():
                            return_job_to_stage(job["job_id"], "DISPATCH", reason, user["full_name"])
                            st.rerun()

            st.markdown("---")
            st.markdown("**Delivered Items Review:**")
            for it in items:
                status_icon = "✅" if it.get("is_delivered") else "⏳"
                st.write(f"{status_icon} **{it['item_name']}** - Qty: {it['quantity']} {it['unit']} | Delivered: `{it.get('is_delivered', False)}`")

            notes = st.text_input("Reviewer Authorization Remarks", key=f"bill_notes_{job['job_id']}")
            if st.button("Authorize & Push to CA Billing Queue", key=f"btn_ca_{job['job_id']}", type="primary", use_container_width=True):
                update_job_stage(job["job_id"], "BILLING_QUEUE", user["full_name"], f"Authorized for CA Invoicing: {notes}")
                st.success(f"Job #{job['job_no']} moved to Accounts Desk.")
                st.rerun()