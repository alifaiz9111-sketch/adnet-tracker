from datetime import datetime, date
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
    st.session_state["view_dsp_job_id"] = None


def _reset_dispatch_filters():
    _clear_active_modals()
    st.session_state["dsp_search_kw"] = ""
    st.session_state["dsp_sort_filter"] = "Recent Jobs (Newest First)"
    st.session_state["dsp_page_num"] = 1


@st.dialog("Dispatch & Delivery Details")
def show_dispatch_details_modal(job, items, user):
    """Full detail view opened when clicking on any row cell."""
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    jid = job["job_id"]
    job_no = job.get("job_no", str(jid))
    total_val = sum(float(it.get("amount", 0) or 0) for it in items)

    st.markdown(f"### Dispatch & Delivery Sheet: #{job_no}")
    st.caption(
        f"**Client:** {job.get('client_name')} | "
        f"**Contact:** {job.get('contact_person') or 'N/A'} ({job.get('contact_phone') or 'N/A'}) | "
        f"**Total Value:** ₹{total_val:,.2f}"
    )

    if job.get("is_returned"):
        st.error(f"Return / Defect Notice: {job.get('return_reason')} (Reported by: {job.get('returned_by', 'Floor')})")

    st.markdown("##### Items & Destination Addresses")
    if not items:
        st.info("No line items logged for this order.")
    else:
        for it in items:
            del_badge = "Delivered" if it.get("is_delivered") else "In Transit"
            with st.container(border=True):
                st.markdown(f"**{it.get('item_name')}** ({it.get('quantity')} {it.get('unit', 'Pcs')}) — Status: `{del_badge}`")
                if it.get("delivery_address"):
                    st.caption(f"**Destination Address:** {it.get('delivery_address')}")

    st.markdown("---")
    st.markdown("##### Delivery Completion Handover & Challan")

    auto_challan_no = f"DC-2026-{job_no}"
    st.markdown(f"**Challan No:** `{auto_challan_no}`")

    runner_name = st.text_input(
        "Driver / Delivery Person",
        placeholder="e.g. Subhash Logistics",
        key=f"dlg_run_{jid}",
    )

    file_challan = st.file_uploader(
        "Upload Challan Copy",
        type=["png", "jpg", "jpeg", "pdf"],
        key=f"dlg_upl_challan_{jid}"
    )

    file_job_done = st.file_uploader(
        "Upload Job Done Image (Site/Delivery Proof)",
        type=["png", "jpg", "jpeg"],
        key=f"dlg_upl_jobdone_{jid}"
    )

    if st.button("Complete Dispatch & Push to Billing", key=f"dlg_btn_dsp_{jid}", type="primary", use_container_width=True):
        with st.spinner("Uploading proof attachments and recording dispatch..."):
            challan_url = None
            job_done_url = None

            def _upload_file(file_obj, prefix):
                if not file_obj:
                    return None
                try:
                    f_ext = file_obj.name.split(".")[-1]
                    path = f"{prefix}_{jid}_{job_no}.{f_ext}"
                    try:
                        supabase.storage.from_("dispatch-media").upload(
                            path=path,
                            file=file_obj.getvalue(),
                            file_options={"content-type": file_obj.type, "upsert": "true"}
                        )
                        return supabase.storage.from_("dispatch-media").get_public_url(path)
                    except Exception:
                        supabase.storage.from_("delivery_proofs").upload(
                            path=path,
                            file=file_obj.getvalue(),
                            file_options={"content-type": file_obj.type, "upsert": "true"}
                        )
                        return supabase.storage.from_("delivery_proofs").get_public_url(path)
                except Exception as err:
                    st.warning(f"File upload note: {err}")
                    return None

            if file_challan:
                challan_url = _upload_file(file_challan, "challan")
            if file_job_done:
                job_done_url = _upload_file(file_job_done, "jobdone")

            try:
                supabase.table("job_items").update({
                    "is_delivered": True
                }).eq("job_id", int(jid)).execute()

                update_payload = {
                    "current_stage": "BILLING_REVIEW",
                    "is_returned": False,
                    "challan_no": auto_challan_no,
                }

                d_name = runner_name.strip() if runner_name else None
                if d_name:
                    update_payload["dispatch_notes"] = f"Driver: {d_name}"
                    update_payload["driver_name"] = d_name

                if challan_url:
                    update_payload["challan_doc_url"] = challan_url
                    update_payload["challan_image_url"] = challan_url

                if job_done_url:
                    update_payload["proof_file_url"] = job_done_url
                    update_payload["job_done_image_url"] = job_done_url

                try:
                    supabase.table("jobs").update(update_payload).eq("job_id", int(jid)).execute()
                except Exception:
                    fallback_payload = {
                        "current_stage": "BILLING_REVIEW",
                        "is_returned": False,
                        "challan_no": auto_challan_no
                    }
                    supabase.table("jobs").update(fallback_payload).eq("job_id", int(jid)).execute()

                log_audit(user["user_id"], "DISPATCH_COMPLETED", f"Job #{job_no} completed dispatch and sent to Billing Review")
                st.session_state["view_dsp_job_id"] = None
                st.session_state["dsp_toast_msg"] = f"Job #{job_no} marked delivered and passed to Billing Review."
                st.rerun()

            except Exception as e:
                st.error(f"Failed to route job: {e}")

    st.markdown("---")
    if st.button("Close View", use_container_width=True, key=f"dlg_close_dsp_{jid}"):
        st.session_state["view_dsp_job_id"] = None
        st.rerun()


