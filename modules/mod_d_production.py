import streamlit as st
from database import (
    get_production_jobs,
    complete_production_step,
    return_job_to_prev_desk,
    get_dynamic_dropdown_options,
    add_dynamic_option
)

def render(user):
    st.title("⚙️ Workstation 4: Production Floor")
    st.caption("Active job execution across in-house printing, outsourced job-work vendors, and paper fabrication.")

    jobs = get_production_jobs()

    if not jobs:
        st.info("No job sheets currently waiting on the production floor.")
        return

    for job in jobs:
        with st.container(border=True):
            col_hdr1, col_hdr2 = st.columns([3, 1])
            with col_hdr1:
                st.subheader(f"Job #{job['job_no']} — {job['client_name']}")
                origin_user = job.get("last_dispatched_by") or job.get("order_taken_by") or "Sales/Accounts"
                st.caption(f"Dispatched by / Origin Desk: `{origin_user}`")
            with col_hdr2:
                if job.get("is_returned"):
                    st.error(f"⚠️ Flagged Return:\n{job.get('return_reason')}")

            # =================================================================
            # MICRO-STEP 1: In-House Floor Execution
            # =================================================================
            st.markdown("#### 1️⃣ Micro-Step 1: In-House Printing & Floor Allocation")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                machine = st.selectbox(
                    "Machine Allocated*",
                    ["Solvent Alpha", "Eco-Solvent 1", "UV Flatbed", "Plotter / Cutter", "Offset Sheetfed", "Manual Handcraft"],
                    key=f"mach_{job['job_id']}"
                )
            with c2:
                operator = st.text_input("Machine Operator Name*", placeholder="e.g. Ramesh Kumar", key=f"op_{job['job_id']}")
            with c3:
                media_used = st.text_input("Roll / Substrate Type*", placeholder="e.g. 280 GSM Star Flex, Cast Vinyl", key=f"med_{job['job_id']}")

            with st.popover("↩️ Return to Previous Desk (Step 1)"):
                reason_1 = st.text_area("Reason for Return*", placeholder="e.g., File format incompatible, missing substrate specs", key=f"r1_{job['job_id']}")
                if st.button("Confirm Return", key=f"btn_r1_{job['job_id']}", type="primary"):
                    if reason_1.strip():
                        return_job_to_prev_desk(job['job_id'], target_user=origin_user, reason=reason_1, step="Micro-Step 1")
                        st.warning("Job sheet returned to previous desk.")
                        st.rerun()
                    st.error("Please enter a valid reason.")

            st.markdown("---")

            # =================================================================
            # MICRO-STEP 2: Outsourced Vendor Execution (With Inline Add New)
            # =================================================================
            st.markdown("#### 2️⃣ Micro-Step 2: Outsourced Vendor Work (Optional)")
            
            vendors_list = get_dynamic_dropdown_options("vendors", "vendor_name")
            job_types_list = get_dynamic_dropdown_options("vendor_job_types", "job_type")

            # Vendor Selection & Inline Add
            col_v1, col_v2 = st.columns([2, 1])
            with col_v1:
                sel_vendor = st.selectbox(
                    "Select Vendor",
                    ["None"] + vendors_list,
                    key=f"v_sel_{job['job_id']}"
                )
            with col_v2:
                with st.popover("➕ Add New Vendor"):
                    new_v = st.text_input("Vendor Company Name", key=f"new_v_in_{job['job_id']}")
                    if st.button("Save Vendor", key=f"btn_v_save_{job['job_id']}", type="primary"):
                        if new_v.strip():
                            add_dynamic_option("vendors", "vendor_name", new_v.strip())
                            st.rerun()
                        st.error("Enter a name.")

            # Job Type Selection & Inline Add
            col_j1, col_j2 = st.columns([2, 1])
            with col_j1:
                sel_job = st.selectbox(
                    "Select Job Type",
                    ["None"] + job_types_list,
                    key=f"j_sel_{job['job_id']}"
                )
            with col_j2:
                with st.popover("➕ Add New Job Type"):
                    new_j = st.text_input("Job Type / Task", placeholder="e.g. Acrylic Laser Cutting, Neon Sign", key=f"new_j_in_{job['job_id']}")
                    if st.button("Save Job Type", key=f"btn_j_save_{job['job_id']}", type="primary"):
                        if new_j.strip():
                            add_dynamic_option("vendor_job_types", "job_type", new_j.strip())
                            st.rerun()
                        st.error("Enter a job type.")

            col_vh, col_vw = st.columns(2)
            with col_vh:
                v_height = st.text_input("Vendor Job Height", placeholder="e.g. 10 ft / 120 in", key=f"vh_{job['job_id']}")
            with col_vw:
                v_width = st.text_input("Vendor Job Width", placeholder="e.g. 4 ft / 48 in", key=f"vw_{job['job_id']}")

            with st.popover("↩️ Return to Previous Desk (Step 2)"):
                reason_2 = st.text_area("Reason for Return*", placeholder="e.g., Vendor capacity full, rate mismatch", key=f"r2_{job['job_id']}")
                if st.button("Confirm Return", key=f"btn_r2_{job['job_id']}", type="primary"):
                    if reason_2.strip():
                        return_job_to_prev_desk(job['job_id'], target_user=origin_user, reason=reason_2, step="Micro-Step 2")
                        st.warning("Job sheet returned to previous desk.")
                        st.rerun()
                    st.error("Please enter a valid reason.")

            st.markdown("---")

            # =================================================================
            # MICRO-STEP 3: Paper Fabrication & Finishing (With Inline Add New)
            # =================================================================
            st.markdown("#### 3️⃣ Micro-Step 3: Paper Fabrication & Finishing (Optional)")
            
            fab_list = get_dynamic_dropdown_options("paper_fabrications", "fabrication_name")

            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                sel_fab = st.selectbox(
                    "Select Paper Fabrication",
                    ["None"] + fab_list,
                    key=f"fab_sel_{job['job_id']}"
                )
            with col_f2:
                with st.popover("➕ Add Fabrication"):
                    new_f = st.text_input("Finishing / Fabrication Type", placeholder="e.g. Thermal Gloss Lamination, Eyeleting", key=f"new_f_in_{job['job_id']}")
                    if st.button("Save Fabrication", key=f"btn_f_save_{job['job_id']}", type="primary"):
                        if new_f.strip():
                            add_dynamic_option("paper_fabrications", "fabrication_name", new_f.strip())
                            st.rerun()
                        st.error("Enter a fabrication type.")

            col_fh, col_fw = st.columns(2)
            with col_fh:
                fab_height = st.text_input("Fabrication Height", placeholder="e.g. 3 ft / 36 in", key=f"fh_{job['job_id']}")
            with col_fw:
                fab_width = st.text_input("Fabrication Width", placeholder="e.g. 2 ft / 24 in", key=f"fw_{job['job_id']}")

            with st.popover("↩️ Return to Previous Desk (Step 3)"):
                reason_3 = st.text_area("Reason for Return*", placeholder="e.g., Missing finishing specifications", key=f"r3_{job['job_id']}")
                if st.button("Confirm Return", key=f"btn_r3_{job['job_id']}", type="primary"):
                    if reason_3.strip():
                        return_job_to_prev_desk(job['job_id'], target_user=origin_user, reason=reason_3, step="Micro-Step 3")
                        st.warning("Job sheet returned to previous desk.")
                        st.rerun()
                    st.error("Please enter a valid reason.")

            st.markdown("---")

            # =================================================================
            # Bottom Completion Button with Strict Data Gates
            # =================================================================
            if st.button("✅ Complete Production Floor", key=f"btn_comp_{job['job_id']}", type="primary", use_container_width=True):
                if not operator.strip() or not media_used.strip():
                    st.error("Step 1 Machine Operator and Roll/Substrate fields are mandatory before moving to Quality Control.")
                else:
                    success = complete_production_step(
                        job_id=job['job_id'],
                        machine=machine,
                        operator=operator.strip(),
                        media=media_used.strip(),
                        vendor=sel_vendor,
                        v_job=sel_job,
                        v_h=v_height.strip(),
                        v_w=v_width.strip(),
                        fab=sel_fab,
                        fab_h=fab_height.strip(),
                        fab_w=fab_width.strip(),
                        completed_by=user['username']
                    )
                    if success:
                        st.success(f"Job #{job['job_no']} successfully routed to Quality Check (QC).")
                        st.rerun()
                    else:
                        st.error("Failed to complete production step. Check database logs.")