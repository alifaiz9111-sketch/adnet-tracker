import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("📊 Accounts Ledger & Settlement Queue")
    st.caption(f"Finance Desk Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .order("job_id", desc=True)
            .execute()
        )
        all_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching ledger records: {e}")
        return

    if not all_jobs:
        st.info("No job records available in the finance queue.")
        return

    # Categorize accounts
    unpaid_advance = [j for j in all_jobs if j.get("current_stage") == "PAYMENT"]
    in_production = [j for j in all_jobs if j.get("current_stage") in ["PRODUCTION", "QC", "DISPATCH"]]
    pending_billing = [j for j in all_jobs if j.get("current_stage") in ["BILLING_REVIEW", "BILLING_QUEUE"]]
    settled = [j for j in all_jobs if j.get("current_stage") == "SETTLED"]

    # KPI Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Pending Advance", len(unpaid_advance))
    with c2:
        st.metric("WIP Floor Value", len(in_production))
    with c3:
        st.metric("In Invoicing Queue", len(pending_billing))
    with c4:
        st.metric("Settled & Closed", len(settled))

    st.markdown("---")

    t_advance, t_settled = st.tabs(["💳 Pending Advance Queue", "🗄️ Settled Accounts Ledger"])

    with t_advance:
        st.markdown("#### Orders Awaiting Advance Confirmation")
        if not unpaid_advance:
            st.info("No orders awaiting advance payment.")
        else:
            for job in unpaid_advance:
                items = get_job_items(job["job_id"])
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                with st.container(border=True):
                    col1, col2, col3 = st.columns([2.5, 2, 1.5])
                    with col1:
                        st.markdown(f"**Job #{job.get('job_no')} — {job.get('client_name')}**")
                        st.caption(f"Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                        st.caption(f"Booked By: `{job.get('order_taken_by') or 'N/A'}` | Due: `{job.get('due_date')}`")
                    with col2:
                        st.markdown(f"**Total Order Value:** ₹ {total_val:,.2f}")
                        for it in items:
                            st.caption(f"• {it.get('item_name')} ({it.get('quantity')} {it.get('unit')})")
                    with col3:
                        with st.popover("Clear Advance"):
                            rec_amount = st.number_input("Received (₹)", min_value=0.0, value=float(total_val), key=f"q_amt_{job['job_id']}")
                            if st.button("Confirm & Release", key=f"q_btn_{job['job_id']}", type="primary"):
                                supabase.table("jobs").update({
                                    "current_stage": "PRODUCTION",
                                    "is_returned": False
                                }).eq("job_id", int(job["job_id"])).execute()
                                st.success("Job released to production.")
                                st.rerun()

    with t_settled:
        st.markdown("#### Closed Accounts Archive")
        if not settled:
            st.info("No settled accounts found.")
        else:
            for job in settled:
                items = get_job_items(job["job_id"])
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                b_type = job.get("billing_type", "NON_GST")

                with st.container(border=True):
                    col1, col2, col3 = st.columns([2.5, 2, 1.5])
                    with col1:
                        st.markdown(f"**Job #{job.get('job_no')} — {job.get('client_name')}** `[{b_type}]`")
                        st.caption(f"Contact: `{job.get('contact_person') or 'N/A'}` | Billed By: `{job.get('invoice_uploaded_by') or 'System'}`")
                    with col2:
                        st.markdown(f"**Settled Value:** ₹ {total_val:,.2f}")
                    with col3:
                        if job.get("invoice_file_url"):
                            st.link_button("📥 Tax Invoice", job["invoice_file_url"], use_container_width=True)
                        else:
                            st.caption("✅ Non-GST Settled")