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