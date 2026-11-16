from datetime import datetime, date
import streamlit as st
from database import (
    supabase, 
    get_job_items, 
    get_all_vendors, 
    get_custom_presets, 
    add_custom_preset,
    log_audit
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
    st.session_state["view_prod_job_id"] = None


def _reset_production_filters():
    _clear_active_modals()
    st.session_state["prod_search_kw"] = ""
    st.session_state["prod_sort_filter"] = "Recent Jobs (Newest First)"
    st.session_state["prod_page_num"] = 1


@st.dialog("Job Sheet & Production Details")
def show_job_details_modal(job, items, vendors, user):
    """Full detail view opened when clicking on any job number (ALI Theme compact dialog)."""
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    jid = job["job_id"]
    job_no = job.get("job_no", str(jid))
    total_val = sum(float(it.get("amount", 0) or 0) for it in items)

    st.markdown(f"### Production Sheet: #{job_no}")
    st.caption(
        f"**Client:** {job.get('client_name')} | "
        f"**Contact:** {job.get('contact_person') or 'N/A'} ({job.get('contact_phone') or 'N/A'}) | "
        f"**Total Value:** ₹{total_val:,.2f}"
    )

    if job.get("is_returned"):
        st.error(f"Return Notice from {job.get('returned_by')}: {job.get('return_reason')}")

    p_tab1, p_tab2, p_tab3 = st.tabs(["📦 Items & Specs", "🏭 Vendor Job-Work", "📄 Paper Fabrications"])

    with p_tab1:
        st.markdown("##### Ordered Items")
        for idx, it in enumerate(items, 1):
            st.markdown(
                f"**{idx}. {it.get('item_name')}** — `{it.get('quantity')} {it.get('unit', 'Pcs')}` "
                f"@ ₹{float(it.get('rate', 0)):,.2f}"
            )
            if it.get("specifications"):
                st.caption(f"**Specs / Size:** {it.get('specifications')}")
            if it.get("delivery_address"):
                st.caption(f"**Delivery:** {it.get('delivery_address')}")

    with p_tab2:
        st.markdown("##### Outsource Job-Work Details")
        v_names = [v.get("vendor_name", "Vendor") for v in vendors if v.get("is_active", True)] or ["General Vendor"]
        sel_vendor = st.selectbox("Assign Outsource Vendor", options=v_names, key=f"dlg_v_{jid}")

        saved_v_jobs = get_custom_presets("VENDOR_JOB")
        base_item_opts = [it.get("item_name", "").strip() for it in items if it.get("item_name")]
        combined_jobs = sorted(list(set(base_item_opts + saved_v_jobs))) + ["NEW"]
        sel_v_job = st.selectbox("Job Work Item", options=combined_jobs, key=f"dlg_v_job_{jid}")

        if sel_v_job == "NEW":
            new_v = st.text_input("Enter New Outsource Job Name *", key=f"dlg_v_new_{jid}").strip()
            if new_v and st.button("Save New Job Preset", key=f"btn_save_v_{jid}"):
                add_custom_preset("VENDOR_JOB", new_v)
                st.rerun()

        v_sz1, v_sz2, v_sz3, v_sz4 = st.columns(4)
        with v_sz1:
            st.number_input("W", value=1.0, step=0.1, key=f"dlg_vw_{jid}")
        with v_sz2:
            st.number_input("B", value=1.0, step=0.1, key=f"dlg_vb_{jid}")
        with v_sz3:
            st.number_input("H", value=1.0, step=0.1, key=f"dlg_vh_{jid}")
        with v_sz4:
            st.selectbox("Unit", ["Inch", "Ft", "mm"], key=f"dlg_vu_{jid}")

        st.number_input("Quantity", min_value=1, value=1, step=1, key=f"dlg_vq_{jid}")

    with p_tab3:
        st.markdown("##### Post-Print Paper Fabrications")
        default_fabs = [
            "Cardboard Mounting",
            "Foam Board Pasting",
            "Matte Lamination",
            "Gloss Lamination",
            "Die-Punching & Creasing",
            "Binding & Eyeletting"
        ]
        saved_fabs = get_custom_presets("FABRICATION")
        all_fabs = sorted(list(set(default_fabs + saved_fabs))) + ["NEW"]
        fab_sel = st.selectbox("Fabrication Task", options=all_fabs, key=f"dlg_fab_{jid}")

        if fab_sel == "NEW":
            new_f = st.text_input("Enter New Fabrication Description *", key=f"dlg_f_new_{jid}").strip()
            if new_f and st.button("Save Fabrication Preset", key=f"btn_save_f_{jid}"):
                add_custom_preset("FABRICATION", new_f)
                st.rerun()

        f_sz1, f_sz2, f_sz3, f_sz4 = st.columns(4)
        with f_sz1:
            st.number_input("W", value=1.0, step=0.1, key=f"dlg_fw_{jid}")
        with f_sz2:
            st.number_input("B", value=1.0, step=0.1, key=f"dlg_fb_{jid}")
        with f_sz3:
            st.number_input("H", value=1.0, step=0.1, key=f"dlg_fh_{jid}")
        with f_sz4:
            st.selectbox("Unit", ["Inch", "Ft", "mm"], key=f"dlg_fu_{jid}")

        st.number_input("Quantity", min_value=1, value=1, step=1, key=f"dlg_fq_{jid}")

    st.markdown("---")
    if st.button("Close View", use_container_width=True, key=f"cls_prod_modal_{jid}"):
        st.session_state["view_prod_job_id"] = None
        st.rerun()


def render(user):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)

    if st.session_state.get("prod_toast_msg"):
        st.toast(st.session_state.pop("prod_toast_msg"))
    if st.session_state.get("prod_err_msg"):
        st.error(st.session_state.pop("prod_err_msg"))

    st.subheader("Module 4: Production Floor & Fabrication Desk")
    st.caption(
        f"Floor Supervisor / Operator: **{user['full_name']}** | "
        f"Station: `{user.get('primary_station') or 'Floor General'}` | Role: `{user.get('account_type')}`"
    )

    # 1. Fetch all jobs currently in PRODUCTION stage
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "PRODUCTION")
            .order("job_id", desc=True)
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching production jobs: {e}")
        return

    vendors = get_all_vendors()

    # --- TOP FILTER & SEARCH BAR ---
    with st.container(border=True):
        f1, f2, f3 = st.columns([4, 3, 1.5])
        with f1:
            search_kw = st.text_input(
                "Search Orders",
                placeholder="Search Job No, Client, Contact Phone...",
                key="prod_search_kw",
                on_change=_clear_active_modals,
            ).strip().lower()
        with f2:
            sort_order = st.selectbox(
                "Sort By",
                options=["Recent Jobs (Newest First)", "Oldest Jobs", "Delivery Due Soonest"],
                key="prod_sort_filter",
                on_change=_clear_active_modals,
            )
        with f3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "Reset Filters",
                type="secondary",
                use_container_width=True,
                key="prod_reset_btn",
                on_click=_reset_production_filters
            )

    # --- FILTERING LOGIC ---
    filtered_jobs = []
    for j in jobs:
        if search_kw:
            comb_text = f"{j.get('job_no', '')} {j.get('client_name', '')} {j.get('contact_person', '')} {j.get('contact_phone', '')}".lower()
            if search_kw not in comb_text:
                continue
        filtered_jobs.append(j)

    # --- SORTING LOGIC ---
    if sort_order == "Recent Jobs (Newest First)":
        filtered_jobs.sort(key=lambda x: x.get("job_id", 0), reverse=True)
    elif sort_order == "Oldest Jobs":
        filtered_jobs.sort(key=lambda x: x.get("job_id", 0))
    elif sort_order == "Delivery Due Soonest":
        filtered_jobs.sort(key=lambda x: str(x.get("due_date", "9999-99-99")))

    # --- PAGINATION LOGIC (15 ROWS PER PAGE) ---
    ROWS_PER_PAGE = 15
    total_records = len(filtered_jobs)
    total_pages = max(1, (total_records + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

    if "prod_page_num" not in st.session_state:
        st.session_state.prod_page_num = 1

    if st.session_state.prod_page_num > total_pages:
        st.session_state.prod_page_num = total_pages

    curr_page = st.session_state.prod_page_num
    start_idx = (curr_page - 1) * ROWS_PER_PAGE
    end_idx = min(start_idx + ROWS_PER_PAGE, total_records)
    page_records = filtered_jobs[start_idx:end_idx]

    # --- IDENTIFY SELECTED CHECKBOXES FOR BULK ACTIONS ---
    selected_job_ids = [
        j["job_id"] for j in page_records 
        if st.session_state.get(f"prod_chk_{j['job_id']}", False)
    ]

    # --- BULK ACTION BAR & COUNTER ---
    bar_col1, bar_col2 = st.columns([5, 5])
    with bar_col1:
        st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** pending production jobs")

    with bar_col2:
        if selected_job_ids:
            b_act1, b_act2 = st.columns(2)
            with b_act1:
                with st.popover(f"Bulk Complete ({len(selected_job_ids)})", use_container_width=True):
                    st.success(f"Forward all {len(selected_job_ids)} selected job(s) directly to the QC Desk?")
                    if st.button("Confirm Bulk QC Forward", key="btn_bulk_qc_confirm", type="primary", use_container_width=True):
                        _clear_active_modals()
                        try:
                            for bid in selected_job_ids:
                                supabase.table("jobs").update({
                                    "current_stage": "QC",
                                    "is_returned": False
                                }).eq("job_id", int(bid)).execute()
                                if f"prod_chk_{bid}" in st.session_state:
                                    del st.session_state[f"prod_chk_{bid}"]
                            log_audit(user["user_id"], "BULK_PRODUCTION_COMPLETED", f"Completed jobs: {selected_job_ids}")
                            st.session_state["prod_toast_msg"] = f"{len(selected_job_ids)} job(s) moved to QC Desk."
                            st.rerun()
                        except Exception as e:
                            st.error(f"Bulk complete failed: {e}")

            with b_act2:
                with st.popover(f"Bulk Flag / Return ({len(selected_job_ids)})", use_container_width=True):
                    st.markdown("#### Return Selected Jobs")
                    bulk_ret_target = st.selectbox(
                        "Return To Station",
                        ["PAYMENT", "DESIGN", "SALES"],
                        format_func=lambda x: {
                            "PAYMENT": "Accounts / Advance Clearance",
                            "DESIGN": "Design & Proofs",
                            "SALES": "Order Intake / Sales"
                        }.get(x, x),
                        key="bulk_ret_target"
                    )
                    bulk_ret_reason = st.text_area("Return Explanation *", key="bulk_ret_reason")
                    if st.button("Confirm Bulk Return", key="btn_bulk_ret_confirm", type="primary", use_container_width=True):
                        if not bulk_ret_reason.strip():
                            st.error("Please enter a return explanation.")
                        else:
                            _clear_active_modals()
                            try:
                                for bid in selected_job_ids:
                                    supabase.table("jobs").update({
                                        "current_stage": bulk_ret_target,
                                        "is_returned": True,
                                        "returned_by": f"{user['full_name']} (Production)",
                                        "return_reason": bulk_ret_reason.strip()
                                    }).eq("job_id", int(bid)).execute()
                                    if f"prod_chk_{bid}" in st.session_state:
                                        del st.session_state[f"prod_chk_{bid}"]
                                log_audit(user["user_id"], "BULK_PRODUCTION_RETURN", f"Returned jobs {selected_job_ids} to {bulk_ret_target}: {bulk_ret_reason.strip()}")
                                st.session_state["prod_toast_msg"] = f"{len(selected_job_ids)} job(s) returned to {bulk_ret_target}."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Bulk return failed: {e}")

    if not page_records:
        st.info("No active jobs pending on the production floor.")
        return

    # --- TABLE HEADER ---
    st.markdown("""
        <div class="adnet-table-header" style="padding: 10px 14px;">
            <div style="display: grid; grid-template-columns: 0.3fr 1.1fr 1fr 1.8fr 1.6fr 1.1fr 1.2fr 1.8fr; align-items: center; gap: 8px;">
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

    def _open_view_modal(target_jid):
        st.session_state["view_prod_job_id"] = target_jid

    # --- TABLE ROWS ---
    for job in page_records:
        jid = job["job_id"]
        job_no = job.get("job_no", str(jid))
        created_date = str(job.get("created_at", ""))[:10] or "N/A"
        client_name = job.get("client_name") or "N/A"
        contact_p = job.get("contact_person") or "N/A"
        contact_ph = job.get("contact_phone") or "N/A"
        due_date_str = str(job.get("due_date") or "N/A")

        items = get_job_items(jid) or []
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        r_chk, r_no, r_date, r_client, r_contact, r_due, r_val, r_act = st.columns(
            [0.3, 1.1, 1, 1.8, 1.6, 1.1, 1.2, 1.8],
            vertical_alignment="center",
        )

        with r_chk:
            st.checkbox(
                " ",
                key=f"prod_chk_{jid}",
                label_visibility="collapsed",
                on_change=_clear_active_modals,
            )

        with r_no:
            st.button(
                f"JOB-{job_no}",
                key=f"btn_link_{jid}",
                type="tertiary",
                help="Click to view full job details",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_date:
            st.button(
                created_date,
                key=f"prod_m_dt_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_client:
            st.button(
                client_name,
                key=f"prod_m_cl_{jid}",
                type="tertiary",
                help=client_name,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_contact:
            st.button(
                f"{contact_p} ({contact_ph})",
                key=f"prod_m_cp_{jid}",
                type="tertiary",
                help=f"{contact_p} ({contact_ph})",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_due:
            st.button(
                due_date_str,
                key=f"prod_m_due_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_val:
            st.button(
                f"₹ {total_val:,.2f}",
                key=f"prod_m_val_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_act:
            def _on_prod_action_change(target_job=job):
                t_jid = target_job["job_id"]
                t_jno = target_job.get("job_no", str(t_jid))
                choice = st.session_state.get(f"act_prod_{t_jid}")
                if choice == "Production Completed":
                    st.session_state["view_prod_job_id"] = None
                    try:
                        supabase.table("jobs").update({
                            "current_stage": "QC",
                            "is_returned": False
                        }).eq("job_id", int(t_jid)).execute()
                        log_audit(user["user_id"], "PRODUCTION_COMPLETED", f"Job #{t_jno} sent to QC Desk")
                        st.session_state["prod_toast_msg"] = f"Job #{t_jno} forwarded to QC Desk."
                    except Exception as e:
                        st.session_state["prod_err_msg"] = f"Failed to update status: {e}"
                st.session_state[f"act_prod_{t_jid}"] = "Select Action"

            action_choice = st.selectbox(
                "Action",
                options=["Select Action", "Production Completed", "Return / Flag Job"],
                index=0,
                key=f"act_prod_{jid}",
                label_visibility="collapsed",
                on_change=_on_prod_action_change,
                args=(job,),
            )

            if action_choice == "Return / Flag Job":
                with st.popover(f"Return Job #{job_no}", use_container_width=True):
                    st.markdown("#### Return Station")
                    return_target = st.selectbox(
                        "Return To Station",
                        ["PAYMENT", "DESIGN", "SALES"],
                        format_func=lambda x: {
                            "PAYMENT": "Accounts / Advance Clearance",
                            "DESIGN": "Design & Proofs",
                            "SALES": "Order Intake / Sales"
                        }.get(x, x),
                        key=f"ret_tgt_{jid}"
                    )
                    reason = st.text_area(
                        "Return Reason *", 
                        placeholder="e.g. Discrepancy in specs, missing material, advance pending...", 
                        key=f"ret_rsn_{jid}"
                    )
                    if st.button("Submit Return", key=f"btn_ret_submit_{jid}", type="primary", use_container_width=True):
                        if not reason.strip():
                            st.error("Please enter a return reason.")
                        else:
                            _clear_active_modals()
                            try:
                                supabase.table("jobs").update({
                                    "current_stage": return_target,
                                    "is_returned": True,
                                    "returned_by": f"{user['full_name']} (Production)",
                                    "return_reason": reason.strip()
                                }).eq("job_id", int(jid)).execute()
                                log_audit(user["user_id"], "PRODUCTION_RETURN", f"Job #{job_no} returned to {return_target}: {reason.strip()}")
                                st.session_state["prod_toast_msg"] = f"Job #{job_no} returned to {return_target}."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to return job: {e}")

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

    # --- MODAL TRIGGER WHEN JOB LINK IS CLICKED ---
    active_jid = st.session_state.get("view_prod_job_id")
    if active_jid:
        job_match = next((j for j in jobs if j["job_id"] == active_jid), None)
        if job_match:
            job_match_items = get_job_items(active_jid) or []
            show_job_details_modal(job_match, job_match_items, vendors, user)

    # --- PAGINATION CONTROLS AT BOTTOM ---
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns([2, 1, 2, 1, 2])

        with p_c2:
            if st.button("◀ Previous", disabled=(curr_page <= 1), use_container_width=True, key="prod_pg_prev"):
                _clear_active_modals()
                st.session_state.prod_page_num = max(1, curr_page - 1)
                st.rerun()

        with p_c3:
            st.markdown(
                f"<div style='text-align: center; padding-top: 6px; font-size: 13px; font-weight: 600; color: #1e293b;'>"
                f"Page {curr_page} of {total_pages}"
                f"</div>",
                unsafe_allow_html=True
            )

        with p_c4:
            if st.button("Next ▶", disabled=(curr_page >= total_pages), use_container_width=True, key="prod_pg_next"):
                _clear_active_modals()
                st.session_state.prod_page_num = min(total_pages, curr_page + 1)
                st.rerun()