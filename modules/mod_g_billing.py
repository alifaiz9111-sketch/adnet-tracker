import streamlit as st
import pandas as pd
from database import supabase, get_jobs_for_stage, update_job_stage, return_job_to_previous_stage

def render(user):
    st.title("📑 7. Billing Review")
    st.caption("Final verification of delivered jobs before releasing them to the Accounts & CA Invoicing Queue.")

    jobs = get_jobs_for_stage("BILLING_REVIEW", is_financial_role=True)
    if not jobs:
        st.info("No jobs pending billing review.")
        return

    for j in jobs:
        job_id = j["job_id"]
        job_no = j["job_no"]
        client = j["client_name"]
        items = j.get("items", [])

        with st.container(border=True):
            if j.get("is_returned"):
                st.error(f"⚠️ **Returned from Accounts:** {j.get('return_reason')} (Returned by: {j.get('returned_by')})")

            c1, c2 = st.columns([3, 1])
            c1.markdown(f"### Job #{job_no} - {client}")
            c1.write(f"**Main Address:** {j.get('delivery_address')}")

            total_val = sum(i.get("amount", 0) for i in items)
            c2.metric("Total Order Value", f"₹ {total_val:,.2f}")

            st.markdown("##### 📦 Delivered Line Items Check:")
            if items:
                item_rows = []
                for it in items:
                    item_rows.append({
                        "Item": it.get("description_spec"),
                        "Material": it.get("material"),
                        "Qty": it.get("qty"),
                        "Rate (₹)": f"₹ {it.get('rate', 0):,.2f}",
                        "Amount (₹)": f"₹ {it.get('amount', 0):,.2f}",
                        "Delivery Status": "✅ Delivered" if it.get("is_delivered") else "⏳ Pending"
                    })
                st.dataframe(pd.DataFrame(item_rows), use_container_width=True, hide_index=True)

            col_btn, col_ret = st.columns([3, 2])
            with col_btn:
                if st.button(f"📥 Approve & Release to CA Billing Desk", key=f"push_queue_{job_id}", type="primary"):
                    update_job_stage(job_id, "BILLING_QUEUE", "Freelancer CA / Accounts Desk")
                    st.toast(f"Job #{job_no} sent to Accounts Billing Portal!", icon="🚀")
                    st.rerun()

            with col_ret:
                with st.popover("↩️ Return to Dispatch / Production"):
                    ret_reason = st.text_input("Reason for return (required)", key=f"bill_ret_rsn_{job_id}")
                    ret_target = st.selectbox("Return to", ["DISPATCH", "PRODUCTION"], key=f"bill_ret_tgt_{job_id}")
                    if st.button("Confirm Return", key=f"bill_btn_ret_{job_id}"):
                        if not ret_reason.strip():
                            st.warning("Please provide a reason.")
                        else:
                            role_name = "Employee F (Dispatch)" if ret_target == "DISPATCH" else "Employee D (Production)"
                            return_job_to_previous_stage(job_id, ret_target, role_name, ret_reason, user["full_name"])
                            st.toast(f"Job #{job_no} returned to {ret_target}", icon="↩️")
                            st.rerun()