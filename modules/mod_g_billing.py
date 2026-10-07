import streamlit as st
from database import supabase

def render(user):
    st.subheader("🧾 Module 7: Billing Review Desk")
    st.caption("Review delivered orders, select billing classification (GST vs Non-GST), and authorize completion or CA queue.")

    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "BILLING_REVIEW")
            .order("job_id")
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching jobs: {e}")
        return

    if not jobs:
        st.info("No jobs pending billing review at this workstation.")
        return

    for job in jobs:
        # Fetch items directly without database helper
        try:
            it_res = supabase.table("job_items").select("*").eq("job_id", job["job_id"]).execute()
            items = it_res.data or []
        except Exception:
            items = []

        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                st.caption(f"📅 Booked: `{str(job.get('created_at', ''))[:10]}` | Due: `{job.get('due_date')}`")
                st.caption(f"Order Taken By: `{job.get('order_taken_by') or 'N/A'}`")
            with c2:
                st.markdown("##### 📦 Delivered Items Checklist")
                for idx, it in enumerate(items, 1):
                    del_status = "✅ Delivered" if it.get("is_delivered") else "⏳ Pending"
                    st.write(f"**{idx}. {it.get('item_name', 'Item')}** ({it.get('quantity')} {it.get('unit')}) - {del_status}")
            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")

            st.markdown("---")

            # GST vs Non-GST Selection & Actions
            act_col1, act_col2 = st.columns([2, 3])
            with act_col1:
                billing_type = st.radio(
                    "Select Invoicing Type:",
                    options=["GST", "Non-GST"],
                    key=f"bill_type_{job['job_id']}",
                    horizontal=True
                )

            with act_col2:
                if billing_type == "GST":
                    st.caption("ℹ️ Pushes this job to CA Desk for GST Invoicing.")
                    if st.button("Authorize", key=f"auth_gst_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            supabase.table("jobs").update({
                                "current_stage": "BILLING_QUEUE",
                                "billing_type": "GST",
                                "is_billed": False
                            }).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} authorized for GST invoicing.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.caption("ℹ️ Non-GST settles directly and marks the job Completed.")
                    if st.button("Complete & Settle Job (Non-GST)", key=f"settle_nongst_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            supabase.table("jobs").update({
                                "current_stage": "SETTLED",
                                "billing_type": "NON_GST",
                                "is_billed": True
                            }).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} marked as Settled.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")