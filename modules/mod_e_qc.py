import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage
from datetime import date

def render(user):
    st.title("🔍 5. Quality Control Inspection")
    st.caption("Inspect printed deliverables against customer specifications (Pricing masked).")

    jobs = get_jobs_for_stage("QC", is_financial_role=False)
    if not jobs:
        st.info("No jobs awaiting quality check.")
        return

    for j in jobs:
        with st.container(border=True):
            st.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
            st.caption(f"Due: {j['due_date']} | Priority: {j['priority']}")

            with st.form(f"qc_form_{j['job_id']}"):
                st.markdown("##### Inspection Checkpoints:")
                c1, c2 = st.columns(2)
                size_ok = c1.checkbox("✓ Size & Specifications Correct", value=True, key=f"qc_size_{j['job_id']}")
                color_ok = c1.checkbox("✓ Colour Matches Approved Proof", value=True, key=f"qc_col_{j['job_id']}")
                finish_ok = c1.checkbox("✓ Finishing / Eyelets / Lamination OK", value=True, key=f"qc_fin_{j['job_id']}")
                qty_ok = c2.checkbox("✓ Quantity Accurately Counted", value=True, key=f"qc_qty_{j['job_id']}")
                pack_ok = c2.checkbox("✓ Packed & Labeled Properly", value=True, key=f"qc_pack_{j['job_id']}")

                remarks = st.text_input("QC Remarks / Notes", placeholder="e.g. Cleared with extra grommets", key=f"rem_{j['job_id']}")

                col_btn1, col_btn2 = st.columns(2)
                pass_btn = col_btn1.form_submit_button("✅ PASS QC & Send to Dispatch", type="primary")
                reject_btn = col_btn2.form_submit_button("❌ REJECT (Send back to Production)")

                if pass_btn:
                    supabase.table("job_quality_check").update({
                        "size_spec_correct": "Y" if size_ok else "N",
                        "colour_matches_proof": "Y" if color_ok else "N",
                        "finishing_ok": "Y" if finish_ok else "N",
                        "quantity_counted": "Y" if qty_ok else "N",
                        "packing_done": "Y" if pack_ok else "N",
                        "checked_by": user["full_name"],
                        "check_date": str(date.today()),
                        "remarks": remarks,
                        "qc_passed": True
                    }).eq("job_id", j["job_id"]).execute()

                    # Move to Dispatch
                    update_job_stage(j["job_id"], "DISPATCH", "Employee F (Dispatch)")
                    st.success(f"Job #{j['job_no']} passed QC inspection!")
                    st.rerun()

                elif reject_btn:
                    update_job_stage(j["job_id"], "PRODUCTION", "Employee D (Production Rework)")
                    st.warning(f"Job #{j['job_no']} rejected and sent back for floor rework.")
                    st.rerun()