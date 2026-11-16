import streamlit as st
from database import supabase, get_job_items, log_audit

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
    st.session_state["view_bill_job_id"] = None
    st.session_state["view_settled_job_id"] = None


@st.dialog("Billing & Settlement Review")
def show_billing_details_modal(job, items, user):
    """Full detail modal opened when clicking any row in Pending Billing Review."""
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    jid = job["job_id"]
    job_no = job.get("job_no", str(jid))
    total_val = sum(float(it.get("amount", 0) or 0) for it in items)

    st.markdown(f"### Billing Review Sheet: #{job_no}")
    st.caption(
        f"**Client:** {job.get('client_name')} | "
        f"**Contact:** {job.get('contact_person') or 'N/A'} ({job.get('contact_phone') or 'N/A'}) | "
        f"**Booked By:** {job.get('order_taken_by') or 'N/A'}"
    )

    if job.get("challan_no"):
        st.markdown(f"**Challan No:** `{job.get('challan_no')}`")

    st.markdown("##### Delivered Items Checklist")
    if not items:
        st.info("No line items logged for this order.")
    else:
        for idx, it in enumerate(items, 1):
            del_status = "Delivered" if it.get("is_delivered") else "Pending"
            with st.container(border=True):
                st.markdown(f"**{idx}. {it.get('item_name', 'Item')}** ({it.get('quantity')} {it.get('unit', 'Pcs')}) — Status: `{del_status}`")
                if it.get("specifications"):
                    st.caption(f"**Specs:** {it.get('specifications')}")

    st.markdown(f"#### Total Order Value: ₹ {total_val:,.2f}")
    st.markdown("---")
    st.markdown("##### Finalize & Settle Invoice")

    bill_type = st.radio("Classification", ["Non-GST", "GST"], key=f"dlg_bt_{jid}", horizontal=True)
    inv_link = st.text_input("Invoice Document Link (Optional)", placeholder="https://...", key=f"dlg_inv_{jid}")

    if st.button("Complete & Settle Job", key=f"dlg_btn_set_{jid}", type="primary", use_container_width=True):
        try:
            update_data = {
                "current_stage": "SETTLED",
                "is_billed": True,
                "billing_type": bill_type.upper(),
                "invoice_file_url": inv_link.strip() if inv_link else None,
                "invoice_uploaded_by": user["full_name"]
            }
            supabase.table("jobs").update(update_data).eq("job_id", int(jid)).execute()
            log_audit(user["user_id"], "JOB_SETTLED", f"Finalized and settled JOB-{job_no}")
            st.session_state["view_bill_job_id"] = None
            st.session_state["bill_toast_msg"] = f"Job #{job_no} marked as Settled."
            st.rerun()
        except Exception as e:
            st.error(f"Error settling job: {e}")

    st.markdown("---")
    if st.button("Close View", use_container_width=True, key=f"dlg_close_bill_{jid}"):
        st.session_state["view_bill_job_id"] = None
        st.rerun()


@st.dialog("Settled Job Archive Details")
def show_settled_details_modal(job, items):
    """Full detail modal opened when clicking any row in Settled Jobs Archive."""
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    jid = job["job_id"]
    job_no = job.get("job_no", str(jid))
    total_val = sum(float(it.get("amount", 0) or 0) for it in items)
    b_type = job.get("billing_type", "NON-GST")

    st.markdown(f"### Settled Archive Sheet: #{job_no} [{b_type}]")
    st.caption(
        f"**Client:** {job.get('client_name')} | "
        f"**Contact:** {job.get('contact_person') or 'N/A'} ({job.get('contact_phone') or 'N/A'}) | "
        f"**Billed By:** {job.get('invoice_uploaded_by') or 'Staff'}"
    )

    if job.get("challan_no"):
        st.markdown(f"**Challan No:** `{job.get('challan_no')}`")

    st.markdown("##### Settled Line Items")
    if not items:
        st.info("No line items found.")
    else:
        for idx, it in enumerate(items, 1):
            with st.container(border=True):
                st.markdown(f"**{idx}. {it.get('item_name')}** ({it.get('quantity')} {it.get('unit', 'Pcs')}) — Amount: ₹{float(it.get('amount', 0)):,.2f}")

    st.markdown(f"#### Total Settled Value: ₹ {total_val:,.2f}")

    if job.get("invoice_file_url"):
        st.markdown("---")
        st.link_button("View Invoice Document", job["invoice_file_url"], use_container_width=True)

    st.markdown("---")
    if st.button("Close View", use_container_width=True, key=f"dlg_close_settled_{jid}"):
        st.session_state["view_settled_job_id"] = None
        st.rerun()


