import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage
from datetime import datetime

def render(user):
    st.title("⚙️ 4. Production Floor Execution")
    st.caption("Assign machines, log start/end timestamps, and track material consumption & scrap.")

    jobs = get_jobs_for_stage("PRODUCTION", is_financial_role=False)
    if not jobs:
        st.info("No active jobs pending production.")
        return

    for j in jobs:
        with st.container(border=True):
            st.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
            st.write(f"**Due Date:** `{j['due_date']}` | **Priority:** `{j['priority']}`")

            st.markdown("##### Specifications to Print:")
            for item in j["items"]:
                st.write(f"- Item {item['item_no']}: **{item['description_spec']}** | Material: {item['material']} | Qty: {item['qty']}")

            with st.form(f"prod_form_{j['job_id']}"):
                c1, c2 = st.columns(2)
                machine = c1.selectbox("Machine / Section", ["Solvent 1", "Solvent 2", "Eco-Solvent", "Flatbed UV", "Fabric Printer", "Lamination / Fabrication"], key=f"mach_{j['job_id']}")
                operator = c2.text_input("Operator Assigned", value=user["full_name"], key=f"op_{j['job_id']}")

                st.markdown("##### Material Consumption:")
                m1, m2, m3 = st.columns(3)
                mat_name = m1.text_input("Material Name / Roll Spec", key=f"mname_{j['job_id']}")
                qty_issued = m2.number_input("Qty / Sq Ft Issued", min_value=0.0, step=1.0, key=f"qiss_{j['job_id']}")
                qty_used = m3.number_input("Qty / Sq Ft Actually Used", min_value=0.0, step=1.0, key=f"quse_{j['job_id']}")

                submit = st.form_submit_button("✅ Complete Production & Send to QC", type="primary")

                if submit:
                    now = datetime.now().isoformat()
                    supabase.table("job_production").update({
                        "assigned_to": operator,
                        "machine_section": machine,
                        "start_time": now,
                        "end_time": now,
                        "is_production_done": True
                    }).eq("job_id", j["job_id"]).execute()

                    if mat_name and qty_issued > 0:
                        supabase.table("job_production_materials").insert({
                            "job_id": j["job_id"],
                            "row_no": 1,
                            "material_item": mat_name,
                            "qty_issued": qty_issued,
                            "issued_by": user["full_name"],
                            "qty_used": qty_used,
                            "sign": operator
                        }).execute()

                    # Move to Quality Check stage
                    update_job_stage(j["job_id"], "QC", "Employee E (Quality Check)")
                    st.success(f"Job #{j['job_no']} completed on floor. Dispatched to QC queue!")
                    st.rerun()

from database import return_job_to_previous_stage

with st.popover("↩️ Return to Previous Desk"):
    return_reason = st.text_input("Reason for return", key=f"reason_{job_id}")
    if st.button("Confirm Return", key=f"return_btn_{job_id}"):
        if return_reason.strip():
            # Example: from QC back to Production
            return_job_to_previous_stage(job_id, "PRODUCTION", "EMPLOYEE_D", return_reason, user["full_name"])
            st.toast("Job returned successfully", icon="↩️")
            st.rerun()
        else:
            st.warning("Please enter a reason.")