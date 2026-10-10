from datetime import date, datetime
import streamlit as st
from database import supabase, get_job_items, record_payment_and_release


def render(user):
    st.subheader("💳 Module 3: Advance Clearance & Accounts Desk")
    st.caption(
        f"Accounts Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    # 1. Fetch jobs currently queued for PAYMENT clearance
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "PAYMENT")
            .order("job_id")
            .execute()
        )
        payment_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching payment queue: {e}")
        return

    # Calculate Overview Metrics
    total_queue_jobs = len(payment_jobs)
    priority_count = 0
    total_pipeline_val = 0.0

    jobs_with_meta = []
    for j in payment_jobs:
        items = get_job_items(j["job_id"])
        job_val = sum(float(it.get("amount", 0) or 0) for it in items)
        total_pipeline_val += job_val

        # Urgent / Priority assessment (overdue or due within 24h)
        is_priority = False
        if j.get("due_date"):
            try:
                due_d = datetime.strptime(str(j["due_date"]), "%Y-%m-%d").date()
                if (due_d - date.today()).days <= 1:
                    is_priority = True
                    priority_count += 1
            except Exception:
                pass
        
        if j.get("is_returned"):
            priority_count += 1

        jobs_with_meta.append({
            "job": j,
            "items": items,
            "total_val": job_val,
            "is_priority": is_priority
        })

    # --- QUEUE STATUS & OVERVIEW CARD ---
    with st.container(border=True):
        st.markdown("#### 📊 Queue Status & Accounts Overview")
        m1, m2, m3 = st.columns(3)
        m1.metric("Orders Pending Clearance", f"{total_queue_jobs} Orders")
        m2.metric("Total Pending Pipeline Value", f"₹ {total_pipeline_val:,.2f}")
        m3.metric("Priority / Flagged Jobs", f"{priority_count} Orders")

    st.markdown("---")

    if not payment_jobs:
        st.success("✅ Accounts queue is clear! No orders pending advance or credit clearance.")
        return

    # --- SINGLE-LIST JOBS DISPLAY ---
    for entry in jobs_with_meta:
        job = entry["job"]
        items = entry["items"]
        total_order_val = entry["total_val"]
        is_priority = entry["is_priority"]
        job_id = job["job_id"]

        with st.container(border=True):
            # 1. Job Commercial Header
            h_col1, h_col2, h_col3 = st.columns([3, 2, 1.5])
            with h_col1:
                st.markdown(f"### Job #{job.get('job_no')} — {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
            with h_col2:
                due_tag = f"📅 Due: **{job.get('due_date')}**"
                if is_priority:
                    st.error(f"🔥 **PRIORITY / URGENT** | {due_tag}")
                else:
                    st.info(f"⏳ Normal | {due_tag}")
                st.caption(f"Booked by: **{job.get('order_taken_by') or 'N/A'}**")
            with h_col3:
                st.metric("Total Order Value", f"₹ {total_order_val:,.2f}")

            if job.get("is_returned"):
                st.warning(f"⚠️ Flagged Return: {job.get('return_reason')}")

            # 2. Client Financial Terms
            billing_type = job.get("billing_type", "NON_GST")
            t_col1, t_col2 = st.columns([2, 4])
            with t_col1:
                term_mode = st.radio(
                    "Client Financial Terms:",
                    ["Advance Client (Upfront Required)", "Credit / Corporate Client (Pre-Approved Ledger)"],
                    key=f"terms_{job_id}",
                    index=0
                )
            # with t_col2:
            #     if "Advance Client" in term_mode:
            #         st.caption("ℹ️ **Standard Policy:** Minimum deposit / advance payment is required before production floor kicks off.")
            #     else:
            #         st.caption("ℹ️ **Corporate Policy:** Pre-approved client running on credit terms. Job can proceed with zero upfront deposit.")

            st.markdown("##### 📝 Ordered Line Items Summary")
            for idx, it in enumerate(items, 1):
                st.caption(f"• **{it.get('item_name')}** | Qty: {it.get('quantity')} {it.get('unit')} | Amount: ₹{float(it.get('amount', 0)):,.2f}")

            st.markdown("---")

            # 3. Payment Entry Inputs & Live Balance Calculator
            st.markdown("##### 💵 Payment Entry & Commercial Clearance")
            p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns(5)

            with p_c1:
                po_number = st.text_input(
                    "Client P.O. No. (Optional)",
                    value=job.get("po_no") or "",
                    placeholder="e.g. PO/2026/8941",
                    key=f"po_{job_id}"
                ).strip()

            with p_c2:
                adv_amt = st.number_input(
                    "Advance Amount Received (₹)",
                    min_value=0.0,
                    max_value=float(total_order_val),
                    value=0.0,
                    step=100.0,
                    key=f"adv_{job_id}"
                )

            with p_c3:
                pay_mode = st.selectbox(
                    "Payment Mode *",
                    ["UPI", "NEFT/RTGS", "Cheque", "Cash", "Bank Transfer"],
                    key=f"mode_{job_id}"
                )

            with p_c4:
                ref_no = st.text_input(
                    "Transaction / Ref No.",
                    placeholder="e.g. UTR / Cheque / Ref",
                    key=f"ref_{job_id}"
                )

            with p_c5:
                pay_date = st.date_input(
                    "Payment Date",
                    value=date.today(),
                    key=f"pdate_{job_id}"
                )

            # Live Balance Computation
            pending_balance = max(0.0, round(total_order_val - adv_amt, 2))
            bal_col1, bal_col2 = st.columns([2, 4])
            with bal_col1:
                st.metric("Pending Balance to Collect", f"₹ {pending_balance:,.2f}")
            with bal_col2:
                notes = st.text_input(
                    "Accounts Notes / Remarks (Optional)",
                    placeholder="e.g. Cheque received subject to realization / 50% advance confirmed by accounts",
                    key=f"notes_{job_id}"
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # 4. Routing Action Controls
            b_c1, b_c2 = st.columns(2)
            with b_c1:
                if st.button("🚀 Clear & Release to Production", key=f"btn_rel_{job_id}", type="primary", use_container_width=True):
                    if po_number:
                        supabase.table("jobs").update({"po_no": po_number}).eq("job_id", job_id).execute()

                    ok, msg = record_payment_and_release(
                        job_id=job_id,
                        user_name=user["full_name"],
                        advance_received=adv_amt,
                        balance_remaining=pending_balance,
                        payment_mode=pay_mode,
                        ref_no=ref_no,
                        payment_date=pay_date,
                        notes=notes,
                        is_credit=False
                    )
                    if ok:
                        st.success(f"Job #{job.get('job_no')} cleared and pushed to PRODUCTION!")
                        st.rerun()
                    else:
                        st.error(f"Error updating payment: {msg}")

            with b_c2:
                if st.button("📑 Approve on Credit (Zero Advance)", key=f"btn_crd_{job_id}", use_container_width=True):
                    if po_number:
                        supabase.table("jobs").update({"po_no": po_number}).eq("job_id", job_id).execute()

                    ok, msg = record_payment_and_release(
                        job_id=job_id,
                        user_name=user["full_name"],
                        advance_received=0.0,
                        balance_remaining=total_order_val,
                        payment_mode="CREDIT",
                        ref_no="PRE_APPROVED_CREDIT",
                        payment_date=date.today(),
                        notes="Corporate credit pre-approved. Zero advance collected." if not notes else notes,
                        is_credit=True
                    )
                    if ok:
                        st.info(f"Job #{job.get('job_no')} approved on credit and released to PRODUCTION!")
                        st.rerun()
                    else:
                        st.error(f"Error releasing credit job: {msg}")