def render(user):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)

    if st.session_state.get("bill_toast_msg"):
        st.toast(st.session_state.pop("bill_toast_msg"))
    if st.session_state.get("bill_err_msg"):
        st.error(st.session_state.pop("bill_err_msg"))

    st.subheader("Module 7: Billing & Settlement Desk")
    st.caption(f"Billing Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    tab_pending, tab_settled = st.tabs(["Pending Billing Review", "Settled Jobs Archive"])

    # --- TAB 1: PENDING BILLING REVIEW ---
    with tab_pending:
        try:
            res = (
                supabase.table("jobs")
                .select("*")
                .eq("current_stage", "BILLING_REVIEW")
                .order("job_id", desc=True)
                .execute()
            )
            jobs = res.data or []
        except Exception as e:
            st.error(f"Error fetching jobs: {e}")
            jobs = []

        # Top Filter Bar for Pending Review
        with st.container(border=True):
            f1, f2 = st.columns([7, 3])
            with f1:
                search_kw_p = st.text_input(
                    "Search Pending Billing Orders",
                    placeholder="Search Job No, Client, Contact...",
                    key="bill_search_kw_p",
                    on_change=_clear_active_modals,
                ).strip().lower()
            with f2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Reset", type="secondary", use_container_width=True, key="bill_reset_p"):
                    _clear_active_modals()
                    st.session_state["bill_search_kw_p"] = ""
                    st.rerun()

        filtered_pending = []
        for j in jobs:
            if search_kw_p:
                comb = f"{j.get('job_no', '')} {j.get('client_name', '')} {j.get('contact_person', '')} {j.get('contact_phone', '')}".lower()
                if search_kw_p not in comb:
                    continue
            filtered_pending.append(j)

        # Pagination for Pending
        ROWS_PER_PAGE = 15
        total_rec_p = len(filtered_pending)
        total_pag_p = max(1, (total_rec_p + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

        if "bill_page_p" not in st.session_state:
            st.session_state.bill_page_p = 1
        if st.session_state.bill_page_p > total_pag_p:
            st.session_state.bill_page_p = total_pag_p

        curr_page_p = st.session_state.bill_page_p
        start_p = (curr_page_p - 1) * ROWS_PER_PAGE
        end_p = min(start_p + ROWS_PER_PAGE, total_rec_p)
        page_pending = filtered_pending[start_p:end_p]

        selected_pending_ids = [
            j["job_id"] for j in page_pending
            if st.session_state.get(f"bill_chk_{j['job_id']}", False)
        ]

        # Bulk Actions Bar
        bbar1, bbar2 = st.columns([5, 5])
        with bbar1:
            st.caption(f"Showing **{start_p + 1 if total_rec_p else 0} to {end_p}** of **{total_rec_p}** pending billing orders")
        with bbar2:
            if selected_pending_ids:
                with st.popover(f"Bulk Settle ({len(selected_pending_ids)})", use_container_width=True):
                    st.markdown(f"**Settle {len(selected_pending_ids)} selected order(s) as Non-GST?**")
                    if st.button("Confirm Bulk Settlement", key="btn_bulk_settle", type="primary", use_container_width=True):
                        _clear_active_modals()
                        try:
                            for bid in selected_pending_ids:
                                supabase.table("jobs").update({
                                    "current_stage": "SETTLED",
                                    "is_billed": True,
                                    "billing_type": "NON-GST",
                                    "invoice_uploaded_by": user["full_name"]
                                }).eq("job_id", int(bid)).execute()
                                if f"bill_chk_{bid}" in st.session_state:
                                    del st.session_state[f"bill_chk_{bid}"]
                            log_audit(user["user_id"], "BULK_JOB_SETTLED", f"Settled jobs: {selected_pending_ids}")
                            st.session_state["bill_toast_msg"] = f"{len(selected_pending_ids)} order(s) marked as Settled."
                            st.rerun()
                        except Exception as e:
                            st.error(f"Bulk settlement failed: {e}")

        if not page_pending:
            st.info("No jobs pending billing review.")
        else:
            # Table Header
            st.markdown("""
                <div class="adnet-table-header" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="display: grid; grid-template-columns: 0.4fr 1.2fr 1fr 1.8fr 1.6fr 1.1fr 1.2fr 1.7fr; align-items: center; gap: 8px;">
                        <div class="tbl-cell-header">&nbsp;</div>
                        <div class="tbl-cell-header">Job No.</div>
                        <div class="tbl-cell-header">Date</div>
                        <div class="tbl-cell-header">Client</div>
                        <div class="tbl-cell-header">Contact</div>
                        <div class="tbl-cell-header">Delivery Date</div>
                        <div class="tbl-cell-header" style="text-align: right;">Total Value</div>
                        <div class="tbl-cell-header" style="text-align: center;">Action</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            def _open_bill_modal(target_jid):
                st.session_state["view_bill_job_id"] = target_jid

            for job in page_pending:
                jid = job["job_id"]
                job_no = job.get("job_no", str(jid))
                created_date = str(job.get("created_at", ""))[:10] or "N/A"
                client_name = job.get("client_name") or "N/A"
                contact_p = job.get("contact_person") or "N/A"
                contact_ph = job.get("contact_phone") or "N/A"
                due_date_str = str(job.get("due_date") or "N/A")

                items = get_job_items(jid) or []
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                contact_label = f"{contact_p} ({contact_ph})" if contact_ph != "N/A" else contact_p
                val_label = f"₹ {total_val:,.2f}"

                r_chk, r_no, r_date, r_client, r_contact, r_due, r_val, r_act = st.columns(
                    [0.4, 1.2, 1, 1.8, 1.6, 1.1, 1.2, 1.7],
                    vertical_alignment="center",
                )

                with r_chk:
                    st.checkbox(
                        " ",
                        key=f"bill_chk_{jid}",
                        label_visibility="collapsed",
                        on_change=_clear_active_modals,
                    )

                with r_no:
                    st.button(f"JOB-{job_no}", key=f"bill_btn_{jid}", type="tertiary", help="Click to view details & settle", on_click=_open_bill_modal, args=(jid,))
                with r_date:
                    st.button(created_date, key=f"bill_dt_{jid}", type="tertiary", on_click=_open_bill_modal, args=(jid,))
                with r_client:
                    st.button(client_name, key=f"bill_cl_{jid}", type="tertiary", help=client_name, on_click=_open_bill_modal, args=(jid,))
                with r_contact:
                    st.button(contact_label, key=f"bill_cp_{jid}", type="tertiary", help=contact_label, on_click=_open_bill_modal, args=(jid,))
                with r_due:
                    st.button(due_date_str, key=f"bill_due_{jid}", type="tertiary", on_click=_open_bill_modal, args=(jid,))
                with r_val:
                    st.button(val_label, key=f"bill_val_{jid}", type="tertiary", on_click=_open_bill_modal, args=(jid,))

                with r_act:
                    def _on_bill_action_change(target_job=job):
                        t_jid = target_job["job_id"]
                        choice = st.session_state.get(f"act_bill_{t_jid}")
                        if choice == "Finalize & Settle":
                            st.session_state["view_bill_job_id"] = t_jid
                        st.session_state[f"act_bill_{t_jid}"] = "Select Action"

                    st.selectbox(
                        "Action",
                        options=["Select Action", "Finalize & Settle"],
                        index=0,
                        key=f"act_bill_{jid}",
                        label_visibility="collapsed",
                        on_change=_on_bill_action_change,
                        args=(job,),
                    )

                st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

        # Modal trigger for Pending tab
        view_bill_jid = st.session_state.get("view_bill_job_id")
        if view_bill_jid:
            job_match = next((j for j in jobs if j["job_id"] == view_bill_jid), None)
            if job_match:
                job_match_items = get_job_items(view_bill_jid) or []
                show_billing_details_modal(job_match, job_match_items, user)

        # Pagination controls for Pending
        if total_pag_p > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            pc1, pc2, pc3, pc4, pc5 = st.columns([2, 1, 2, 1, 2])
            with pc2:
                if st.button("◀ Previous", disabled=(curr_page_p <= 1), use_container_width=True, key="bill_p_prev"):
                    _clear_active_modals()
                    st.session_state.bill_page_p = max(1, curr_page_p - 1)
                    st.rerun()
            with pc3:
                st.markdown(f"<div style='text-align: center; padding-top: 6px; font-size: 14px; font-weight: 600; color: #475569;'>Page {curr_page_p} of {total_pag_p}</div>", unsafe_allow_html=True)
            with pc4:
                if st.button("Next ▶", disabled=(curr_page_p >= total_pag_p), use_container_width=True, key="bill_p_next"):
                    _clear_active_modals()
                    st.session_state.bill_page_p = min(total_pag_p, curr_page_p + 1)
                    st.rerun()

    # --- TAB 2: SETTLED JOBS ARCHIVE ---
    with tab_settled:
        try:
            res_settled = (
                supabase.table("jobs")
                .select("*")
                .eq("current_stage", "SETTLED")
                .order("job_id", desc=True)
                .execute()
            )
            settled_jobs = res_settled.data or []
        except Exception:
            settled_jobs = []

        # Top Filter Bar for Settled Archive
        with st.container(border=True):
            sf1, sf2 = st.columns([7, 3])
            with sf1:
                search_kw_s = st.text_input(
                    "Search Settled Archive",
                    placeholder="Search Job No, Client, Contact...",
                    key="bill_search_kw_s",
                    on_change=_clear_active_modals,
                ).strip().lower()
            with sf2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Reset", type="secondary", use_container_width=True, key="bill_reset_s"):
                    _clear_active_modals()
                    st.session_state["bill_search_kw_s"] = ""
                    st.rerun()

        filtered_settled = []
        for sj in settled_jobs:
            if search_kw_s:
                comb_s = f"{sj.get('job_no', '')} {sj.get('client_name', '')} {sj.get('contact_person', '')} {sj.get('contact_phone', '')}".lower()
                if search_kw_s not in comb_s:
                    continue
            filtered_settled.append(sj)

        # Pagination for Settled
        total_rec_s = len(filtered_settled)
        total_pag_s = max(1, (total_rec_s + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

        if "bill_page_s" not in st.session_state:
            st.session_state.bill_page_s = 1
        if st.session_state.bill_page_s > total_pag_s:
            st.session_state.bill_page_s = total_pag_s

        curr_page_s = st.session_state.bill_page_s
        start_s = (curr_page_s - 1) * ROWS_PER_PAGE
        end_s = min(start_s + ROWS_PER_PAGE, total_rec_s)
        page_settled = filtered_settled[start_s:end_s]

        selected_settled_ids = [
            sj["job_id"] for sj in page_settled
            if st.session_state.get(f"settled_chk_{sj['job_id']}", False)
        ]

        # Settled Bulk Bar
        sbar1, sbar2 = st.columns([5, 5])
        with sbar1:
            st.caption(f"Showing **{start_s + 1 if total_rec_s else 0} to {end_s}** of **{total_rec_s}** settled archive records")
        with sbar2:
            if selected_settled_ids:
                st.caption(f"Selected: {len(selected_settled_ids)} settled job(s)")

        if not page_settled:
            st.info("No settled jobs recorded.")
        else:
            # Table Header for Settled Archive
            st.markdown("""
                <div class="adnet-table-header" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="display: grid; grid-template-columns: 0.4fr 1.2fr 1fr 1.8fr 1.6fr 1.1fr 1.2fr 1.7fr; align-items: center; gap: 8px;">
                        <div class="tbl-cell-header">&nbsp;</div>
                        <div class="tbl-cell-header">Job No.</div>
                        <div class="tbl-cell-header">Date</div>
                        <div class="tbl-cell-header">Client</div>
                        <div class="tbl-cell-header">Contact</div>
                        <div class="tbl-cell-header">Type</div>
                        <div class="tbl-cell-header" style="text-align: right;">Total Value</div>
                        <div class="tbl-cell-header" style="text-align: center;">Action</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            def _open_settled_modal(target_jid):
                st.session_state["view_settled_job_id"] = target_jid

            for sj in page_settled:
                jid = sj["job_id"]
                job_no = sj.get("job_no", str(jid))
                created_date = str(sj.get("created_at", ""))[:10] or "N/A"
                client_name = sj.get("client_name") or "N/A"
                contact_p = sj.get("contact_person") or "N/A"
                contact_ph = sj.get("contact_phone") or "N/A"
                b_type = sj.get("billing_type", "NON-GST")

                s_items = get_job_items(jid) or []
                s_total = sum(float(it.get("amount", 0) or 0) for it in s_items)
                contact_label = f"{contact_p} ({contact_ph})" if contact_ph != "N/A" else contact_p
                val_label = f"₹ {s_total:,.2f}"

                r_chk, r_no, r_date, r_client, r_contact, r_type, r_val, r_act = st.columns(
                    [0.4, 1.2, 1, 1.8, 1.6, 1.1, 1.2, 1.7],
                    vertical_alignment="center",
                )

                with r_chk:
                    st.checkbox(
                        " ",
                        key=f"settled_chk_{jid}",
                        label_visibility="collapsed",
                        on_change=_clear_active_modals,
                    )

                with r_no:
                    st.button(f"JOB-{job_no}", key=f"settled_btn_{jid}", type="tertiary", help="Click to view archive details", on_click=_open_settled_modal, args=(jid,))
                with r_date:
                    st.button(created_date, key=f"settled_dt_{jid}", type="tertiary", on_click=_open_settled_modal, args=(jid,))
                with r_client:
                    st.button(client_name, key=f"settled_cl_{jid}", type="tertiary", help=client_name, on_click=_open_settled_modal, args=(jid,))
                with r_contact:
                    st.button(contact_label, key=f"settled_cp_{jid}", type="tertiary", help=contact_label, on_click=_open_settled_modal, args=(jid,))
                with r_type:
                    st.button(b_type, key=f"settled_tp_{jid}", type="tertiary", on_click=_open_settled_modal, args=(jid,))
                with r_val:
                    st.button(val_label, key=f"settled_val_{jid}", type="tertiary", on_click=_open_settled_modal, args=(jid,))

                with r_act:
                    if sj.get("invoice_file_url"):
                        st.link_button("View Invoice", sj["invoice_file_url"], use_container_width=True, key=f"link_inv_{jid}")
                    else:
                        st.button("View Archive", key=f"settled_act_{jid}", type="secondary", use_container_width=True, on_click=_open_settled_modal, args=(jid,))

                st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

        # Modal trigger for Settled tab
        view_settled_jid = st.session_state.get("view_settled_job_id")
        if view_settled_jid:
            sj_match = next((sj for sj in settled_jobs if sj["job_id"] == view_settled_jid), None)
            if sj_match:
                sj_match_items = get_job_items(view_settled_jid) or []
                show_settled_details_modal(sj_match, sj_match_items)

        # Pagination controls for Settled Archive
        if total_pag_s > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            sc1, sc2, sc3, sc4, sc5 = st.columns([2, 1, 2, 1, 2])
            with sc2:
                if st.button("◀ Previous", disabled=(curr_page_s <= 1), use_container_width=True, key="settled_p_prev"):
                    _clear_active_modals()
                    st.session_state.bill_page_s = max(1, curr_page_s - 1)
                    st.rerun()
            with sc3:
                st.markdown(f"<div style='text-align: center; padding-top: 6px; font-size: 14px; font-weight: 600; color: #475569;'>Page {curr_page_s} of {total_pag_s}</div>", unsafe_allow_html=True)
            with sc4:
                if st.button("Next ▶", disabled=(curr_page_s >= total_pag_s), use_container_width=True, key="settled_p_next"):
                    _clear_active_modals()
                    st.session_state.bill_page_s = min(total_pag_s, curr_page_s + 1)
                    st.rerun()