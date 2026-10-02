import streamlit as st
from database import supabase, get_jobs_for_stage
from datetime import date

def render(user):
    st.title("🧾 8. Accounts Billing To-Do List (FIFO Queue)")
    st.caption("Completed jobs awaiting Tax Invoice generation. Newest jobs appear at the bottom. 24-hour turnaround target.")

    # In FIFO order: earliest delivered first
    jobs = supabase.table("jobs").select("*").eq("current_stage", "BILLING_QUEUE").order("job_id", desc=False).execute().data

    if not jobs:
        st.success("🎉 All clear! No jobs pending billing in the queue.")
        return

    st.write(f"**Total Pending Invoices:** `{len(jobs)}`")

    for idx, j in enumerate(jobs, 1):
        items = supabase.table("job_items").select("*").eq("job_id", j["job_id"]).execute().data
        delivery = supabase.table("job_delivery").select("*").eq("job_id", j["job_id"]).execute().data
        adv = supabase.table("job_payments_advance").select("*").eq("job_id", j["job_id"]).execute().data

        deliv_info = delivery[0] if delivery else {}
        adv_info = adv[0] if adv else {}
        total_taxable = sum(i["amount"] for i in items)

        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 2, 1])
            col1.markdown(f"#### #{idx}. Job #{j['job_no']} - {j['client_name']}")
            col1.write(f"**GST No:** `{j['gst_no'] or 'N/A'}` | **PO Ref:** `{j['po_order_ref'] or 'N/A'}`")
            col1.write(f"**Billing Address:** {j['delivery_address']}")

            col2.write(f"**Challan No:** `{deliv_info.get('challan_no', 'N/A')}`")
            col2.write(f"**Delivered On:** `{deliv_info.get('delivery_date', 'N/A')}`")
            col2.write(f"**Advance Paid:** ₹ {adv_info.get('advance_po_received', 0.0):,.2f}")

            col3.metric("Taxable Total", f"₹ {total_taxable:,.2f}")

            # Specific line items
            st.markdown("##### Line Items for Invoicing:")
            for it in items:
                st.write(f"- {it['description_spec']} | Qty: {it['qty']} | Rate: ₹{it['rate']} | Amount: **₹{it['amount']:,.2f}**")

            # Checkout form
            with st.expander(f"📝 Check Out & Log Invoice Details (Job #{j['job_no']})"):
                with st.form(f"inv_form_{j['job_id']}"):
                    c_a, c_b, c_c = st.columns(3)
                    inv_no = c_a.text_input("Tax Invoice No. *", placeholder="e.g. INV/2026/045")
                    inv_date = c_b.date_input("Invoice Date", value=date.today())
                    inv_amt = c_c.number_input("Final Invoice Amount (₹) *", value=float(total_taxable), step=100.0)

                    checkout_btn = st.form_submit_button("✅ Check Out & Remove from Queue", type="primary")

                    if checkout_btn:
                        if not inv_no or inv_amt <= 0:
                            st.error("Please enter Invoice No and Valid Invoice Amount.")
                            return

                        supabase.table("job_billing").update({
                            "invoice_no": inv_no,
                            "invoice_date": str(inv_date),
                            "invoice_amount": inv_amt,
                            "billed_in_24_hrs": "Y",
                            "is_settled": True
                        }).eq("job_id", j["job_id"]).execute()

                        # Move job to settled archive
                        supabase.table("jobs").update({
                            "current_stage": "SETTLED",
                            "holding_employee_role": "Settled & Archived"
                        }).eq("job_id", j["job_id"]).execute()

                        st.success(f"Job #{j['job_no']} successfully billed and checked out!")
                        st.rerun()