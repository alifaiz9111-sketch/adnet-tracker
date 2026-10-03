import streamlit as st
import pandas as pd
from database import (
    get_jobs_for_stage,
    update_job_stage,
    return_job_to_previous_stage,
    update_item_delivery_status
)

def render(user):
    st.title("🚚 6. Dispatch & Delivery Floor")
    
    jobs = get_jobs_for_stage("DISPATCH")
    if not jobs:
        st.success("✅ All clear! No jobs waiting for dispatch.")
        return

    st.markdown(f"**{len(jobs)}** job(s) pending dispatch.")

    for job in jobs:
        job_id = job["job_id"]
        job_no = job["job_no"]
        client = job["client_name"]
        items = job.get("items", [])

        # Highlight returned jobs
        if job.get("is_returned"):
            st.error(f"⚠️ **Returned Job #{job_no}:** {job.get('return_reason')} (Returned by: {job.get('returned_by')})")

        with st.expander(f"📦 Job #{job_no} — {client} (Due: {job.get('due_date')})", expanded=True):
            st.write(f"**Delivery / Dispatch Address:** {job.get('address', 'Main Client Address')}")
            
            st.markdown("##### 📋 Line Items - Delivery Verification")
            st.caption("Tick items as they are dispatched:")

            all_items_delivered = True
            for it in items:
                it_id = it.get("item_id")
                curr_status = bool(it.get("is_delivered", False))
                
                col_chk, col_desc, col_qty, col_rem = st.columns([1, 4, 2, 3])
                with col_chk:
                    is_ticked = st.checkbox("Delivered", value=curr_status, key=f"del_chk_{it_id}")
                    if is_ticked != curr_status:
                        update_item_delivery_status(it_id, is_ticked)
                        st.rerun()
                
                if not is_ticked:
                    all_items_delivered = False

                with col_desc:
                    st.write(f"**{it.get('description_spec')}** ({it.get('material')})")
                with col_qty:
                    st.write(f"Qty: **{it.get('qty')}**")
                with col_rem:
                    st.caption(f"Remarks: {it.get('remarks') or 'None'}")

            st.markdown("---")

            col_actions, col_return = st.columns([3, 2])

            with col_actions:
                challan_no = st.text_input(f"Delivery Challan / Gate Pass No.", key=f"ch_{job_id}")
                if st.button(f"✅ Mark Dispatched & Send to Billing Review", type="primary", key=f"fwd_{job_id}"):
                    update_job_stage(job_id, "BILLING_REVIEW", "EMPLOYEE_G")
                    st.toast(f"Job #{job_no} moved to Billing Review!", icon="🚀")
                    st.success(f"Job #{job_no} dispatched!")
                    st.rerun()

            with col_return:
                st.markdown("##### ↩️ Return to Floor")
                with st.popover("Return to Production"):
                    ret_reason = st.text_input("Reason for return (required)", key=f"ret_rsn_{job_id}")
                    if st.button("Confirm Return", key=f"btn_ret_{job_id}"):
                        if not ret_reason.strip():
                            st.warning("Please specify a reason.")
                        else:
                            return_job_to_previous_stage(job_id, "PRODUCTION", "EMPLOYEE_D", ret_reason, user["full_name"])
                            st.toast(f"Job #{job_no} returned to Production Floor", icon="↩️")
                            st.rerun()