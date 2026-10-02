import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage
from datetime import date

def render(user):
    st.title("💳 3. Advance Payment & Credit Clearance")
    st.caption("Verify advance or confirm credit clearance before jobs can move to the production floor.")

    jobs = get_jobs_for_stage("PAYMENT", is_financial_role=True)
    if not jobs:
        st.info("No jobs awaiting advance clearance.")
        return

    for j in jobs:
        total_amt = sum(item.get("amount", 0) for item in j["items"])
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            col1.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
            col1.write(f"**Contact:** {j['contact_phone']} | **Due Date:** {j['due_date']}")
            col2.metric("Total Order Value", f"₹ {total_amt:,.2f}")

            with st.form(f"payment_form_{j['job_id']}"):
                c1, c2, c3 = st.columns(3)
                adv_amt = c1.number_input("Advance / PO Amount Received (₹)", min_value=0.0, step=100.0, key=f"adv_{j['job_id']}")
                mode = c2.selectbox("Payment Mode", ["Bank / NEFT", "UPI", "Cheque", "Cash", "PO / Credit Terms"], key=f"mode_{j['job_id']}")
                rec_no = c3.text_input("Receipt / Ref / PO No.", key=f"rec_{j['job_id']}")

                c4, c5 = st.columns(2)
                pay_terms = c4.text_input("Payment Terms / Notes", placeholder="e.g. 50% advance, balance on delivery", key=f"term_{j['job_id']}")
                credit_by = c5.text_input("Credit Approved By (Admin/CEO)", placeholder="Leave blank if advance paid", key=f"cred_{j['job_id']}")

                submit = st.form_submit_button("✅ Clear for Production", type="primary")

                if submit:
                    bal = max(0.0, total_amt - adv_amt)
                    supabase.table("job_payments_advance").update({
                        "advance_po_received": adv_amt,
                        "mode": mode,
                        "receipt_po_no": rec_no,
                        "balance_amount": bal,
                        "payment_terms": pay_terms,
                        "credit_approved_by": credit_by,
                        "is_cleared_for_production": True
                    }).eq("job_id", j["job_id"]).execute()

                    # Move job to Production Stage
                    update_job_stage(j["job_id"], "PRODUCTION", "Employee D (Production Head)")
                    st.success(f"Job #{j['job_no']} cleared! Sent to Production Floor.")
                    st.rerun()