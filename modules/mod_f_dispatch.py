import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage
from datetime import date

def render(user):
    st.title("🚚 6. Dispatch & Delivery")
    st.caption("Record delivery details, challan numbers, and recipient confirmation.")

    jobs = get_jobs_for_stage("DISPATCH", is_financial_role=False)
    if not jobs:
        st.info("No jobs awaiting dispatch.")
        return

    for j in jobs:
        with st.container(border=True):
            st.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
            st.write(f"**Delivery Address:** {j['delivery_address']}")

            with st.form(f"dispatch_form_{j['job_id']}"):
                c1, c2, c3 = st.columns(3)
                deliv_by = c1.text_input("Delivered By (Driver / Person)", value=user["full_name"], key=f"dby_{j['job_id']}")
                challan_no = c2.text_input("Challan No. *", placeholder="e.g. CH-2026-089", key=f"chal_{j['job_id']}")
                mode_awb = c3.text_input("Mode / AWB / Vehicle No.", placeholder="e.g. Porter / WB-02-XXXX", key=f"awb_{j['job_id']}")

                c4, c5 = st.columns(2)
                deliv_date = c4.date_input("Delivery Date", value=date.today(), key=f"ddate_{j['job_id']}")
                received_by = c5.text_input("Customer Receiving Person Name / Sign", key=f"recby_{j['job_id']}")

                submit = st.form_submit_button("✅ Mark Delivered & Send to Billing Review", type="primary")

                if submit:
                    if not challan_no:
                        st.error("Challan Number is required.")
                        return

                    supabase.table("job_delivery").update({
                        "delivered_by": deliv_by,
                        "mode_awb_no": mode_awb,
                        "delivery_date": str(deliv_date),
                        "challan_no": challan_no,
                        "received_by_name_sign": received_by,
                        "is_delivered": True
                    }).eq("job_id", j["job_id"]).execute()

                    # Move to Billing Review (Employee G / Accounts)
                    update_job_stage(j["job_id"], "BILLING_REVIEW", "Employee G (Billing Review)")
                    st.success(f"Job #{j['job_no']} marked as dispatched and delivered!")
                    st.rerun()