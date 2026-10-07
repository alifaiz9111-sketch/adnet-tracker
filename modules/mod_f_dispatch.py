import streamlit as st
from database import (
    supabase,
    get_jobs_for_stage,
    upload_pod_image,
    complete_dispatch_step,
    return_job_to_previous_stage
)

def render(user):
    st.title("🚚 Workstation 6: Dispatch & Logistics")
    st.caption("Verify final item packaging, capture physical proof of delivery (POD), and dispatch to billing review.")

    jobs = get_jobs_for_stage("DISPATCH", is_financial_role=False)

    if not jobs:
        st.info("No orders currently waiting in the dispatch bay.")
        return

    for job in jobs:
        with st.container(border=True):
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.subheader(f"Job #{job['job_no']} — {job['client_name']}")
                origin_user = job.get("last_dispatched_by") or job.get("order_taken_by") or "QC/Production"
                st.caption(f"Cleared from QC by: `{origin_user}`")
            with col_h2:
                if job.get("is_returned"):
                    st.error(f"⚠️ Return Note:\n{job.get('return_reason')}")

            # Delivery Items Verification
            st.markdown("#### 📦 Package Line Items")
            items = job.get("items", [])
            if items:
                for idx, item in enumerate(items, 1):
                    st.write(f"• **Item {idx}:** {item.get('description_spec', 'Print Item')} | **Qty:** {item.get('qty', 1)} | **Delivery Address:** {item.get('delivery_address', 'Self Pickup')}")
            else:
                st.caption("Standard bulk order packaging.")

            st.markdown("---")

            # Dispatch Proof of Delivery (POD) Form
            st.markdown("#### 📝 Delivery Proof & Gate Pass")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                challan_no = st.text_input(
                    "Delivery Challan / Gate Pass Number*",
                    placeholder="e.g. CH-2026-0891",
                    key=f"ch_{job['job_id']}"
                )
            with col_c2:
                pod_file = st.file_uploader(
                    "Proof of Delivery (Camera Photo or Gallery Image)*",
                    type=["png", "jpg", "jpeg", "pdf"],
                    key=f"pod_file_{job['job_id']}",
                    help="Upload a photo of the physically signed receiving copy, delivery slip, or gate pass."
                )

            # Return Option
            with st.popover("↩️ Return to Quality Control (QC)"):
                reason = st.text_area("Reason for Return*", placeholder="e.g., Damaged during packing, missing roll bundle", key=f"r_disp_{job['job_id']}")
                if st.button("Confirm Return to QC", key=f"btn_r_disp_{job['job_id']}", type="primary"):
                    if reason.strip():
                        return_job_to_previous_stage(
                            job_id=job['job_id'],
                            previous_stage="QC",
                            holding_role="QC_INSPECTOR",
                            reason=f"[Dispatch] {reason.strip()}",
                            returned_by_name=user['username']
                        )
                        st.warning("Job returned to Quality Check.")
                        st.rerun()
                    st.error("Please enter a return reason.")

            st.markdown("---")

            # Final Gate Dispatch Button
            if st.button("🚀 Confirm Dispatch & Send to Billing", key=f"btn_disp_comp_{job['job_id']}", type="primary", use_container_width=True):
                if not challan_no.strip():
                    st.error("Delivery Challan / Gate Pass Number is strictly mandatory.")
                elif pod_file is None:
                    st.error("Proof of Delivery (signed challan photo or image) is strictly required to proceed.")
                else:
                    with st.spinner("Uploading proof of delivery receipt..."):
                        pod_url = upload_pod_image(job['job_id'], pod_file)
                        if not pod_url:
                            st.error("Failed to upload delivery proof image. Please retry.")
                        else:
                            success = complete_dispatch_step(
                                job_id=job['job_id'],
                                challan_no=challan_no.strip(),
                                pod_url=pod_url,
                                dispatched_by=user['username']
                            )
                            if success:
                                st.success(f"Job #{job['job_no']} successfully dispatched and forwarded to Billing Review.")
                                st.rerun()
                            else:
                                st.error("Failed to update dispatch record. Check database logs.")