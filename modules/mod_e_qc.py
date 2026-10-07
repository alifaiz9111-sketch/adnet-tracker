import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("🔍 Module 5: Quality Check (QC) Desk")
    st.caption(f"QC Inspector: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    # Fetch jobs pending Quality Check
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "QC")
            .order("job_id")
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching QC queue: {e}")
        return

    if not jobs:
        st.info("No jobs pending quality inspection on the QC desk.")
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
                if job.get("is_returned"):
                    st.error(f"⚠️ Past Return: {job.get('return_reason')}")
            with c2:
                st.markdown("##### 📦 Inspection Checklist")
                for idx, it in enumerate(items, 1):
                    st.markdown(f"**{idx}. {it.get('item_name')}** — `{it.get('quantity')} {it.get('unit')}`")
                    if it.get("specifications"):
                        st.caption(f"&nbsp;&nbsp;📐 **Specs to Validate:** {it.get('specifications')}")
            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")

                # Action 1: Approve and Pass to Dispatch
                with st.popover("✅ Approve & Send to Dispatch"):
                    st.markdown("#### Quality Clearance Sign-Off")
                    st.checkbox("Colors, print resolution & saturation verified", key=f"qc_chk1_{job['job_id']}")
                    st.checkbox("Cutting, lamination, and fabrication accurate", key=f"qc_chk2_{job['job_id']}")
                    st.checkbox("Packed and ready for transit", key=f"qc_chk3_{job['job_id']}")
                    
                    if st.button("Pass QC & Dispatch", key=f"btn_pass_qc_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            supabase.table("jobs").update({
                                "current_stage": "DISPATCH",
                                "is_returned": False
                            }).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} passed QC and routed to Dispatch.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update stage: {e}")

                # Action 2: Fail QC / Return to Production Floor
                with st.popover("❌ Defect Reject (Send to Production)"):
                    st.markdown("#### Reject & Return for Rework")
                    defect_reason = st.text_area("Defect Description / Rework Instructions *", placeholder="e.g. Scratches on acrylic, misaligned grommets, wrong vinyl finish", key=f"qc_rej_{job['job_id']}")
                    if st.button("Reject & Return to Floor", key=f"btn_rej_qc_{job['job_id']}", type="primary", use_container_width=True):
                        if not defect_reason.strip():
                            st.error("Please explain the defect before rejecting.")
                        else:
                            try:
                                supabase.table("jobs").update({
                                    "current_stage": "PRODUCTION",
                                    "is_returned": True,
                                    "returned_by": f"{user['full_name']} (QC Desk)",
                                    "return_reason": defect_reason.strip()
                                }).eq("job_id", int(job["job_id"])).execute()
                                st.warning(f"Job #{job.get('job_no')} returned to Production floor for rework.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to reject job: {e}")