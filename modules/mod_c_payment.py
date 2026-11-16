from datetime import date, datetime
import streamlit as st
from database import supabase, get_job_items, record_payment_and_release, log_audit

# ALI Theme: Unified Font, Size & Color across Main View and All Dialogs
_UNIFORM_MODULE_CSS = """
    <style>
    /* Base uniform typography for main view and modals */
    div[data-testid="stAppViewContainer"] .main p,
    div[data-testid="stAppViewContainer"] .main span,
    div[data-testid="stAppViewContainer"] .main label,
    div[data-testid="stAppViewContainer"] .main input,
    div[data-testid="stAppViewContainer"] .main textarea,
    div[data-testid="stAppViewContainer"] .main select,
    div[data-testid="stAppViewContainer"] .main div[data-testid="stCaptionContainer"] p,
    div[data-testid="stAppViewContainer"] .main div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stAppViewContainer"] .main div[data-baseweb="select"] div,
    div[data-testid="stAppViewContainer"] .main div[data-baseweb="input"] input,
    div[data-testid="stDialog"] p,
    div[data-testid="stDialog"] span,
    div[data-testid="stDialog"] label,
    div[data-testid="stDialog"] input,
    div[data-testid="stDialog"] textarea,
    div[data-testid="stDialog"] select,
    div[data-testid="stDialog"] div[data-testid="stCaptionContainer"] p,
    div[data-testid="stDialog"] div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stDialog"] div[data-baseweb="select"] div,
    div[data-testid="stDialog"] div[data-baseweb="input"] input {
        font-family: inherit !important;
        font-size: 13px !important;
        color: #1e293b !important;
    }

    /* Unified Section & Dialog Subheaders */
    div[data-testid="stAppViewContainer"] .main h3,
    div[data-testid="stAppViewContainer"] .main h4,
    div[data-testid="stAppViewContainer"] .main h5,
    div[data-testid="stDialog"] h3,
    div[data-testid="stDialog"] h4,
    div[data-testid="stDialog"] h5 {
        font-family: inherit !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #1e293b !important;
    }

    /* Keep primary action buttons readable */
    div[data-testid="stAppViewContainer"] .main button[kind="primary"] p,
    div[data-testid="stAppViewContainer"] .main button[kind="primary"] span,
    div[data-testid="stDialog"] button[kind="primary"] p,
    div[data-testid="stDialog"] button[kind="primary"] span {
        color: #ffffff !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    /* Table Header & Cell Styles */
    .tbl-cell-header {
        font-size: 13px !important;
        font-family: inherit !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }

    /* Checkbox & Dropdown Vertical Alignment inside 38px rows */
    div[data-testid="stCheckbox"] {
        display: flex;
        align-items: center;
        height: 38px;
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stCheckbox"] label {
        margin-bottom: 0 !important;
    }
    div[data-testid="stSelectbox"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }

    /* Flat clickable text styling in Table (tertiary only, preserves secondary button borders) */
    div[data-testid="stHorizontalBlock"] button[kind="tertiary"] {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 6px 0 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        font-family: inherit !important;
        color: #1e293b !important;
        text-align: left !important;
        justify-content: flex-start !important;
        align-items: center !important;
        display: flex !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        width: 100% !important;
        line-height: 1.4 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="tertiary"]:hover {
        color: #E11D48 !important;
        text-decoration: underline !important;
        background: transparent !important;
    }
    </style>
"""


def _clear_active_modals():
    st.session_state["pay_view_jid"] = None