def render(user):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)

    if st.session_state.get("dsp_toast_msg"):
        st.toast(st.session_state.pop("dsp_toast_msg"))
    if st.session_state.get("dsp_err_msg"):
        st.error(st.session_state.pop("dsp_err_msg"))

    st.subheader("Module 6: Dispatch, Delivery & Challan Desk")
    st.caption(
        f"Dispatch Officer: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    # Fetch jobs pending delivery/dispatch
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "DISPATCH")
            .order("job_id", desc=True)
            .execute()
        )
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching dispatch queue: {e}")
        return

    # --- TOP FILTER & SEARCH BAR ---
    with st.container(border=True):
        f1, f2, f3 = st.columns([4, 3, 1.5])
        with f1:
            search_kw = st.text_input(
                "Search Orders",
                placeholder="Search Job No, Client, Contact Phone...",
                key="dsp_search_kw",
                on_change=_clear_active_modals,
            ).strip().lower()
        with f2:
            sort_order = st.selectbox(
                "Sort By",
                options=["Recent Jobs (Newest First)", "Oldest Jobs", "Delivery Due Soonest"],
                key="dsp_sort_filter",
                on_change=_clear_active_modals,
            )
        with f3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.button(
                "Reset Filters",
                type="secondary",
                use_container_width=True,
                key="dsp_reset_btn",
                on_click=_reset_dispatch_filters,
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

    if "dsp_page_num" not in st.session_state:
        st.session_state.dsp_page_num = 1

    if st.session_state.dsp_page_num > total_pages:
        st.session_state.dsp_page_num = total_pages

    curr_page = st.session_state.dsp_page_num
    start_idx = (curr_page - 1) * ROWS_PER_PAGE
    end_idx = min(start_idx + ROWS_PER_PAGE, total_records)
    page_records = filtered_jobs[start_idx:end_idx]

    # --- IDENTIFY SELECTED CHECKBOXES FOR BULK ACTIONS ---
    selected_job_ids = [
        j["job_id"] for j in page_records 
        if st.session_state.get(f"dsp_chk_{j['job_id']}", False)
    ]

    # --- BULK ACTION BAR & COUNTER ---
    bar_col1, bar_col2 = st.columns([5, 5])
    with bar_col1:
        st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** pending dispatch orders")

    with bar_col2:
        if selected_job_ids:
            b_act1, b_act2 = st.columns(2)
            with b_act1:
                with st.popover(f"Bulk Complete ({len(selected_job_ids)})", use_container_width=True):
                    st.markdown(f"**Complete dispatch for {len(selected_job_ids)} selected job(s) and push to Billing Review?**")
                    if st.button("Confirm Bulk Billing Handover", key="btn_bulk_dsp_app", type="primary", use_container_width=True):
                        _clear_active_modals()
                        try:
                            for bid in selected_job_ids:
                                supabase.table("job_items").update({
                                    "is_delivered": True
                                }).eq("job_id", int(bid)).execute()

                                supabase.table("jobs").update({
                                    "current_stage": "BILLING_REVIEW",
                                    "is_returned": False,
                                    "challan_no": f"DC-2026-{bid}"
                                }).eq("job_id", int(bid)).execute()

                                if f"dsp_chk_{bid}" in st.session_state:
                                    del st.session_state[f"dsp_chk_{bid}"]

                            log_audit(user["user_id"], "BULK_DISPATCH_COMPLETED", f"Completed dispatch jobs: {selected_job_ids}")
                            st.session_state["dsp_toast_msg"] = f"{len(selected_job_ids)} job(s) marked delivered and passed to Billing Review."
                            st.rerun()
                        except Exception as e:
                            st.error(f"Bulk dispatch completion failed: {e}")

            with b_act2:
                with st.popover(f"Bulk Return to QC ({len(selected_job_ids)})", use_container_width=True):
                    st.markdown(f"**Return {len(selected_job_ids)} selected job(s) back to Quality Check?**")
                    bulk_dsp_reason = st.text_area("Issue / Defect Reason *", key="bulk_dsp_reason_inp")
                    if st.button("Confirm Bulk Return to QC", key="btn_bulk_dsp_rej", type="primary", use_container_width=True):
                        if not bulk_dsp_reason.strip():
                            st.error("Please provide a valid reason.")
                        else:
                            _clear_active_modals()
                            try:
                                for bid in selected_job_ids:
                                    supabase.table("jobs").update({
                                        "current_stage": "QC",
                                        "is_returned": True,
                                        "returned_by": f"{user['full_name']} (Dispatch)",
                                        "return_reason": bulk_dsp_reason.strip()
                                    }).eq("job_id", int(bid)).execute()
                                    if f"dsp_chk_{bid}" in st.session_state:
                                        del st.session_state[f"dsp_chk_{bid}"]
                                log_audit(user["user_id"], "BULK_DISPATCH_RETURN", f"Returned dispatch jobs {selected_job_ids} to QC: {bulk_dsp_reason.strip()}")
                                st.session_state["dsp_toast_msg"] = f"{len(selected_job_ids)} job(s) returned to Quality Check (QC)."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Bulk return to QC failed: {e}")

    if not page_records:
        st.info("No orders pending dispatch or delivery.")
        return

    # --- TABLE HEADER ---
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

    def _open_view_modal(target_jid):
        st.session_state["view_dsp_job_id"] = target_jid

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
        contact_label = f"{contact_p} ({contact_ph})" if contact_ph != "N/A" else contact_p
        val_label = f"₹ {total_val:,.2f}"

        r_chk, r_no, r_date, r_client, r_contact, r_due, r_val, r_act = st.columns(
            [0.4, 1.2, 1, 1.8, 1.6, 1.1, 1.2, 1.7],
            vertical_alignment="center",
        )

        with r_chk:
            st.checkbox(
                " ",
                key=f"dsp_chk_{jid}",
                label_visibility="collapsed",
                on_change=_clear_active_modals,
            )

        with r_no:
            st.button(
                f"JOB-{job_no}",
                key=f"dsp_btn_link_{jid}",
                type="tertiary",
                help="Click to view full dispatch & challan details",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_date:
            st.button(
                created_date,
                key=f"dsp_dt_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_client:
            st.button(
                client_name,
                key=f"dsp_cl_{jid}",
                type="tertiary",
                help=client_name,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_contact:
            st.button(
                contact_label,
                key=f"dsp_cp_{jid}",
                type="tertiary",
                help=contact_label,
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_due:
            st.button(
                due_date_str,
                key=f"dsp_due_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_val:
            st.button(
                val_label,
                key=f"dsp_val_{jid}",
                type="tertiary",
                on_click=_open_view_modal,
                args=(jid,),
            )

        with r_act:
            def _on_dsp_action_change(target_job=job):
                t_jid = target_job["job_id"]
                t_jno = target_job.get("job_no", str(t_jid))
                choice = st.session_state.get(f"act_dsp_{t_jid}")
                if choice == "Complete Dispatch & Send to Billing":
                    st.session_state["view_dsp_job_id"] = t_jid  # Opens details modal to upload proof/challan
                elif choice == "Return to QC":
                    st.session_state["view_dsp_job_id"] = t_jid  # Opens details modal to specify defect reason
                st.session_state[f"act_dsp_{t_jid}"] = "Select Action"

            st.selectbox(
                "Action",
                options=["Select Action", "Complete Dispatch & Send to Billing", "Return to QC"],
                index=0,
                key=f"act_dsp_{jid}",
                label_visibility="collapsed",
                on_change=_on_dsp_action_change,
                args=(job,),
            )

        st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

    # --- MODAL TRIGGER WHEN ANY ROW CELL IS CLICKED ---
    active_jid = st.session_state.get("view_dsp_job_id")
    if active_jid:
        job_match = next((j for j in jobs if j["job_id"] == active_jid), None)
        if job_match:
            job_match_items = get_job_items(active_jid) or []
            show_dispatch_details_modal(job_match, job_match_items, user)

    # --- PAGINATION CONTROLS AT BOTTOM ---
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns([2, 1, 2, 1, 2])

        with p_c2:
            if st.button("◀ Previous", disabled=(curr_page <= 1), use_container_width=True, key="dsp_pg_prev"):
                _clear_active_modals()
                st.session_state.dsp_page_num = max(1, curr_page - 1)
                st.rerun()

        with p_c3:
            st.markdown(
                f"<div style='text-align: center; padding-top: 6px; font-size: 14px; font-weight: 600; color: #475569;'>"
                f"Page {curr_page} of {total_pages}"
                f"</div>",
                unsafe_allow_html=True
            )

        with p_c4:
            if st.button("Next ▶", disabled=(curr_page >= total_pages), use_container_width=True, key="dsp_pg_next"):
                _clear_active_modals()
                st.session_state.dsp_page_num = min(total_pages, curr_page + 1)
                st.rerun()