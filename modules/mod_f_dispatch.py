import streamlit as st
from database import supabase, get_job_items


def render(user):
    st.subheader("🚚 Module 6: Dispatch, Delivery & Challan Desk")
    st.caption(
        f"Dispatch Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    # Fetch jobs pending delivery/dispatch
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "DISPATCH")
            .order("job_id")
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching dispatch queue: {e}")
        return

    if not jobs:
        st.info("No orders pending dispatch or delivery.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(
                    f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`"
                )
                st.caption(
                    f"📅 Target Date: `{job.get('due_date')}` | Booked By: `{job.get('order_taken_by') or 'N/A'}`"
                )
                if job.get("is_returned"):
                    st.error(
                        f"⚠️ Return: {job.get('return_reason')} (Reported by: {job.get('returned_by', 'Floor')})"
                    )

            with c2:
                st.markdown("##### 📦 Items & Destination Addresses")
                for it in items:
                    del_badge = "✅ Delivered" if it.get("is_delivered") else "⏳ In Transit"
                    st.markdown(
                        f"• **{it.get('item_name')}** ({it.get('quantity')} {it.get('unit')}) — `{del_badge}`"
                    )
                    if it.get("delivery_address"):
                        st.caption(f"&nbsp;&nbsp;📍 Destination: {it.get('delivery_address')}")

            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")

                # Item-level delivery confirmation
                with st.popover("📝 Update Item Deliveries", use_container_width=True):
                    st.markdown("#### Confirm Delivery Status")
                    for it in items:
                        curr_status = bool(it.get("is_delivered", False))
                        new_status = st.checkbox(
                            f"Mark '{it.get('item_name')}' Delivered",
                            value=curr_status,
                            key=f"chk_del_{it['item_id']}",
                        )
                        if new_status != curr_status:
                            try:
                                supabase.table("job_items").update({
                                    "is_delivered": new_status
                                }).eq("item_id", it["item_id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating item: {e}")

                # Handover to Billing Review with Auto Challan & Dual Uploads
                with st.popover("🚀 Send to Billing Review", use_container_width=True):
                    st.markdown("#### Delivery Completion Handover")
                    
                    auto_challan_no = f"DC-2026-{job.get('job_no')}"
                    st.info(f"📄 **Challan No:** `{auto_challan_no}`")

                    runner_name = st.text_input(
                        "Driver / Delivery Person",
                        placeholder="e.g. Subhash Logistics",
                        key=f"run_{job['job_id']}",
                    )

                    file_challan = st.file_uploader(
                        "📷 Upload Challan Copy",
                        type=["png", "jpg", "jpeg", "pdf"],
                        key=f"upl_challan_{job['job_id']}"
                    )

                    file_job_done = st.file_uploader(
                        "📸 Upload Job Done Image (Site/Delivery Proof)",
                        type=["png", "jpg", "jpeg"],
                        key=f"upl_jobdone_{job['job_id']}"
                    )

                    if st.button(
                        "Complete Dispatch & Push to Billing",
                        key=f"btn_dsp_{job['job_id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        with st.spinner("Uploading proof attachments and recording dispatch..."):
                            challan_url = None
                            job_done_url = None

                            def _upload_file(file_obj, prefix):
                                if not file_obj:
                                    return None
                                try:
                                    f_ext = file_obj.name.split(".")[-1]
                                    path = f"{prefix}_{job['job_id']}_{job.get('job_no')}.{f_ext}"
                                    try:
                                        supabase.storage.from_("dispatch-media").upload(
                                            path=path,
                                            file=file_obj.getvalue(),
                                            file_options={"content-type": file_obj.type, "upsert": "true"}
                                        )
                                        return supabase.storage.from_("dispatch-media").get_public_url(path)
                                    except Exception:
                                        supabase.storage.from_("delivery_proofs").upload(
                                            path=path,
                                            file=file_obj.getvalue(),
                                            file_options={"content-type": file_obj.type, "upsert": "true"}
                                        )
                                        return supabase.storage.from_("delivery_proofs").get_public_url(path)
                                except Exception as err:
                                    st.warning(f"File upload note: {err}")
                                    return None

                            if file_challan:
                                challan_url = _upload_file(file_challan, "challan")
                            if file_job_done:
                                job_done_url = _upload_file(file_job_done, "jobdone")

                            try:
                                # 1. Mark all items delivered
                                supabase.table("job_items").update({
                                    "is_delivered": True
                                }).eq("job_id", job["job_id"]).execute()

                                # 2. Build update dictionary
                                update_payload = {
                                    "current_stage": "BILLING_REVIEW",
                                    "is_returned": False,
                                    "challan_no": auto_challan_no,
                                }

                                d_name = runner_name.strip() if runner_name else None
                                if d_name:
                                    update_payload["dispatch_notes"] = f"Driver: {d_name}"
                                    update_payload["driver_name"] = d_name

                                if challan_url:
                                    update_payload["challan_doc_url"] = challan_url
                                    update_payload["challan_image_url"] = challan_url

                                if job_done_url:
                                    update_payload["proof_file_url"] = job_done_url
                                    update_payload["job_done_image_url"] = job_done_url

                                try:
                                    supabase.table("jobs").update(update_payload).eq("job_id", int(job["job_id"])).execute()
                                except Exception as db_err:
                                    # Fallback in case optional media columns don't exist in schema
                                    fallback_payload = {
                                        "current_stage": "BILLING_REVIEW",
                                        "is_returned": False,
                                        "challan_no": auto_challan_no
                                    }
                                    supabase.table("jobs").update(fallback_payload).eq("job_id", int(job["job_id"])).execute()
                                    st.warning(f"Job moved to Billing Review (schema note: {db_err})")

                                st.success(f"Job #{job.get('job_no')} marked delivered and passed to Billing Review.")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Failed to route job: {e}")

                # Return to QC Action
                with st.popover("⚠️ Return to QC", use_container_width=True):
                    st.markdown("#### Send Job Back to Quality Check")
                    st.caption("Flag packaging issues, missing items, or inspection defects.")
                    qc_reason = st.text_area(
                        "Issue / Defect Reason *",
                        placeholder="e.g. Quantity short, packaging damaged...",
                        key=f"ret_qc_rsn_{job['job_id']}",
                    )
                    if st.button(
                        "Confirm Return to QC",
                        key=f"btn_ret_qc_{job['job_id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        if not qc_reason.strip():
                            st.error("Please provide a valid reason.")
                        else:
                            try:
                                supabase.table("jobs").update({
                                    "current_stage": "QC",
                                    "is_returned": True,
                                    "returned_by": f"{user['full_name']} (Dispatch)",
                                    "return_reason": qc_reason.strip(),
                                }).eq("job_id", int(job["job_id"])).execute()
                                st.warning(f"Job #{job.get('job_no')} returned to Quality Check (QC).")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to return job to QC: {e}")