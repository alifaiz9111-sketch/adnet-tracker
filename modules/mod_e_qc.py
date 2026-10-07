from datetime import datetime
import pytz
import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, return_job_to_stage

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("🔍 Module 5: Quality Check (QC)")
    st.caption("Inspect physical dimensions, finish, color fidelity, and packaging.")

    jobs = get_jobs_by_stage("QC")
    if not jobs:
        st.info("No jobs awaiting quality inspection.")
        return

    for job in jobs:
        items = get_job_items(job["job_id"])

        with st.container(border=True):
            st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
            st.caption(f"Target Due: `{job['due_date']}`")

            st.markdown("**Items under inspection:**")
            for it in items:
                st.write(f"- {it['item_name']} | Qty: {it['quantity']} | Specs: {it.get('specifications','')}")

            with st.form(f"qc_form_{job['job_id']}"):
                st.markdown("##### Inspection Checkpoints")
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    chk_size = st.checkbox("Dimensions & Bleed Checked", key=f"chk1_{job['job_id']}")
                with c2:
                    chk_color = st.checkbox("Color Match & Print Quality", key=f"chk2_{job['job_id']}")
                with c3:
                    chk_finish = st.checkbox("Lamination & Eyelets / Trim", key=f"chk3_{job['job_id']}")
                with c4:
                    chk_pack = st.checkbox("Quantity Count & Packaging", key=f"chk4_{job['job_id']}")

                remarks = st.text_input("QC Remarks / Defect Notes", key=f"qcnote_{job['job_id']}")
                btn_pass, btn_reject = st.columns(2)

                with btn_pass:
                    pass_submit = st.form_submit_button("✅ PASS & Move to Dispatch", type="primary", use_container_width=True)
                with btn_reject:
                    reject_submit = st.form_submit_button("❌ REJECT & Return to Production", use_container_width=True)

                if pass_submit:
                    if not (chk_size and chk_color and chk_finish and chk_pack):
                        st.error("All 4 inspection criteria must be verified before passing QC.")
                    else:
                        update_job_stage(job["job_id"], "DISPATCH", user["full_name"], f"QC Passed: {remarks}")
                        st.success(f"Job #{job['job_no']} moved to Dispatch Desk.")
                        st.rerun()

                if reject_submit:
                    if not remarks.strip():
                        st.error("Please provide defect notes explaining the rejection.")
                    else:
                        return_job_to_stage(job["job_id"], "PRODUCTION", f"QC REJECTED: {remarks}", user["full_name"])
                        st.warning(f"Job #{job['job_no']} returned to Production Floor.")
                        st.rerun()