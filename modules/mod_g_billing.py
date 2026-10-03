import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage

def render(user):
    st.title("📑 7. Billing Review")
    st.caption("Final verification of delivered jobs before sending them into the Accounts FIFO Billing Queue.")

    jobs = get_jobs_for_stage("BILLING_REVIEW", is_financial_role=True)
    if not jobs:
        st.info("No jobs pending billing review.")
        return

    for j in jobs:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
            c1.write(f"**Challan:** Logged | **Address:** {j['delivery_address']}")

            total_val = sum(i.get("amount", 0) for i in j["items"])
            c2.metric("Order Value", f"₹ {total_val:,.2f}")

            if st.button(f"📥 Approve & Push to FIFO Billing Queue", key=f"push_queue_{j['job_id']}", type="primary"):
                update_job_stage(j["job_id"], "BILLING_QUEUE", "Accounts Department (Billing To-Do)")
                st.success(f"Job #{j['job_no']} placed into Accounts FIFO Billing Queue!")
                st.rerun()

from database import return_job_to_previous_stage
with st.popover("↩️ Return to Previous Desk"):
    return_reason = st.text_input("Reason for return", key=f"reason_{job_id}")
    if st.button("Confirm Return", key=f"return_btn_{job_id}"):
        if return_reason.strip():
            # Example: from QC back to Production
            return_job_to_previous_stage(job_id, "PRODUCTION", "EMPLOYEE_D", return_reason, user["full_name"])
            st.toast("Job returned successfully", icon="↩️")
            st.rerun()
        else:
            st.warning("Please enter a reason.")