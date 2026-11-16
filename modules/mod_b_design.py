from datetime import date, datetime
import streamlit as st
from database import (
    supabase,
    get_job_items,
    bulk_approve_design_jobs,
    bulk_reject_design_jobs,
    reject_job_to_sales,
    log_audit,
)

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
    st.session_state["des_view_jid"] = None


@st.dialog("Jobsheet Details")
def show_jobsheet_spec_modal(job):
    """Displays jobsheet particulars and pre-press specifications with all monetary values masked."""
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    items = get_job_items(job["job_id"])

    # 1. Header Information
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Job No:** `JOB-{job.get('job_no')}`")
        st.markdown(f"**Client:** {job.get('client_name') or 'N/A'}")
        st.caption(f"Contact Person: {job.get('contact_person') or 'N/A'}")
        st.caption(f"Phone: {job.get('contact_phone') or 'N/A'}")
    with c2:
        st.markdown(f"**Target Due Date:** {job.get('due_date') or 'N/A'}")
        st.markdown(f"**Booked By:** {job.get('order_taken_by') or 'Sales'}")
        st.caption(f"Assigned Artist: `{job.get('assigned_designer') or 'Unassigned'}`")

    if job.get("is_returned"):
        st.error(f"Return / Flagged Notice: {job.get('return_reason')}")

    st.markdown("---")
    st.markdown("##### Pre-Press Items & Specifications")

    if not items:
        st.info("No line items logged for this order.")
    else:
        for idx, it in enumerate(items, 1):
            with st.container(border=True):
                st.markdown(f"**{idx}. {it.get('item_name')}** — Quantity: `{it.get('quantity')} {it.get('unit')}`")
                spec_text = it.get("specifications") or "No technical notes entered."
                st.caption("Technical Notes / Sizes:")
                st.code(spec_text, language="markdown")
                if it.get("delivery_address"):
                    st.caption(f"Destination: {it.get('delivery_address')}")

    if st.button("Close", use_container_width=True, key=f"cls_view_des_{job['job_id']}"):
        st.session_state["des_view_jid"] = None
        st.rerun()


