import streamlit as st
from database import supabase, get_jobs_for_stage, update_job_stage
from datetime import date

def render(user):
    st.title("🎨 2. Artwork & Proof Approval")
    st.caption("Design Queue (Commercial rates & totals are masked).")

    # Fetch jobs in DESIGN stage with financial fields masked
    jobs = get_jobs_for_stage("DESIGN", is_financial_role=False)

    if not jobs:
        st.info("No jobs pending artwork approval.")
        return

    for j in jobs:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
            c1.write(f"**Contact:** {j['contact_phone']} | **Delivery:** {j['delivery_address']}")
            c2.write(f"**Due Date:** {j['due_date']} | **Priority:** `{j['priority']}`")

            st.markdown("##### Specifications:")
            for item in j["items"]:
                st.write(f"- Item {item['item_no']}: **{item['description_spec']}** | Material: {item['material']} | Qty: {item['qty']} (Remarks: {item.get('remarks', '')})")

            with st.form(f"proof_form_{j['job_id']}"):
                col_a, col_b, col_c, col_d = st.columns(4)
                proof_sent = col_a.date_input("Proof sent on", key=f"ps_{j['job_id']}")
                approved_on = col_b.date_input("Approved on", key=f"ao_{j['job_id']}")
                approved_by = col_c.text_input("Approved by (client)", key=f"ab_{j['job_id']}")
                approval_mode = col_d.selectbox("Approval mode", ["WhatsApp", "Email", "Signed proof"], key=f"am_{j['job_id']}")
                designer = st.text_input("Designer Name", value=user["full_name"], key=f"des_{j['job_id']}")

                submit = st.form_submit_button("✅ Mark Artwork Approved & Pass to Accounts")
                if submit:
                    supabase.table("job_artwork").update({
                        "proof_sent_on": str(proof_sent),
                        "approved_on": str(approved_on),
                        "approved_by_client": approved_by,
                        "approval_mode": approval_mode,
                        "designer_name": designer
                    }).eq("job_id", j["job_id"]).execute()

                    # Move to payment clearance stage
                    update_job_stage(j["job_id"], "PAYMENT", "Employee C (Accounts)")
                    st.success(f"Job #{j['job_no']} approved and forwarded to Accounts!")
                    st.rerun()