@st.dialog("Jobsheet & Payment Details")
def _show_payment_details_modal(entry, user):
    """Compact ALI Theme modal displaying jobsheet particulars, line items, and advance/credit clearance controls."""
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)

    job = entry["job"]
    items = entry["items"]
    total_order_val = entry["total_val"]
    is_priority = entry["is_priority"]
    job_id = job["job_id"]
    job_no = job.get("job_no", str(job_id))

    st.markdown(f"### JOB-{job_no} — {job.get('client_name') or 'N/A'}")
    st.caption(
        f"**Booked Date:** `{str(job.get('created_at', ''))[:10] or 'N/A'}` | "
        f"**Target Due Date:** `{job.get('due_date') or 'N/A'}` | "
        f"**Booked By:** `{job.get('order_taken_by') or 'Sales'}`"
    )

    if is_priority:
        st.error("Priority / Urgent Order (Due within 24 hours or overdue)")
    if job.get("is_returned"):
        st.warning(f"Flagged Notice: {job.get('return_reason')}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Contact Person:**\n{job.get('contact_person') or 'N/A'}")
    with c2:
        st.markdown(f"**Phone:**\n{job.get('contact_phone') or 'N/A'}")
    with c3:
        st.markdown(f"**Billing Type:**\n{'GST Tax Invoice' if job.get('billing_type') == 'GST' else 'Non-GST Bill'}")

    if job.get("billing_type") == "GST":
        st.caption(f"**GSTIN:** `{job.get('gstin') or 'N/A'}` | **Place of Supply:** `{job.get('place_of_supply') or 'N/A'}`")
    if job.get("billing_address"):
        st.caption(f"**Billing Address:** {job.get('billing_address')}")

    st.markdown("---")
    st.markdown("##### Ordered Line Items & Commercials")
    if not items:
        st.info("No line items logged for this order.")
    else:
        for idx, it in enumerate(items, 1):
            with st.container(border=True):
                ic1, ic2 = st.columns([6.5, 3.5])
                with ic1:
                    st.markdown(f"**{idx}. {it.get('item_name')}**")
                    if it.get("specifications"):
                        st.caption(f"Specs: {it.get('specifications')}")
                    if it.get("delivery_address"):
                        st.caption(f"Destination: {it.get('delivery_address')}")
                with ic2:
                    st.markdown(
                        f"<div style='text-align: right; font-size: 13px; color: #1e293b;'>"
                        f"Qty: <b>{it.get('quantity')} {it.get('unit', 'Pcs')}</b><br>"
                        f"Rate: ₹{float(it.get('rate', 0)):,.2f}<br>"
                        f"<b>Total: ₹{float(it.get('amount', 0)):,.2f}</b>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    st.markdown(f"#### Total Order Value: ₹ {total_order_val:,.2f}")
    st.markdown("---")
    st.markdown("##### Payment Entry & Commercial Clearance")

    p1, p2 = st.columns(2)
    with p1:
        po_number = st.text_input(
            "Client P.O. No. (Optional)",
            value=job.get("po_no") or "",
            placeholder="e.g. PO/2026/8941",
            key=f"dlg_po_{job_id}",
        ).strip()
    with p2:
        adv_amt = st.number_input(
            "Advance Amount Received (₹)",
            min_value=0.0,
            max_value=float(total_order_val),
            value=0.0,
            step=100.0,
            key=f"dlg_adv_{job_id}",
        )

    p3, p4, p5 = st.columns(3)
    with p3:
        pay_mode = st.selectbox(
            "Payment Mode *",
            ["UPI", "NEFT/RTGS", "Cheque", "Cash", "Bank Transfer"],
            key=f"dlg_mode_{job_id}",
        )
    with p4:
        ref_no = st.text_input(
            "Transaction / Ref No.",
            placeholder="e.g. UTR / Cheque",
            key=f"dlg_ref_{job_id}",
        ).strip()
    with p5:
        pay_date = st.date_input(
            "Payment Date",
            value=date.today(),
            key=f"dlg_pdate_{job_id}",
        )

    pending_balance = max(0.0, round(total_order_val - adv_amt, 2))
    st.markdown(f"**Pending Balance to Collect:** `₹ {pending_balance:,.2f}`")

    notes = st.text_input(
        "Accounts Notes / Remarks (Optional)",
        placeholder="e.g. 50% advance confirmed / Cheque subject to realization",
        key=f"dlg_notes_{job_id}",
    ).strip()

    b1, b2 = st.columns(2)
    with b1:
        if st.button("Clear & Release to Production", key=f"dlg_rel_{job_id}", type="primary", use_container_width=True):
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
                is_credit=False,
            )
            if ok:
                log_audit(user["user_id"], "PAYMENT_CLEARED", f"Cleared advance ₹{adv_amt:,.2f} for JOB-{job_no}")
                st.session_state["pay_view_jid"] = None
                st.session_state["pay_toast_msg"] = f"Job #{job_no} cleared and pushed to PRODUCTION!"
                st.rerun()
            else:
                st.error(f"Error updating payment: {msg}")

    with b2:
        if st.button("Approve on Credit (Zero Advance)", key=f"dlg_crd_{job_id}", use_container_width=True):
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
                is_credit=True,
            )
            if ok:
                log_audit(user["user_id"], "CREDIT_APPROVED", f"Approved zero-advance credit for JOB-{job_no}")
                st.session_state["pay_view_jid"] = None
                st.session_state["pay_toast_msg"] = f"Job #{job_no} approved on credit and released to PRODUCTION!"
                st.rerun()
            else:
                st.error(f"Error releasing credit job: {msg}")


