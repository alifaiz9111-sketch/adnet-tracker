import streamlit as st
from database import supabase, get_job_items, get_all_vendors

def render(user):
    st.subheader("⚙️ Module 4: Production Floor & Fabrication Desk")
    st.caption(f"Floor Supervisor / Operator: **{user['full_name']}** | Station: `{user.get('primary_station') or 'Floor General'}`")

    # 1. Fetch all jobs currently in PRODUCTION stage
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "PRODUCTION")
            .order("job_id")
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching production jobs: {e}")
        return

    # Fetch available vendors for outsourcing dropdowns
    vendors = get_all_vendors()
    vendor_options = ["In-House Floor"] + [f"{v['vendor_name']} ({v.get('category') or 'Job-Work'})" for v in vendors if v.get("is_active", True)]

    if not jobs:
        st.info("No active jobs pending on the production floor.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                st.caption(f"📅 Target Due Date: `{job.get('due_date')}` | Booked By: `{job.get('order_taken_by') or 'N/A'}`")
                if job.get("is_returned"):
                    st.error(f"⚠️ Return Notice from {job.get('returned_by')}: {job.get('return_reason')}")
            with c2:
                st.markdown("##### 📦 Items & Print Specifications")
                for idx, it in enumerate(items, 1):
                    st.markdown(f"**{idx}. {it.get('item_name')}** — `{it.get('quantity')} {it.get('unit')}`")
                    if it.get("specifications"):
                        st.caption(f"&nbsp;&nbsp;⚙️ **Specs:** {it.get('specifications')}")
            with c3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")

                # Action 1: Forward to QC
                with st.popover("🚀 Complete & Send to QC"):
                    st.markdown("#### Production Sign-Off")
                    prod_notes = st.text_area("Operator / Finishing Notes", placeholder="e.g. Printed on 3M Vinyl, eyeletted, laminated.", key=f"p_notes_{job['job_id']}")
                    if st.button("Pass to Quality Check (QC)", key=f"btn_qc_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            supabase.table("jobs").update({
                                "current_stage": "QC",
                                "is_returned": False
                            }).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} moved to QC Desk.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update stage: {e}")

                # Action 2: Report Defect / Return to Previous Stage
                with st.popover("⚠️ Return / Flag Job"):
                    st.markdown("#### Send Job Back")
                    return_target = st.selectbox(
                        "Return To Station",
                        ["DESIGN", "SALES"],
                        format_func=lambda x: "🎨 Design / Proofs" if x == "DESIGN" else "📝 Order Intake / Sales",
                        key=f"ret_tgt_{job['job_id']}"
                    )
                    reason = st.text_area("Issue / Defect Explanation *", placeholder="e.g. File resolution too low, dimensions mismatch", key=f"ret_rsn_{job['job_id']}")
                    if st.button("Confirm Return", key=f"btn_ret_{job['job_id']}", type="primary", use_container_width=True):
                        if not reason.strip():
                            st.error("Please provide a valid reason.")
                        else:
                            try:
                                supabase.table("jobs").update({
                                    "current_stage": return_target,
                                    "is_returned": True,
                                    "returned_by": f"{user['full_name']} (Production)",
                                    "return_reason": reason.strip()
                                }).eq("job_id", int(job["job_id"])).execute()
                                st.warning(f"Job #{job.get('job_no')} returned to {return_target}.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to return job: {e}")

                # Action 3: Vendor Outsourcing (if employee is permitted)
                if user.get("can_manage_vendors") or user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]:
                    with st.popover("🏭 Outsource Job-Work"):
                        st.markdown("#### Vendor Assignment")
                        sel_vendor = st.selectbox("Assign Outsourced Vendor", vendor_options, key=f"v_sel_{job['job_id']}")
                        v_notes = st.text_input("Outsourcing Instructions", placeholder="e.g. 5 days delivery promised", key=f"v_inst_{job['job_id']}")
                        if st.button("Save Vendor Log", key=f"btn_vnd_{job['job_id']}", use_container_width=True):
                            st.success(f"Outsourcing logged with {sel_vendor}.")