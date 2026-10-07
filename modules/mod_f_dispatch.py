import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("🚚 Module 6: Dispatch, Delivery & Challan Desk")
    st.caption(f"Dispatch Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`")

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
        all_delivered = len(items) > 0 and all(it.get("is_delivered") for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                st.caption(f"📅 Target Date: `{job.get('due_date')}` | Booked By: `{job.get('order_taken_by') or 'N/A'}`")
            with c2:
                st.markdown("##### 📦 Items & Destination Addresses")
                for it in items:
                    del_badge = "✅ Delivered" if it.get("is_delivered") else "⏳ In Transit"
                    st.markdown(f"• **{it.get('item_name')}** ({it.get('quantity')} {it.get('unit')}) — `{del_badge}`")
                    if it.get("delivery_address"):
                        st.caption(f"&nbsp;&nbsp;📍 Destination: {it.get('delivery_address')}")
            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")

                # Item-level delivery confirmation
                with st.popover("📝 Update Item Deliveries"):
                    st.markdown("#### Confirm Delivery Status")
                    for it in items:
                        curr_status = bool(it.get("is_delivered", False))
                        new_status = st.checkbox(
                            f"Mark '{it.get('item_name')}' Delivered",
                            value=curr_status,
                            key=f"chk_del_{it['item_id']}"
                        )
                        if new_status != curr_status:
                            try:
                                supabase.table("job_items").update({
                                    "is_delivered": new_status
                                }).eq("item_id", it["item_id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating item: {e}")

                # Handover to Billing Review
                with st.popover("🚀 Send to Billing Review"):
                    st.markdown("#### Delivery Completion Handover")
                    challan_no = st.text_input("Delivery Challan / Tracking Ref #", placeholder="e.g. DC-2026-902", key=f"dc_{job['job_id']}")
                    runner_name = st.text_input("Driver / Delivery Person", placeholder="e.g. Subhash Logistics", key=f"run_{job['job_id']}")
                    
                    if st.button("Complete Dispatch & Push to Billing", key=f"btn_dsp_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            # Auto-mark all line items delivered upon final handover
                            supabase.table("job_items").update({"is_delivered": True}).eq("job_id", job["job_id"]).execute()
                            supabase.table("jobs").update({
                                "current_stage": "BILLING_REVIEW",
                                "is_returned": False
                            }).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} passed to Billing Review.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to route job: {e}")