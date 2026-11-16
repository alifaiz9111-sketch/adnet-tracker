import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("🧾 Module 7: Billing & Settlement Desk")
    st.caption(f"Billing Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    tab_pending, tab_settled = st.tabs(["⏳ Pending Billing Review", "📁 Settled Jobs Archive"])

    # --- TAB 1: PENDING BILLING REVIEW ---
    with tab_pending:
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
            jobs = []

        if not jobs:
            st.info("No jobs pending billing review.")
        else:
            for job in jobs:
                items = get_job_items(job["job_id"])
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
                        
                        with st.popover("🧾 Finalize & Settle Job"):
                            st.markdown("#### Invoice Settlement")
                            bill_type = st.radio("Classification", ["Non-GST", "GST"], key=f"bt_{job['job_id']}", horizontal=True)
                            inv_link = st.text_input("Invoice Document Link (Optional)", placeholder="https://...", key=f"inv_{job['job_id']}")
                            
                            if st.button("Complete & Settle", key=f"btn_set_{job['job_id']}", type="primary", use_container_width=True):
                                try:
                                    update_data = {
                                        "current_stage": "SETTLED",
                                        "is_billed": True,
                                        "billing_type": bill_type.upper(),
                                        "invoice_file_url": inv_link.strip() if inv_link else None,
                                        "invoice_uploaded_by": user["full_name"]
                                    }
                                    supabase.table("jobs").update(update_data).eq("job_id", int(job["job_id"])).execute()
                                    st.success(f"Job #{job.get('job_no')} marked as Settled.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error settling job: {e}")

    # --- TAB 2: SETTLED JOBS ARCHIVE ---
    with tab_settled:
        try:
            res_settled = (
                supabase.table("jobs")
                .select("*")
                .eq("current_stage", "SETTLED")
                .order("job_id", desc=True)
                .limit(50)
                .execute()
            )
            settled_jobs = res_settled.data or []
        except Exception:
            settled_jobs = []

        if not settled_jobs:
            st.info("No settled jobs recorded.")
        else:
            for sj in settled_jobs:
                s_items = get_job_items(sj["job_id"])
                s_total = sum(float(it.get("amount", 0) or 0) for it in s_items)
                b_type = sj.get("billing_type", "NON-GST")

                with st.container(border=True):
                    sc1, sc2, sc3 = st.columns([2.5, 2, 1.5])
                    with sc1:
                        st.markdown(f"**Job #{sj.get('job_no')} - {sj.get('client_name')}** `[{b_type}]`")
                        st.caption(f"Contact: `{sj.get('contact_person') or 'N/A'}` | Billed By: `{sj.get('invoice_uploaded_by') or 'Staff'}`")
                    with sc2:
                        st.markdown(f"**Total Settled:** ₹ {s_total:,.2f}")
                    with sc3:
                        if sj.get("invoice_file_url"):
                            st.link_button("📥 View Invoice", sj["invoice_file_url"], use_container_width=True)
                        else:
                            st.caption("✅ Settled (No File)")