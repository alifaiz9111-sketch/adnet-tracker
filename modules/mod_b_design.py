import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("🎨 Module 2: Design, Proofing & Pre-Press Desk")
    st.caption(f"Graphic Artist / Pre-Press: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    # Fetch jobs currently at DESIGN stage
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "DESIGN")
            .order("job_id")
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching design queue: {e}")
        return

    if not jobs:
        st.info("No jobs pending design or pre-press proofs.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                st.caption(f"📅 Target Date: `{job.get('due_date')}` | Order Taken By: `{job.get('order_taken_by') or 'N/A'}`")
                if job.get("is_returned"):
                    st.error(f"⚠️ Returned by {job.get('returned_by')}: {job.get('return_reason')}")
            with c2:
                st.markdown("##### 📦 Ordered Items & Design Specs")
                for idx, it in enumerate(items, 1):
                    st.markdown(f"**{idx}. {it.get('item_name')}** ({it.get('quantity')} {it.get('unit')})")
                    if it.get("specifications"):
                        st.caption(f"&nbsp;&nbsp;📐 Specs: {it.get('specifications')}")
            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                
                with st.popover("🚀 Complete Design / Route"):
                    st.markdown("#### Design Clearance")
                    proof_url = st.text_input("Design File / Drive Link", placeholder="https://drive.google.com/...", key=f"dsg_url_{job['job_id']}")
                    next_stage = st.selectbox(
                        "Next Stage Target",
                        ["PAYMENT", "PRODUCTION"],
                        format_func=lambda x: "💳 Advance / Accounts Clearance" if x == "PAYMENT" else "⚙️ Production Floor",
                        key=f"nxt_stg_{job['job_id']}"
                    )
                    
                    if st.button("Approve Proof & Forward", key=f"btn_dsg_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            update_data = {
                                "current_stage": next_stage,
                                "is_returned": False
                            }
                            supabase.table("jobs").update(update_data).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} forwarded to {next_stage} successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating stage: {e}")