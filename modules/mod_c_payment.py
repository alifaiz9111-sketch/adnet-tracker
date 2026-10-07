import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("💳 Module 3: Advance Clearance & Accounts Desk")
    st.caption(f"Operator: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    # Fetch jobs pending payment clearance
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "PAYMENT")
            .order("job_id")
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching jobs: {e}")
        return

    if not jobs:
        st.info("No jobs pending advance payment clearance.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                st.caption(f"📅 Due Date: `{job.get('due_date')}` | Booked By: `{job.get('order_taken_by') or 'N/A'}`")
            with c2:
                st.markdown("##### 📦 Ordered Line Items")
                for idx, it in enumerate(items, 1):
                    st.caption(f"**{idx}. {it.get('item_name', 'Item')}** — {it.get('quantity')} {it.get('unit')} @ ₹{float(it.get('rate', 0)):,.2f}")
            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                
                with st.popover("💵 Record Payment & Clear"):
                    st.markdown("#### Advance Clearance")
                    adv_amount = st.number_input(
                        "Amount Received (₹)", 
                        min_value=0.0, 
                        max_value=float(total_val) if total_val > 0 else 1000000.0, 
                        value=float(total_val), 
                        key=f"amt_{job['job_id']}"
                    )
                    mode = st.selectbox(
                        "Payment Mode", 
                        ["Bank Transfer / NEFT / IMPS", "UPI / QR", "Cheque", "Cash"], 
                        key=f"mode_{job['job_id']}"
                    )
                    notes = st.text_input("Transaction Ref / Notes", placeholder="e.g. UTR / Cheque No.", key=f"ref_{job['job_id']}")
                    
                    if st.button("Confirm Clearance & Push to Floor", key=f"btn_pay_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            supabase.table("jobs").update({
                                "current_stage": "PRODUCTION",
                                "is_returned": False
                            }).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} cleared and pushed to Production floor.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to clear payment: {e}")