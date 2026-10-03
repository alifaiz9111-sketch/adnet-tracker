import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage, return_job_to_previous_stage
from datetime import date

def render(user):
    st.title("🔍 5. Quality Control Inspection")
    st.caption("Inspect printed deliverables against customer specifications (Pricing masked).")

    jobs = get_jobs_for_stage("QC", is_financial_role=False)
    if not jobs:
        st.info("No jobs awaiting quality check.")
        return

    for j in jobs:
        job_id = j["job_id"]
        job_no = j["job_no"]

        with st.container(border=True):
            if j.get("is_returned"):
                st.error(f"⚠️ **Rework History:** {j.get('return_reason')} (Returned by: {j.get('returned_by')})")

            st.markdown(f"### Job #{job_no} - {j['client_name']}")
            st.caption(f"Due: {j['due_date']} | Priority: {j['priority']}")

            with st.form(f"qc_form_{job_id}"):
                st.markdown("##### Inspection Checkpoints:")
                c1, c2 = st.columns(2)
                size_ok = c1.checkbox("✓ Size & Specifications Correct", value=True, key=f"qc_size_{job_id}")
                color_ok = c1.checkbox("✓ Colour Matches Approved Proof", value=True, key=f"qc_col_{job_id}")
                finish_ok = c1.checkbox("✓ Finishing / Eyelets / Lamination OK", value=True, key=f"qc_fin_{job_id}")
                qty_ok = c2.checkbox("✓ Quantity Accurately Counted", value=True, key=f"qc_qty_{job_id}")
                pack_ok = c2.checkbox("✓ Packed & Labeled Properly", value=True, key=f"qc_pack_{job_id}")

                remarks = st.text_input("QC Remarks / Notes", placeholder="e.g. Cleared with extra grommets", key=f"rem_{job_id}")

                col_btn1, col_btn2 = st.columns(2)
                pass_btn = col_btn1.form_submit_button("✅ PASS QC & Send to Dispatch", type="primary")
                reject_btn = col_btn2.form_submit_button("❌ REJECT (Send back to Production)")

                if pass_btn:
                    qc_payload = {
                        "size_spec_correct": "Y" if size_ok else "N",
                        "colour_matches_proof": "Y" if color_ok else "N",
                        "finishing_ok": "Y" if finish_ok else "N",
                        "quantity_counted": "Y" if qty_ok else "N",
                        "packing_done": "Y" if pack_ok else "N",
                        "checked_by": user["full_name"],
                        "check_date": str(date.today()),
                        "remarks": remarks,
                        "qc_passed": True
                    }
                    try:
                        supabase.table("job_quality_check").update(qc_payload).eq("job_id", job_id).execute()
                    except Exception:
                        try:
                            supabase.table("job_qc").update(qc_payload).eq("job_id", job_id).execute()
                        except Exception:
                            pass

                    update_job_stage(job_id, "DISPATCH", "Employee F (Dispatch)")
                    st.toast(f"Job #{job_no} passed QC inspection!", icon="✅")
                    st.rerun()

                elif reject_btn:
                    return_job_to_previous_stage(
                        job_id,
                        "PRODUCTION",
                        "Employee D (Production Head)",
                        f"QC REJECTED: {remarks if remarks else 'Quality checkpoints failed'}",
                        user["full_name"]
                    )
                    st.toast(f"Job #{job_no} rejected and sent back to Production.", icon="⚠️")
                    st.rerun()

            with st.popover("↩️ Return to Design / Production"):
                ret_reason = st.text_input("Reason for return (required)", key=f"qc_ret_{job_id}")
                target_stage = st.selectbox("Return back to", ["PRODUCTION", "DESIGN"], key=f"qc_dest_{job_id}")
                if st.button("Confirm Return", key=f"btn_qcret_{job_id}"):
                    if not ret_reason.strip():
                        st.warning("Please specify a reason.")
                    else:
                        role_label = "Employee D (Production)" if target_stage == "PRODUCTION" else "Employee B (Design)"
                        return_job_to_previous_stage(job_id, target_stage, role_label, ret_reason, user["full_name"])
                        st.toast(f"Job #{job_no} returned to {target_stage}", icon="↩️")
                        st.rerun()