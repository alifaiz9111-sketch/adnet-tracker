import streamlit as st
from database import (
    supabase, 
    get_job_items, 
    get_all_vendors, 
    get_custom_presets, 
    add_custom_preset
)

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

        jid = job["job_id"]
        step_key = f"prod_step_{jid}"
        if step_key not in st.session_state:
            st.session_state[step_key] = 1

        curr_step = st.session_state[step_key]

        with st.container(border=True):
            # Job Overview Header
            jh1, jh2, jh3 = st.columns([3, 2, 2])
            with jh1:
                st.markdown(f"### Job #{job.get('job_no')} — {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                if job.get("is_returned"):
                    st.error(f"⚠️ Return Notice from {job.get('returned_by')}: {job.get('return_reason')}")
            with jh2:
                st.caption(f"📅 Due: **{job.get('due_date')}** | Booked By: `{job.get('order_taken_by') or 'N/A'}`")
            with jh3:
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")

            # Section Progress Indicator
            s_col1, s_col2, s_col3 = st.columns(3)
            with s_col1:
                st.info("🔹 **Section 1: Floor Dashboard**" if curr_step == 1 else "Section 1: Floor Dashboard")
            with s_col2:
                st.info("🔹 **Section 2: Vendor Job-Work**" if curr_step == 2 else "Section 2: Vendor Job-Work")
            with s_col3:
                st.info("🔹 **Section 3: Paper Fabrications**" if curr_step == 3 else "Section 3: Paper Fabrications")

            st.markdown("---")

            # ==========================================
            # SECTION 1: ORIGINAL PRODUCTION FLOOR DASHBOARD
            # ==========================================
            if curr_step == 1:
                st.markdown("#### ⚙️ Section 1: In-House Production Dashboard")
                c_items, c_actions = st.columns([3, 2])
                with c_items:
                    st.markdown("##### 📦 Items & Print Specifications")
                    for idx, it in enumerate(items, 1):
                        st.markdown(f"**{idx}. {it.get('item_name')}** — `{it.get('quantity')} {it.get('unit')}`")
                        if it.get("specifications"):
                            st.caption(f"&nbsp;&nbsp;⚙️ **Specs:** {it.get('specifications')}")

                with c_actions:
                    # Return / Flag Job back to Accounts, Design, or Sales
                    with st.popover("⚠️ Return / Flag Job", use_container_width=True):
                        st.markdown("#### Send Job Back")
                        return_target = st.selectbox(
                            "Return To Station",
                            ["PAYMENT", "DESIGN", "SALES"],
                            format_func=lambda x: {
                                "PAYMENT": "💳 Advance / Accounts Clearance",
                                "DESIGN": "🎨 Design & Proofs",
                                "SALES": "📝 Order Intake / Sales"
                            }.get(x, x),
                            key=f"ret_tgt_{jid}"
                        )
                        reason = st.text_area(
                            "Issue / Return Explanation *", 
                            placeholder="e.g. Advance pending, payment confirmation unverified, dimension discrepancy...", 
                            key=f"ret_rsn_{jid}"
                        )
                        if st.button("Confirm Return", key=f"btn_ret_{jid}", type="primary", use_container_width=True):
                            if not reason.strip():
                                st.error("Please provide a valid reason for returning the job.")
                            else:
                                try:
                                    target_label = "Accounts Clearance" if return_target == "PAYMENT" else return_target
                                    supabase.table("jobs").update({
                                        "current_stage": return_target,
                                        "is_returned": True,
                                        "returned_by": f"{user['full_name']} (Production)",
                                        "return_reason": reason.strip()
                                    }).eq("job_id", int(jid)).execute()
                                    st.warning(f"Job #{job.get('job_no')} returned to {target_label}.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to return job: {e}")

                    # Outsourcing logging
                    if user.get("can_manage_vendors") or user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]:
                        with st.popover("🏭 Outsource Job-Work Log", use_container_width=True):
                            sel_v = st.selectbox("Assign Outsourced Vendor", vendor_options, key=f"v_sel_{jid}")
                            v_nt = st.text_input("Outsourcing Instructions", key=f"v_inst_{jid}")
                            if st.button("Save Vendor Log", key=f"btn_vnd_{jid}", use_container_width=True):
                                st.success(f"Outsourcing logged with {sel_v}.")

                st.markdown("<br>", unsafe_allow_html=True)
                btn_c1, btn_c2 = st.columns([1, 1])
                with btn_c1:
                    if st.button("⏭️ Skip Section", key=f"skip_1_{jid}", use_container_width=True):
                        st.session_state[step_key] = 2
                        st.rerun()
                with btn_c2:
                    if st.button("Proceed to Section 2 ➡️", key=f"next_1_{jid}", type="primary", use_container_width=True):
                        st.session_state[step_key] = 2
                        st.rerun()

            # ==========================================
            # SECTION 2: VENDOR JOB-WORK
            # ==========================================
            elif curr_step == 2:
                st.markdown("#### 🏭 Section 2: Vendor Outsource & Job Details")

                v_names = [v.get("vendor_name", "Vendor") for v in vendors if v.get("is_active", True)] or ["General Vendor"]
                v_selected = st.selectbox("Vendor Name", options=v_names, key=f"s2_vnd_{jid}")

                # Dynamically load base items + saved custom presets
                saved_v_jobs = get_custom_presets("VENDOR_JOB")
                base_item_opts = [it.get("item_name", "").strip() for it in items if it.get("item_name")]
                combined_jobs = sorted(list(set(base_item_opts + saved_v_jobs))) + ["NEW"]

                v_job = st.selectbox("Job", options=combined_jobs, key=f"s2_job_{jid}")
                chosen_job_name = v_job

                if v_job == "NEW":
                    new_v_job = st.text_input("Add NEW JOB Details *", placeholder="Enter custom job name...", key=f"s2_new_job_{jid}").strip()
                    if new_v_job:
                        chosen_job_name = new_v_job
                        add_custom_preset("VENDOR_JOB", new_v_job)

                st.markdown("##### Size: W × B × H")
                sz_c1, sz_c2, sz_c3, sz_c4 = st.columns(4)
                with sz_c1:
                    w2 = st.number_input("Width (W)", value=1.0, step=0.1, key=f"s2_w_{jid}")
                with sz_c2:
                    b2 = st.number_input("Breadth (B)", value=1.0, step=0.1, key=f"s2_b_{jid}")
                with sz_c3:
                    h2 = st.number_input("Height (H)", value=1.0, step=0.1, key=f"s2_h_{jid}")
                with sz_c4:
                    unit2 = st.selectbox("Unit", ["in", "ft", "mm", "cm", "m"], key=f"s2_unit_{jid}")

                qty2 = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"s2_qty_{jid}")

                st.markdown("<br>", unsafe_allow_html=True)
                b2_c1, b2_c2, b2_c3 = st.columns([1, 1, 1])
                with b2_c1:
                    if st.button("⬅️ Return to Section 1", key=f"prev_2_{jid}", use_container_width=True):
                        st.session_state[step_key] = 1
                        st.rerun()
                with b2_c2:
                    if st.button("⏭️ Skip Section", key=f"skip_2_{jid}", use_container_width=True):
                        st.session_state[step_key] = 3
                        st.rerun()
                with b2_c3:
                    if st.button("Proceed to Section 3 ➡️", key=f"next_2_{jid}", type="primary", use_container_width=True):
                        st.session_state[step_key] = 3
                        st.rerun()

            # ==========================================
            # SECTION 3: PAPER FABRICATIONS
            # ==========================================
            elif curr_step == 3:
                st.markdown("#### 📄 Section 3: Paper Fabrications")

                # Base fabrications + saved custom presets
                default_fabs = [
                    "Cardboard Mounting",
                    "Foam Board Pasting",
                    "Matte Lamination",
                    "Gloss Lamination",
                    "Die-Punching & Creasing",
                    "Binding & Eyeletting"
                ]
                saved_fabs = get_custom_presets("FABRICATION")
                combined_fabs = sorted(list(set(default_fabs + saved_fabs))) + ["NEW"]

                fab_choice = st.selectbox("Paper Fabrications", options=combined_fabs, key=f"s3_fab_{jid}")
                chosen_fab_name = fab_choice

                if fab_choice == "NEW":
                    new_fab_job = st.text_input("Add NEW JOB Details *", placeholder="Enter fabrication description...", key=f"s3_new_fab_{jid}").strip()
                    if new_fab_job:
                        chosen_fab_name = new_fab_job
                        add_custom_preset("FABRICATION", new_fab_job)

                st.markdown("##### Size: W × B × H")
                sz3_1, sz3_2, sz3_3, sz3_4 = st.columns(4)
                with sz3_1:
                    w3 = st.number_input("Width (W)", value=1.0, step=0.1, key=f"s3_w_{jid}")
                with sz3_2:
                    b3 = st.number_input("Breadth (B)", value=1.0, step=0.1, key=f"s3_b_{jid}")
                with sz3_3:
                    h3 = st.number_input("Height (H)", value=1.0, step=0.1, key=f"s3_h_{jid}")
                with sz3_4:
                    unit3 = st.selectbox("Unit", ["in", "ft", "mm", "cm", "m"], key=f"s3_unit_{jid}")

                qty3 = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"s3_qty_{jid}")

                st.markdown("<br>", unsafe_allow_html=True)
                b3_c1, b3_c2 = st.columns([1, 1])
                with b3_c1:
                    if st.button("⬅️ Return to Section 2", key=f"prev_3_{jid}", use_container_width=True):
                        st.session_state[step_key] = 2
                        st.rerun()
                with b3_c2:
                    if st.button("⏭️ Skip Section", key=f"skip_3_{jid}", use_container_width=True):
                        st.toast("Section 3 skipped.")

            # ==========================================
            # FINAL SUBMISSION BUTTON (ALWAYS VISIBLE AT BOTTOM)
            # ==========================================
            st.markdown("---")
            st.markdown("""
                <style>
                div.stButton > button.prod-complete-btn {
                    background-color: #E11D48 !important;
                    color: #FFFFFF !important;
                    font-weight: 800 !important;
                    font-size: 15px !important;
                    padding: 10px 0 !important;
                    border: none !important;
                    box-shadow: 0 4px 14px rgba(225, 29, 72, 0.4) !important;
                }
                div.stButton > button.prod-complete-btn:hover {
                    background-color: #BE123C !important;
                }
                </style>
            """, unsafe_allow_html=True)

            btn_done = st.button(
                "🚩 PRODUCTION COMPLETED",
                key=f"btn_prod_complete_{jid}",
                type="primary",
                use_container_width=True
            )

            if btn_done:
                try:
                    supabase.table("jobs").update({
                        "current_stage": "QC",
                        "is_returned": False
                    }).eq("job_id", int(jid)).execute()
                    st.success(f"Production completed for Job #{job.get('job_no')}. Forwarded to QC Desk.")
                    st.session_state[step_key] = 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to complete production: {e}")