def render(user):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    st.subheader("Module 2: Design Approval & Proofing Desk")
    st.caption(
        f"Graphic Artist / Pre-Press: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    is_privileged = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]

    # 1. Fetch jobs currently at DESIGN stage
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "DESIGN")
            .order("job_id", desc=True)
            .execute()
        )
        all_design_jobs = res.data or []
    except Exception as e:
        st.error(f"Error loading design records: {e}")
        return

    # If regular designer, show jobs assigned to them, open pool, or flagged returns
    if not is_privileged:
        display_jobs_source = [
            j for j in all_design_jobs
            if not j.get("assigned_designer")
            or j.get("assigned_designer") == "OPEN_POOL"
            or j.get("assigned_designer") == user["full_name"]
        ]
    else:
        display_jobs_source = all_design_jobs

    # Callback to reset filters
    def _reset_design_filters():
        _clear_active_modals()
        st.session_state["des_search_kw"] = ""
        st.session_state["des_designer_filter"] = "Mine"
        st.session_state["des_sort_filter"] = "Recent Jobs (Newest First)"
        st.session_state["des_page_num"] = 1

    # --- Top Filter Bar ---
    with st.container(border=True):
        f1, f2, f3, f4 = st.columns([3.5, 2.5, 2.5, 1.5])
        with f1:
            search_kw = st.text_input(
                "Search Orders",
                placeholder="Job No, Client, Contact...",
                key="des_search_kw",
                on_change=_clear_active_modals,
            ).strip().lower()

        with f2:
            designer_opts = ["Mine", "Open Pool", "Return"]
            sel_designer = st.selectbox(
                "Assigned",
                options=designer_opts,
                index=0,
                key="des_designer_filter",
                on_change=_clear_active_modals,
            )

        with f3:
            sort_order = st.selectbox(
                "Sort By",
                options=["Recent Jobs (Newest First)", "Oldest Jobs", "Delivery Due Soonest"],
                key="des_sort_filter",
                on_change=_clear_active_modals,
            )

        with f4:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "Reset Filters",
                type="secondary",
                use_container_width=True,
                key="des_reset_btn",
                on_click=_reset_design_filters,
            )

    # --- Filter Logic ---
    filtered_jobs = []
    for j in display_jobs_source:
        designer_assigned = str(j.get("assigned_designer") or "").strip()
        is_returned = bool(j.get("is_returned", False))

        if sel_designer == "Mine":
            if is_returned or designer_assigned.lower() != user["full_name"].strip().lower():
                continue
        elif sel_designer == "Open Pool":
            if is_returned or (designer_assigned and designer_assigned != "OPEN_POOL"):
                continue
        elif sel_designer == "Return":
            if not is_returned:
                continue

        if search_kw:
            comb = f"{j.get('job_no', '')} {j.get('client_name', '')} {j.get('contact_person', '')} {j.get('contact_phone', '')}".lower()
            if search_kw not in comb:
                continue

        filtered_jobs.append(j)

    # --- Sorting Logic ---
    if sort_order == "Recent Jobs (Newest First)":
        filtered_jobs.sort(key=lambda x: x.get("job_id", 0), reverse=True)
    elif sort_order == "Oldest Jobs":
        filtered_jobs.sort(key=lambda x: x.get("job_id", 0))
    elif sort_order == "Delivery Due Soonest":
        filtered_jobs.sort(key=lambda x: str(x.get("due_date", "9999-99-99")))

    # --- 15-Row Pagination ---
    ROWS_PER_PAGE = 15
    total_records = len(filtered_jobs)
    total_pages = max(1, (total_records + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

    if "des_page_num" not in st.session_state:
        st.session_state.des_page_num = 1

    if st.session_state.des_page_num > total_pages:
        st.session_state.des_page_num = total_pages

    curr_page = st.session_state.des_page_num
    start_idx = (curr_page - 1) * ROWS_PER_PAGE
    end_idx = min(start_idx + ROWS_PER_PAGE, total_records)
    page_records = filtered_jobs[start_idx:end_idx]

    # Selected rows on active page
    selected_job_ids = [
        j["job_id"] for j in page_records
        if st.session_state.get(f"des_chk_{j['job_id']}", False)
    ]

    # --- Top Bar: Counter & Bulk Action Triggers ---
    tbar1, tbar2 = st.columns([5, 5])
    with tbar1:
        st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** design orders")

    with tbar2:
        if selected_job_ids:
            b_col_app, b_col_ret = st.columns(2)

            with b_col_app:
                with st.popover(f"Bulk Approve ({len(selected_job_ids)})", use_container_width=True):
                    st.markdown(f"**Approve {len(selected_job_ids)} Order(s)?**")
                    st.caption("Pushes all selected orders forward to Accounts Clearance (PAYMENT).")
                    if st.button("Confirm Bulk Approval", type="primary", use_container_width=True, key="btn_confirm_bulk_app"):
                        _clear_active_modals()
                        ok, msg = bulk_approve_design_jobs(selected_job_ids, user["full_name"])
                        if ok:
                            for jid in selected_job_ids:
                                if f"des_chk_{jid}" in st.session_state:
                                    del st.session_state[f"des_chk_{jid}"]
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

            with b_col_ret:
                with st.popover(f"Bulk Send to Sales ({len(selected_job_ids)})", use_container_width=True):
                    st.markdown(f"**Send {len(selected_job_ids)} Order(s) back to Sales?**")
                    bulk_reason = st.text_input("Discrepancy Reason *", placeholder="e.g. Dimensions missing, low resolution file", key="bulk_spec_reason")
                    if st.button("Confirm Bulk Return", type="primary", use_container_width=True, key="btn_confirm_bulk_ret"):
                        if not bulk_reason.strip():
                            st.error("Please provide a reason before returning.")
                        else:
                            _clear_active_modals()
                            ok, msg = bulk_reject_design_jobs(selected_job_ids, user["full_name"], bulk_reason.strip())
                            if ok:
                                for jid in selected_job_ids:
                                    if f"des_chk_{jid}" in st.session_state:
                                        del st.session_state[f"des_chk_{jid}"]
                                st.warning(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    if not page_records:
        st.info("No matching design approval orders found.")
        return

    # --- Table Header Bar (ALI Theme 7-Column Ratio) ---
    st.markdown("""
        <div class="adnet-table-header" style="padding: 10px 14px;">
            <div style="display: grid; grid-template-columns: 0.3fr 1.1fr 1.1fr 2.3fr 2.1fr 1.3fr 1.8fr; align-items: center; gap: 8px;">
                <div class="tbl-cell-header">&nbsp;</div>
                <div class="tbl-cell-header">Job No.</div>
                <div class="tbl-cell-header">Date</div>
                <div class="tbl-cell-header">Client</div>
                <div class="tbl-cell-header">Contact</div>
                <div class="tbl-cell-header">Delivery Date</div>
                <div class="tbl-cell-header" style="text-align: center;">Action</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    def _open_view_modal(target_jid):
        st.session_state["des_view_jid"] = target_jid

    # --- Table Data Rows ---
    for j in page_records:
        jid = j["job_id"]
        job_no = j.get("job_no", str(jid))
        created_date = str(j.get("created_at", ""))[:10] or "N/A"
        client_name = j.get("client_name") or "N/A"
        contact_p = j.get("contact_person") or "N/A"
        contact_ph = j.get("contact_phone") or "N/A"
        due_date_str = str(j.get("due_date") or "N/A")
        contact_label = f"{contact_p} ({contact_ph})" if contact_ph != "N/A" else contact_p

        r_chk, r_no, r_date, r_client, r_contact, r_due, r_act = st.columns(
            [0.3, 1.1, 1.1, 2.3, 2.1, 1.3, 1.8],
            vertical_alignment="center",
        )

        with r_chk:
            st.checkbox(
                " ",
                key=f"des_chk_{jid}",
                label_visibility="collapsed",
                on_change=_clear_active_modals,
            )

        with r_no:
            st.button(
                f"JOB-{job_no}",
                key=f"btn_m_no_{jid}",
                type="tertiary",
                help="Click to view job details",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_date:
            st.button(
                created_date,
                key=f"btn_m_dt_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_client:
            st.button(
                client_name,
                key=f"btn_m_cl_{jid}",
                type="tertiary",
                help=client_name,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_contact:
            st.button(
                contact_label,
                key=f"btn_m_cp_{jid}",
                type="tertiary",
                help=contact_label,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_due:
            st.button(
                due_date_str,
                key=f"btn_m_due_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_act:
            action_choice = st.selectbox(
                "Action",
                options=["Select Action", "Approved", "Send to Sales"],
                index=0,
                key=f"des_act_drp_{jid}",
                label_visibility="collapsed",
                on_change=_clear_active_modals,
            )

            # Option 1: Approved -> Routes to Accounts (PAYMENT)
            if action_choice == "Approved":
                with st.popover(f"Confirm Approval #{job_no}", use_container_width=True):
                    st.markdown(f"**Approve Job #{job_no}?**")
                    st.caption("Marks design cleared and pushes order to Payment Clearance.")
                    if st.button("Confirm Approval", key=f"btn_single_app_{jid}", type="primary", use_container_width=True):
                        ok, msg = bulk_approve_design_jobs([jid], user["full_name"])
                        if ok:
                            st.success(f"Job #{job_no} approved and sent to Accounts.")
                            st.rerun()
                        else:
                            st.error(msg)

            # Option 2: Send to Sales -> Routes to SALES with return reason
            elif action_choice == "Send to Sales":
                with st.popover(f"Return #{job_no} to Sales", use_container_width=True):
                    st.markdown(f"**Return Job #{job_no} to Sales Intake**")
                    spec_note = st.text_input("Discrepancy Details *", placeholder="e.g. Dimensions incorrect, unreadable artwork", key=f"s_flag_note_{jid}")
                    if st.button("Submit to Sales", key=f"btn_single_rej_{jid}", type="primary", use_container_width=True):
                        if not spec_note.strip():
                            st.error("Please explain the issue before returning.")
                        else:
                            ok, msg = reject_job_to_sales(jid, user["full_name"], spec_note.strip())
                            if ok:
                                st.warning(f"Job #{job_no} returned to Sales.")
                                st.rerun()
                            else:
                                st.error(msg)

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

    # Open Details Modal when any row text is clicked
    view_jid = st.session_state.get("des_view_jid")
    if view_jid:
        target_job = next((x for x in all_design_jobs if x["job_id"] == view_jid), None)
        if target_job:
            show_jobsheet_spec_modal(target_job)

    # --- 15-Row Pagination Footer ---
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        p_cols = st.columns([2, 1, 1, 1, 1, 1, 2])
        with p_cols[1]:
            if st.button("<", disabled=(curr_page == 1), key="des_p_prev_btn", use_container_width=True):
                _clear_active_modals()
                st.session_state.des_page_num = max(1, curr_page - 1)
                st.rerun()

        for p_idx in range(1, min(total_pages + 1, 5)):
            with p_cols[1 + p_idx]:
                is_active = (p_idx == curr_page)
                btn_type = "primary" if is_active else "secondary"
                if st.button(str(p_idx), type=btn_type, key=f"des_p_btn_{p_idx}", use_container_width=True):
                    _clear_active_modals()
                    st.session_state.des_page_num = p_idx
                    st.rerun()

        with p_cols[6]:
            if st.button(">", disabled=(curr_page == total_pages), key="des_p_next_btn", use_container_width=True):
                _clear_active_modals()
                st.session_state.des_page_num = min(total_pages, curr_page + 1)
                st.rerun()