def render(user):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)

    if st.session_state.get("pay_toast_msg"):
        st.toast(st.session_state.pop("pay_toast_msg"))
    if st.session_state.get("pay_err_msg"):
        st.error(st.session_state.pop("pay_err_msg"))

    st.subheader("Module 3: Advance Clearance & Accounts Desk")
    st.caption(
        f"Accounts Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    # 1. Fetch jobs currently queued for PAYMENT clearance
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "PAYMENT")
            .order("job_id", desc=True)
            .execute()
        )
        payment_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching payment queue: {e}")
        return

    # Calculate Overview Metrics & Metadata
    total_queue_jobs = len(payment_jobs)
    priority_count = 0
    total_pipeline_val = 0.0

    jobs_with_meta = []
    for j in payment_jobs:
        items = get_job_items(j["job_id"]) or []
        job_val = sum(float(it.get("amount", 0) or 0) for it in items)
        total_pipeline_val += job_val

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
            "is_priority": is_priority,
        })

    # --- QUEUE STATUS & OVERVIEW CARD ---
    with st.container(border=True):
        st.markdown("#### Queue Status & Accounts Overview")
        m1, m2, m3 = st.columns(3)
        m1.metric("Orders Pending Clearance", f"{total_queue_jobs} Orders")
        m2.metric("Total Pending Pipeline Value", f"₹ {total_pipeline_val:,.2f}")
        m3.metric("Priority / Flagged Jobs", f"{priority_count} Orders")

    if not payment_jobs:
        st.success("Accounts queue is clear! No orders pending advance or credit clearance.")
        return

    # Callback to reset filters
    def _reset_payment_filters():
        _clear_active_modals()
        st.session_state["pay_search_kw"] = ""
        st.session_state["pay_priority_filter"] = "All Orders"
        st.session_state["pay_sort_filter"] = "Recent Jobs (Newest First)"
        st.session_state["pay_page_num"] = 1

    # --- Top Filter Bar ---
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([3.5, 2.5, 2.5, 1.5])
        with f1:
            search_kw = st.text_input(
                "Search Orders",
                placeholder="Job No, Client, Contact...",
                key="pay_search_kw",
                on_change=_clear_active_modals,
            ).strip().lower()
        with f2:
            sel_prio = st.selectbox(
                "Queue Filter",
                options=["All Orders", "Priority / Urgent", "Normal"],
                index=0,
                key="pay_priority_filter",
                on_change=_clear_active_modals,
            )
        with f3:
            sort_order = st.selectbox(
                "Sort By",
                options=["Recent Jobs (Newest First)", "Oldest Jobs", "Delivery Due Soonest", "Highest Order Value"],
                key="pay_sort_filter",
                on_change=_clear_active_modals,
            )
        with f4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "Reset Filters",
                type="secondary",
                use_container_width=True,
                key="pay_reset_btn",
                on_click=_reset_payment_filters,
            )

    # --- Filter Logic ---
    filtered_entries = []
    for entry in jobs_with_meta:
        j = entry["job"]
        if sel_prio == "Priority / Urgent" and not entry["is_priority"]:
            continue
        elif sel_prio == "Normal" and entry["is_priority"]:
            continue

        if search_kw:
            comb = f"{j.get('job_no', '')} {j.get('client_name', '')} {j.get('contact_person', '')} {j.get('contact_phone', '')}".lower()
            if search_kw not in comb:
                continue

        filtered_entries.append(entry)

    # --- Sorting Logic ---
    if sort_order == "Recent Jobs (Newest First)":
        filtered_entries.sort(key=lambda x: x["job"].get("job_id", 0), reverse=True)
    elif sort_order == "Oldest Jobs":
        filtered_entries.sort(key=lambda x: x["job"].get("job_id", 0))
    elif sort_order == "Delivery Due Soonest":
        filtered_entries.sort(key=lambda x: str(x["job"].get("due_date", "9999-99-99")))
    elif sort_order == "Highest Order Value":
        filtered_entries.sort(key=lambda x: x["total_val"], reverse=True)

    # --- 15-Row Pagination ---
    ROWS_PER_PAGE = 15
    total_records = len(filtered_entries)
    total_pages = max(1, (total_records + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

    if "pay_page_num" not in st.session_state:
        st.session_state.pay_page_num = 1
    if st.session_state.pay_page_num > total_pages:
        st.session_state.pay_page_num = total_pages

    curr_page = st.session_state.pay_page_num
    start_idx = (curr_page - 1) * ROWS_PER_PAGE
    end_idx = min(start_idx + ROWS_PER_PAGE, total_records)
    page_entries = filtered_entries[start_idx:end_idx]

    # Selected rows on active page
    selected_entries = [
        e for e in page_entries
        if st.session_state.get(f"pay_chk_{e['job']['job_id']}", False)
    ]

    # --- Top Bar: Counter & Bulk Clearance Controls ---
    tbar1, tbar2 = st.columns([5, 5])
    with tbar1:
        st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** pending accounts orders")

    with tbar2:
        if selected_entries:
            b_col_adv, b_col_crd = st.columns(2)

            with b_col_adv:
                with st.popover(f"Bulk Clear Advance ({len(selected_entries)})", use_container_width=True):
                    st.markdown(f"**Clear Full Advance for {len(selected_entries)} Order(s)?**")
                    bulk_pay_mode = st.selectbox(
                        "Payment Mode *",
                        ["UPI", "NEFT/RTGS", "Cheque", "Cash", "Bank Transfer"],
                        key="bulk_pay_mode_sel",
                    )
                    bulk_ref_no = st.text_input("Batch Ref / Remarks (Optional)", placeholder="e.g. Bulk NEFT / Verified", key="bulk_pay_ref_inp").strip()
                    if st.button("Confirm Bulk Advance Clearance", type="primary", use_container_width=True, key="btn_confirm_bulk_adv"):
                        _clear_active_modals()
                        cleared_cnt = 0
                        for e in selected_entries:
                            j_obj = e["job"]
                            jid_val = j_obj["job_id"]
                            val = float(e["total_val"])
                            ok, _ = record_payment_and_release(
                                job_id=jid_val,
                                user_name=user["full_name"],
                                advance_received=val,
                                balance_remaining=0.0,
                                payment_mode=bulk_pay_mode,
                                ref_no=bulk_ref_no or "BULK_CLEARANCE",
                                payment_date=date.today(),
                                notes=bulk_ref_no or "Bulk full advance cleared by Accounts.",
                                is_credit=False,
                            )
                            if ok:
                                cleared_cnt += 1
                                if f"pay_chk_{jid_val}" in st.session_state:
                                    del st.session_state[f"pay_chk_{jid_val}"]
                        if cleared_cnt:
                            log_audit(user["user_id"], "BULK_PAYMENT_CLEARED", f"Cleared {cleared_cnt} jobs in bulk")
                            st.session_state["pay_toast_msg"] = f"{cleared_cnt} order(s) cleared and released to PRODUCTION!"
                        st.rerun()

            with b_col_crd:
                with st.popover(f"Bulk Credit Approve ({len(selected_entries)})", use_container_width=True):
                    st.markdown(f"**Approve {len(selected_entries)} Order(s) on Credit?**")
                    st.caption("Releases selected orders to PRODUCTION with zero upfront advance.")
                    bulk_crd_note = st.text_input("Credit Remarks (Optional)", placeholder="e.g. Corporate ledger approved", key="bulk_crd_note_inp").strip()
                    if st.button("Confirm Bulk Credit Approval", type="primary", use_container_width=True, key="btn_confirm_bulk_crd"):
                        _clear_active_modals()
                        crd_cnt = 0
                        for e in selected_entries:
                            j_obj = e["job"]
                            jid_val = j_obj["job_id"]
                            val = float(e["total_val"])
                            ok, _ = record_payment_and_release(
                                job_id=jid_val,
                                user_name=user["full_name"],
                                advance_received=0.0,
                                balance_remaining=val,
                                payment_mode="CREDIT",
                                ref_no="PRE_APPROVED_CREDIT",
                                payment_date=date.today(),
                                notes=bulk_crd_note or "Bulk corporate credit pre-approved.",
                                is_credit=True,
                            )
                            if ok:
                                crd_cnt += 1
                                if f"pay_chk_{jid_val}" in st.session_state:
                                    del st.session_state[f"pay_chk_{jid_val}"]
                        if crd_cnt:
                            log_audit(user["user_id"], "BULK_CREDIT_APPROVED", f"Approved {crd_cnt} credit jobs in bulk")
                            st.session_state["pay_toast_msg"] = f"{crd_cnt} order(s) approved on credit and released to PRODUCTION!"
                        st.rerun()

    if not page_entries:
        st.info("No matching orders found in Accounts queue.")
        return

    # --- Table Header Bar (ALI Theme) ---
    st.markdown("""
        <div class="adnet-table-header" style="padding: 10px 14px;">
            <div style="display: grid; grid-template-columns: 0.3fr 1fr 1fr 2fr 1.8fr 1.1fr 1.1fr 1.7fr; align-items: center; gap: 8px;">
                <div class="tbl-cell-header">&nbsp;</div>
                <div class="tbl-cell-header">Job No.</div>
                <div class="tbl-cell-header">Date</div>
                <div class="tbl-cell-header">Client</div>
                <div class="tbl-cell-header">Contact</div>
                <div class="tbl-cell-header">Amount</div>
                <div class="tbl-cell-header">Delivery Date</div>
                <div class="tbl-cell-header" style="text-align: center;">Action</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    def _open_view_modal(target_jid):
        st.session_state["pay_view_jid"] = target_jid

    # --- Table Data Rows ---
    for entry in page_entries:
        j = entry["job"]
        jid = j["job_id"]
        job_no = j.get("job_no", str(jid))
        created_date = str(j.get("created_at", ""))[:10] or "N/A"
        client_name = j.get("client_name") or "N/A"
        contact_p = j.get("contact_person") or "N/A"
        contact_ph = j.get("contact_phone") or "N/A"
        due_date_str = str(j.get("due_date") or "N/A")
        contact_label = f"{contact_p} ({contact_ph})" if contact_ph != "N/A" else contact_p
        amt_label = f"₹{entry['total_val']:,.2f}"

        r_chk, r_no, r_date, r_client, r_contact, r_amt, r_due, r_act = st.columns(
            [0.3, 1, 1, 2, 1.8, 1.1, 1.1, 1.7],
            vertical_alignment="center",
        )

        with r_chk:
            st.checkbox(
                " ",
                key=f"pay_chk_{jid}",
                label_visibility="collapsed",
                on_change=_clear_active_modals,
            )

        with r_no:
            st.button(
                f"JOB-{job_no}",
                key=f"pay_m_no_{jid}",
                type="tertiary",
                help="Click to view details & record payment",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_date:
            st.button(
                created_date,
                key=f"pay_m_dt_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_client:
            st.button(
                client_name,
                key=f"pay_m_cl_{jid}",
                type="tertiary",
                help=client_name,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_contact:
            st.button(
                contact_label,
                key=f"pay_m_cp_{jid}",
                type="tertiary",
                help=contact_label,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_amt:
            st.button(
                amt_label,
                key=f"pay_m_amt_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_due:
            st.button(
                due_date_str,
                key=f"pay_m_due_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_act:
            def _on_pay_action_change(target_entry=entry):
                t_job = target_entry["job"]
                t_jid = t_job["job_id"]
                t_jno = t_job.get("job_no", str(t_jid))
                choice = st.session_state.get(f"pay_act_drp_{t_jid}")
                if choice == "Record Payment":
                    st.session_state["pay_view_jid"] = t_jid
                elif choice == "Clear Full Advance":
                    st.session_state["pay_view_jid"] = None
                    ok, msg = record_payment_and_release(
                        job_id=t_jid,
                        user_name=user["full_name"],
                        advance_received=float(target_entry["total_val"]),
                        balance_remaining=0.0,
                        payment_mode="UPI",
                        ref_no="QUICK_CLEARANCE",
                        payment_date=date.today(),
                        notes="Full advance cleared via quick action.",
                        is_credit=False,
                    )
                    if ok:
                        log_audit(user["user_id"], "PAYMENT_CLEARED", f"Quick-cleared JOB-{t_jno}")
                        st.session_state["pay_toast_msg"] = f"Job #{t_jno} cleared and pushed to PRODUCTION!"
                    else:
                        st.session_state["pay_err_msg"] = f"Error clearing Job #{t_jno}: {msg}"
                elif choice == "Approve on Credit":
                    st.session_state["pay_view_jid"] = None
                    ok, msg = record_payment_and_release(
                        job_id=t_jid,
                        user_name=user["full_name"],
                        advance_received=0.0,
                        balance_remaining=float(target_entry["total_val"]),
                        payment_mode="CREDIT",
                        ref_no="PRE_APPROVED_CREDIT",
                        payment_date=date.today(),
                        notes="Corporate credit pre-approved. Zero advance collected.",
                        is_credit=True,
                    )
                    if ok:
                        log_audit(user["user_id"], "CREDIT_APPROVED", f"Quick-approved credit for JOB-{t_jno}")
                        st.session_state["pay_toast_msg"] = f"Job #{t_jno} approved on credit and released to PRODUCTION!"
                    else:
                        st.session_state["pay_err_msg"] = f"Error approving credit for Job #{t_jno}: {msg}"
                st.session_state[f"pay_act_drp_{t_jid}"] = "Select Action"

            st.selectbox(
                "Action",
                options=["Select Action", "Record Payment", "Clear Full Advance", "Approve on Credit"],
                index=0,
                key=f"pay_act_drp_{jid}",
                label_visibility="collapsed",
                on_change=_on_pay_action_change,
                args=(entry,),
            )

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

    # Open Jobsheet & Payment Details Modal when any row text or "Record Payment" is clicked
    view_jid = st.session_state.get("pay_view_jid")
    if view_jid:
        target_entry = next((x for x in jobs_with_meta if x["job"]["job_id"] == view_jid), None)
        if target_entry:
            _show_payment_details_modal(target_entry, user)

    # --- 15-Row Pagination Footer ---
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        p_cols = st.columns([2, 1, 1, 1, 1, 1, 2])
        with p_cols[1]:
            if st.button("<", disabled=(curr_page == 1), key="pay_p_prev_btn", use_container_width=True):
                _clear_active_modals()
                st.session_state.pay_page_num = max(1, curr_page - 1)
                st.rerun()

        for p_idx in range(1, min(total_pages + 1, 5)):
            with p_cols[1 + p_idx]:
                is_active = (p_idx == curr_page)
                btn_type = "primary" if is_active else "secondary"
                if st.button(str(p_idx), type=btn_type, key=f"pay_p_btn_{p_idx}", use_container_width=True):
                    _clear_active_modals()
                    st.session_state.pay_page_num = p_idx
                    st.rerun()

        with p_cols[6]:
            if st.button(">", disabled=(curr_page == total_pages), key="pay_p_next_btn", use_container_width=True):
                _clear_active_modals()
                st.session_state.pay_page_num = min(total_pages, curr_page + 1)
                st.rerun()