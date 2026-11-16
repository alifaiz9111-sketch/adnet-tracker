import streamlit as st
import pandas as pd
from datetime import date
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
    st.session_state["view_ca_job_id"] = None


def _reset_ca_filters():
    _clear_active_modals()
    st.session_state["ca_search_gstin"] = ""
    st.session_state["ca_search_client"] = ""
    st.session_state["ca_pos_filter"] = "All"
    st.session_state["ca_page_num"] = 1


@st.dialog("CA Audit & GST Verification")
def show_ca_details_modal(job, items):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)
    jid = job["job_id"]
    job_no = job.get("job_no", str(jid))
    taxable_amt = sum(float(it.get("amount", 0) or 0) for it in items)

    pos = str(job.get("place_of_supply") or "19 - West Bengal")
    is_interstate = not pos.startswith("19")
    tax_amt = round(taxable_amt * 0.18, 2)
    final_inv_val = taxable_amt + tax_amt

    st.markdown(f"### GST Audit Sheet: #{job_no}")
    st.caption(
        f"**Client:** {job.get('client_name')} | "
        f"**GSTIN:** `{job.get('gstin') or 'NOT SPECIFIED'}` | "
        f"**Place of Supply:** `{pos}`"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Bill To Address")
        b_addr = job.get("billing_address") or "No registered billing address entered"
        st.info(f"**{job.get('client_name')}**\n\n{b_addr}\n\n**GSTIN:** {job.get('gstin') or 'N/A'}")
    with c2:
        st.markdown("##### Ship To Address")
        ship_addresses = [it.get("delivery_address") for it in items if it.get("delivery_address")]
        ship_to_str = ", ".join(set(ship_addresses)) if ship_addresses else (job.get("billing_address") or "Same as Bill-To Address")
        st.success(f"**Consignee / Site:**\n\n{ship_to_str}\n\n**Contact:** {job.get('contact_person') or 'N/A'} ({job.get('contact_phone') or 'N/A'})")

    st.markdown("---")
    st.markdown("##### HSN and Line Items Tax Breakdown")

    table_rows = []
    for it in items:
        amt = float(it.get("amount", 0) or 0)
        item_tax = round(amt * 0.18, 2)
        table_rows.append({
            "Item Description": it.get("item_name"),
            "HSN / SAC": "4911 / 9989",
            "Qty": f"{it.get('quantity')} {it.get('unit', 'Pcs')}",
            "Rate": f"{float(it.get('rate', 0)):,.2f}",
            "Taxable": f"{amt:,.2f}",
            "CGST (9%)": "-" if is_interstate else f"₹ {round(item_tax/2, 2):,.2f}",
            "SGST (9%)": "-" if is_interstate else f"₹ {round(item_tax/2, 2):,.2f}",
            "IGST (18%)": f"₹ {item_tax:,.2f}" if is_interstate else "-",
            "Total": f"{amt + item_tax:,.2f}"
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.markdown(f"**Total Taxable Value:** `₹ {taxable_amt:,.2f}` | **Total Tax (18%):** `₹ {tax_amt:,.2f}` | **Gross Invoice:** `₹ {final_inv_val:,.2f}`")

    st.markdown("---")
    if st.button("Close View", use_container_width=True, key=f"dlg_close_ca_{jid}"):
        st.session_state["view_ca_job_id"] = None
        st.rerun()


def render(user):
    st.markdown(_UNIFORM_MODULE_CSS, unsafe_allow_html=True)

    if st.session_state.get("ca_toast_msg"):
        st.toast(st.session_state.pop("ca_toast_msg"))
    if st.session_state.get("ca_err_msg"):
        st.error(st.session_state.pop("ca_err_msg"))

    st.subheader("Module: CA & GST Tax Audit Desk")
    st.caption(
        f"Auditor / CA View | User: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("billing_type", "GST")
            .order("job_id", desc=True)
            .execute()
        )
        gst_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching GST billing records: {e}")
        return

    tab_pending, tab_completed = st.tabs(["Pending Audit", "Completed"])

    # --- TAB 1: PENDING AUDIT ---
    with tab_pending:
        pending_jobs = [j for j in gst_jobs if not j.get("is_billed")]

        total_gst_orders = len(pending_jobs)
        total_taxable_turnover = sum(
            sum(float(it.get("amount", 0) or 0) for it in get_job_items(j["job_id"]))
            for j in pending_jobs
        )

        with st.container(border=True):
            m1, m2, m3 = st.columns(3)
            m1.metric("Pending GST B2B Invoices", f"{total_gst_orders}")
            m2.metric("Total Taxable Value", f"₹ {total_taxable_turnover:,.2f}")
            m3.metric("Est. Total GST (18% avg)", f"₹ {(total_taxable_turnover * 0.18):,.2f}")

        # Initialize safe pagination defaults
        total_pages = 1
        curr_page = 1

        if not pending_jobs:
            st.info("No pending GST records found for audit.")
        else:
            with st.container(border=True):
                st.markdown("##### Audit Filter & Search")
                fc1, fc2, fc3 = st.columns(3)
                with fc1:
                    q_gstin = st.text_input(
                        "Filter by GSTIN",
                        placeholder="e.g. 19AAAA...",
                        key="ca_search_gstin",
                        on_change=_clear_active_modals,
                    ).strip().upper()
                with fc2:
                    q_client = st.text_input(
                        "Filter by Client / Trade Name",
                        placeholder="e.g. Apollo",
                        key="ca_search_client",
                        on_change=_clear_active_modals,
                    ).strip().lower()
                with fc3:
                    q_pos = st.selectbox(
                        "Place of Supply",
                        options=["All"] + sorted(list({str(j.get("place_of_supply") or "19 - West Bengal") for j in pending_jobs})),
                        key="ca_pos_filter",
                        on_change=_clear_active_modals,
                    )

            filtered = []
            for j in pending_jobs:
                if q_gstin and q_gstin not in str(j.get("gstin") or "").upper():
                    continue
                if q_client and q_client not in str(j.get("client_name") or "").lower():
                    continue
                if q_pos != "All" and str(j.get("place_of_supply")) != q_pos:
                    continue
                filtered.append(j)

            export_rows = []
            for j in filtered:
                items = get_job_items(j["job_id"])
                taxable_amt = sum(float(it.get("amount", 0) or 0) for it in items)
                pos = str(j.get("place_of_supply") or "19 - West Bengal")
                is_interstate = not pos.startswith("19")
                gst_rate = 18.0
                tax_amt = round(taxable_amt * (gst_rate / 100.0), 2)
                total_inv = taxable_amt + tax_amt
                ship_to = items[0].get("delivery_address") if items and items[0].get("delivery_address") else j.get("billing_address")

                export_rows.append({
                    "Job #": j.get("job_no"),
                    "Challan #": j.get("challan_no") or f"CH-{j.get('job_no')}",
                    "Client Name": j.get("client_name"),
                    "GSTIN": j.get("gstin") or "N/A",
                    "Bill-To Address": j.get("billing_address") or "N/A",
                    "Ship-To Address": ship_to or "Same as Bill-To",
                    "Place of Supply": pos,
                    "Taxable Amount": taxable_amt,
                    "CGST (9%)": 0.0 if is_interstate else round(tax_amt / 2, 2),
                    "SGST (9%)": 0.0 if is_interstate else round(tax_amt / 2, 2),
                    "IGST (18%)": tax_amt if is_interstate else 0.0,
                    "Total Invoice Value": total_inv,
                    "P.O. Number": j.get("po_no") or "N/A",
                    "Order Date": str(j.get("created_at"))[:10],
                    "Due Date": j.get("due_date")
                })

            if export_rows:
                df_export = pd.DataFrame(export_rows)
                csv_data = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Export GST Report for GSTR-1 (CSV)",
                    data=csv_data,
                    file_name=f"GSTR1_Audit_Export_{date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("---")

            ROWS_PER_PAGE = 15
            total_records = len(filtered)
            total_pages = max(1, (total_records + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

            if "ca_page_num" not in st.session_state:
                st.session_state.ca_page_num = 1
            if st.session_state.ca_page_num > total_pages:
                st.session_state.ca_page_num = total_pages

            curr_page = st.session_state.ca_page_num
            start_idx = (curr_page - 1) * ROWS_PER_PAGE
            end_idx = min(start_idx + ROWS_PER_PAGE, total_records)
            page_records = filtered[start_idx:end_idx]

            selected_ca_ids = [
                j["job_id"] for j in page_records
                if st.session_state.get(f"ca_chk_{j['job_id']}", False)
            ]

            bar_col1, bar_col2 = st.columns([5, 5])
            with bar_col1:
                st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** pending GST record(s)")
            with bar_col2:
                if selected_ca_ids:
                    with st.popover(f"Bulk Mark Completed ({len(selected_ca_ids)})", use_container_width=True):
                        st.markdown(f"**Mark {len(selected_ca_ids)} selected GST record(s) as completed/audited?**")
                        if st.button("Confirm Bulk Complete", key="btn_bulk_ca_comp", type="primary", use_container_width=True):
                            _clear_active_modals()
                            try:
                                for bid in selected_ca_ids:
                                    supabase.table("jobs").update({"is_billed": True}).eq("job_id", int(bid)).execute()
                                    if f"ca_chk_{bid}" in st.session_state:
                                        del st.session_state[f"ca_chk_{bid}"]
                                log_audit(user["user_id"], "BULK_CA_COMPLETED", f"Completed audit for jobs: {selected_ca_ids}")
                                st.session_state["ca_toast_msg"] = f"{len(selected_ca_ids)} GST record(s) marked as completed."
                                st.rerun()
                            except Exception as e:
                                st.error(f"Bulk complete failed: {e}")

            if not page_records:
                st.info("No matching GST records found.")
            else:
                st.markdown("""
                    <div class="adnet-table-header" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                        <div style="display: grid; grid-template-columns: 0.4fr 1.1fr 1fr 1.8fr 1.8fr 1.4fr 1.3fr 1.4fr; align-items: center; gap: 8px;">
                            <div class="tbl-cell-header">&nbsp;</div>
                            <div class="tbl-cell-header">Job No.</div>
                            <div class="tbl-cell-header">Date</div>
                            <div class="tbl-cell-header">Client</div>
                            <div class="tbl-cell-header">GSTIN</div>
                            <div class="tbl-cell-header">Place of Supply</div>
                            <div class="tbl-cell-header" style="text-align: right;">Taxable Value</div>
                            <div class="tbl-cell-header" style="text-align: center;">Action</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                def _open_ca_modal(target_jid):
                    st.session_state["view_ca_job_id"] = target_jid

                for j in page_records:
                    jid = j["job_id"]
                    job_no = j.get("job_no", str(jid))
                    created_date = str(j.get("created_at", ""))[:10] or "N/A"
                    client_name = j.get("client_name") or "N/A"
                    gstin_val = j.get("gstin") or "NOT SPECIFIED"
                    pos_val = str(j.get("place_of_supply") or "19 - West Bengal")

                    items = get_job_items(jid) or []
                    taxable_amt = sum(float(it.get("amount", 0) or 0) for it in items)
                    val_label = f"₹ {taxable_amt:,.2f}"

                    r_chk, r_no, r_date, r_client, r_gstin, r_pos, r_val, r_act = st.columns(
                        [0.4, 1.1, 1, 1.8, 1.8, 1.4, 1.3, 1.4],
                        vertical_alignment="center",
                    )

                    with r_chk:
                        st.checkbox(
                            " ",
                            key=f"ca_chk_{jid}",
                            label_visibility="collapsed",
                            on_change=_clear_active_modals,
                        )

                    with r_no:
                        st.button(
                            f"JOB-{job_no}",
                            key=f"ca_btn_link_{jid}",
                            type="tertiary",
                            help="Click to view detailed GST audit breakdown",
                            on_click=_open_ca_modal,
                            args=(jid,),
                        )

                    with r_date:
                        st.button(
                            created_date,
                            key=f"ca_dt_{jid}",
                            type="tertiary",
                            on_click=_open_ca_modal,
                            args=(jid,),
                        )

                    with r_client:
                        st.button(
                            client_name,
                            key=f"ca_cl_{jid}",
                            type="tertiary",
                            help=client_name,
                            on_click=_open_ca_modal,
                            args=(jid,),
                        )

                    with r_gstin:
                        st.button(
                            gstin_val,
                            key=f"ca_gst_{jid}",
                            type="tertiary",
                            help=gstin_val,
                            on_click=_open_ca_modal,
                            args=(jid,),
                        )

                    with r_pos:
                        st.button(
                            pos_val,
                            key=f"ca_pos_{jid}",
                            type="tertiary",
                            help=pos_val,
                            on_click=_open_ca_modal,
                            args=(jid,),
                        )

                    with r_val:
                        st.button(
                            val_label,
                            key=f"ca_val_{jid}",
                            type="tertiary",
                            on_click=_open_ca_modal,
                            args=(jid,),
                        )

                    with r_act:
                        with st.popover("Upload Audit Files", use_container_width=True):
                            st.markdown(f"**Upload Audit Documents for JOB-{job_no}**")
                            uploaded_files = st.file_uploader(
                                "Select files (PDF, Excel, PNG)",
                                type=["pdf", "xlsx", "xls", "png"],
                                accept_multiple_files=True,
                                key=f"ca_upl_files_{jid}"
                            )
                            if st.button("Complete & Move to Completed", key=f"btn_ca_complete_{jid}", type="primary", use_container_width=True):
                                _clear_active_modals()
                                try:
                                    supabase.table("jobs").update({"is_billed": True}).eq("job_id", int(jid)).execute()
                                    log_audit(user["user_id"], "CA_AUDIT_COMPLETED", f"Completed audit for JOB-{job_no} with {len(uploaded_files) if uploaded_files else 0} file(s)")
                                    st.session_state["ca_toast_msg"] = f"JOB-{job_no} marked as Completed and moved to archive."
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to complete audit: {e}")

                    st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

        view_ca_jid = st.session_state.get("view_ca_job_id")
        if view_ca_jid:
            job_match = next((j for j in filtered if j["job_id"] == view_ca_jid), None)
            if job_match:
                job_match_items = get_job_items(view_ca_jid) or []
                show_ca_details_modal(job_match, job_match_items)

        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns([2, 1, 2, 1, 2])

            with p_c2:
                if st.button("◀ Previous", disabled=(curr_page <= 1), use_container_width=True, key="ca_pg_prev"):
                    _clear_active_modals()
                    st.session_state.ca_page_num = max(1, curr_page - 1)
                    st.rerun()

            with p_c3:
                st.markdown(
                    f"<div style='text-align: center; padding-top: 6px; font-size: 14px; font-weight: 600; color: #475569;'>"
                    f"Page {curr_page} of {total_pages}"
                    f"</div>",
                    unsafe_allow_html=True
                )

            with p_c4:
                if st.button("Next ▶", disabled=(curr_page >= total_pages), use_container_width=True, key="ca_pg_next"):
                    _clear_active_modals()
                    st.session_state.ca_page_num = min(total_pages, curr_page + 1)
                    st.rerun()

    # --- TAB 2: COMPLETED AUDIT ARCHIVE ---
    with tab_completed:
        completed_jobs = [j for j in gst_jobs if j.get("is_billed")]

        if not completed_jobs:
            st.info("No completed audit records found.")
        else:
            st.caption(f"Showing **{len(completed_jobs)}** completed audit record(s):")

            st.markdown("""
                <div class="adnet-table-header" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="display: grid; grid-template-columns: 1.1fr 1fr 1.8fr 1.8fr 1.4fr 1.3fr 1.4fr; align-items: center; gap: 8px;">
                        <div class="tbl-cell-header">Job No.</div>
                        <div class="tbl-cell-header">Date</div>
                        <div class="tbl-cell-header">Client</div>
                        <div class="tbl-cell-header">GSTIN</div>
                        <div class="tbl-cell-header">Place of Supply</div>
                        <div class="tbl-cell-header" style="text-align: right;">Taxable Value</div>
                        <div class="tbl-cell-header" style="text-align: center;">Status</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            def _open_ca_comp_modal(target_jid):
                st.session_state["view_ca_job_id"] = target_jid

            for j in completed_jobs:
                jid = j["job_id"]
                job_no = j.get("job_no", str(jid))
                created_date = str(j.get("created_at", ""))[:10] or "N/A"
                client_name = j.get("client_name") or "N/A"
                gstin_val = j.get("gstin") or "NOT SPECIFIED"
                pos_val = str(j.get("place_of_supply") or "19 - West Bengal")

                items = get_job_items(jid) or []
                taxable_amt = sum(float(it.get("amount", 0) or 0) for it in items)
                val_label = f"₹ {taxable_amt:,.2f}"

                r_no, r_date, r_client, r_gstin, r_pos, r_val, r_act = st.columns(
                    [1.1, 1, 1.8, 1.8, 1.4, 1.3, 1.4],
                    vertical_alignment="center",
                )

                with r_no:
                    st.button(f"JOB-{job_no}", key=f"cac_btn_{jid}", type="tertiary", on_click=_open_ca_comp_modal, args=(jid,))
                with r_date:
                    st.button(created_date, key=f"cac_dt_{jid}", type="tertiary", on_click=_open_ca_comp_modal, args=(jid,))
                with r_client:
                    st.button(client_name, key=f"cac_cl_{jid}", type="tertiary", help=client_name, on_click=_open_ca_comp_modal, args=(jid,))
                with r_gstin:
                    st.button(gstin_val, key=f"cac_gst_{jid}", type="tertiary", help=gstin_val, on_click=_open_ca_comp_modal, args=(jid,))
                with r_pos:
                    st.button(pos_val, key=f"cac_pos_{jid}", type="tertiary", help=pos_val, on_click=_open_ca_comp_modal, args=(jid,))
                with r_val:
                    st.button(val_label, key=f"cac_val_{jid}", type="tertiary", on_click=_open_ca_comp_modal, args=(jid,))
                with r_act:
                    st.button("Completed", key=f"cac_act_{jid}", type="secondary", use_container_width=True, on_click=_open_ca_comp_modal, args=(jid,))

                st.markdown("<hr style='margin: 4px 0 8px 0; border: none; border-top: 1px solid #edf2f7;' />", unsafe_allow_html=True)

        view_ca_jid_c = st.session_state.get("view_ca_job_id")
        if view_ca_jid_c:
            job_match_c = next((j for j in completed_jobs if j["job_id"] == view_ca_jid_c), None)
            if job_match_c:
                job_match_items_c = get_job_items(view_ca_jid_c) or []
                show_ca_details_modal(job_match_c, job_match_items_c)