from datetime import datetime
import pytz
import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, return_job_to_stage, supabase

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("🚚 Module 6: Dispatch & Line Item Delivery")
    st.caption("Verify delivery item by item and record gate passes or challans.")

    jobs = get_jobs_by_stage("DISPATCH")
    if not jobs:
        st.info("No orders currently at the Dispatch Desk.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
                st.caption(f"Due Date: `{job['due_date']}`")
            with c2:
                st.markdown(f"**Recipient Contact:** {job.get('contact_person', 'N/A')} ({job.get('contact_phone', 'N/A')})")
            with c3:
                with st.popover("↩️ Return to QC"):
                    reason = st.text_area("Reason", key=f"ret_disp_{job['job_id']}")
                    if st.button("Confirm Return", key=f"btn_ret_d_{job['job_id']}", type="primary"):
                        if reason.strip():
                            return_job_to_stage(job["job_id"], "QC", reason, user["full_name"])
                            st.rerun()

            st.markdown("---")
            st.markdown("##### Line Items Delivery Confirmation")
            item_status_map = {}

            for it in items:
                col_i, col_d, col_c = st.columns([2, 3, 1])
                with col_i:
                    st.write(f"**{it['item_name']}** (Qty: {it['quantity']} {it['unit']})")
                with col_d:
                    st.caption(f"📍 Address: {it.get('delivery_address', 'Self Pickup')}")
                with col_c:
                    is_del = st.checkbox("Delivered", value=it.get("is_delivered", False), key=f"del_{it['item_id']}")
                    item_status_map[it["item_id"]] = is_del

            with st.form(f"dispatch_form_{job['job_id']}"):
                col_x, col_y = st.columns(2)
                with col_x:
                    challan_no = st.text_input("Delivery Challan / Gate Pass #")
                    delivery_agent = st.text_input("Delivery Boy / Transporter Name")
                with col_y:
                    vehicle_no = st.text_input("Vehicle Number")
                    pod_notes = st.text_input("Proof of Delivery Remarks")

                if st.form_submit_button("Update Delivery & Forward to Billing Review", type="primary", use_container_width=True):
                    # Persist line items delivery status
                    now_iso = datetime.now(IST).isoformat()
                    for it_id, del_val in item_status_map.items():
                        supabase.table("job_items").update({
                            "is_delivered": del_val,
                            "delivered_at": now_iso if del_val else None
                        }).eq("item_id", it_id).execute()

                    audit_msg = f"Challan: {challan_no} | Agent: {delivery_agent} | Veh: {vehicle_no} | Notes: {pod_notes}"
                    update_job_stage(job["job_id"], "BILLING_REVIEW", user["full_name"], audit_msg)
                    st.success(f"Job #{job['job_no']} forwarded to Billing Review.")
                    st.rerun()