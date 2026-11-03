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


def _reset_production_filters():
    st.session_state["prod_search_kw"] = ""
    st.session_state["prod_sort_filter"] = "Recent Jobs (Newest First)"
    st.session_state["prod_page_num"] = 1


def render(user):
    st.subheader("⚙️ Module 4: Production Floor & Fabrication Desk")
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

    # Fetch available vendors for outsourcing
    vendors = get_all_vendors()
    vendor_options = ["In-House Floor"] + [
        f"{v['vendor_name']} ({v.get('category') or 'Job-Work'})" 
        for v in vendors if v.get("is_active", True)
    ]

    # --- TOP FILTER & SEARCH BAR ---
    with st.container(border=True):
        f1, f2, f3 = st.columns([4, 3, 1.5])
        with f1:
            search_kw = st.text_input(
                "Search Orders",
                placeholder="Search Job No, Client, Contact Phone...",
                key="prod_search_kw"
            ).strip().lower()
        with f2:
            sort_order = st.selectbox(
                "Sort By",
                options=["Recent Jobs (Newest First)", "Oldest Jobs", "Delivery Due Soonest"],
                key="prod_sort_filter"
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

    # Counter Bar
    st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** pending production jobs")

    if not page_records:
        st.info("No active jobs pending on the production floor.")
        return

    # --- TABLE STYLES ---
    st.markdown("""
        <style>
        .tbl-cell-text {
            font-size: 13px !important;
            font-family: inherit !important;
            color: #1e293b !important;
            font-weight: 500 !important;
            line-height: 1.4 !important;
            padding-top: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tbl-cell-header {
            font-size: 13px !important;
            font-family: inherit !important;
            font-weight: 700 !important;
            color: #475569 !important;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .adnet-pill-prod {
            background-color: #fef2f2;
            color: #b91c1c;
            border: 1px solid #fecaca;
            padding: 3px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 700;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- TABLE HEADER ---
    st.markdown("""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
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

    # --- TABLE ROWS ---
    for job in page_records:
        jid = job["job_id"]
        job_no = job.get("job_no", str(jid))
        created_date = str(job.get("created_at", ""))[:10] or "N/A"
        client_name = job.get("client_name") or "N/A"
        contact_p = job.get("contact_person") or "N/A"
        contact_ph = job.get("contact_phone") or "N/A"
        due_date_str = str(job.get("due_date") or "N/A")

        items = get_job_items(jid)
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        r_chk, r_no, r_date, r_client, r_contact, r_due, r_val, r_act = st.columns(
            [0.4, 1.2, 1, 1.8, 1.6, 1.1, 1.2, 1.7]
        )

        with r_chk:
            st.checkbox(" ", key=f"prod_chk_{jid}", label_visibility="collapsed")

        with r_no:
            # Clickable popover to open complete job sheet details & specs
            with st.popover(f"📄 JOB-{job_no}", use_container_width=True):
                st.markdown(f"### ⚙️ Production Sheet: #{job_no}")
                st.caption(f"**Client:** {client_name} | **Contact:** {contact_p} ({contact_ph})")
                if job.get("is_returned"):
                    st.error(f"⚠️ Return Notice from {job.get('returned_by')}: {job.get('return_reason')}")

                st.markdown("---")
                
                # Tabbed Production Workflow Inside the Modal
                p_tab1, p_tab2, p_tab3 = st.tabs(["📦 Items & Specs", "🏭 Vendor Job-Work", "📄 Paper Fabrications"])

                with p_tab1:
                    st.markdown("##### Ordered Items")
                    for idx, it in enumerate(items, 1):
                        st.markdown(f"**{idx}. {it.get('item_name')}** — `{it.get('quantity')} {it.get('unit', 'Pcs')}` @ ₹{float(it.get('rate', 0)):,.2f}")
                        if it.get("specifications"):
                            st.caption(f"⚙️ **Specs / Size:** {it.get('specifications')}")
                        if it.get("delivery_address"):
                            st.caption(f"📍 **Delivery:** {it.get('delivery_address')}")

                with p_tab2:
                    st.markdown("##### Outsource Job-Work Details")
                    v_names = [v.get("vendor_name", "Vendor") for v in vendors if v.get("is_active", True)] or ["General Vendor"]
                    sel_vendor = st.selectbox("Assign Outsource Vendor", options=v_names, key=f"pop_v_{jid}")

                    saved_v_jobs = get_custom_presets("VENDOR_JOB")
                    base_item_opts = [it.get("item_name", "").strip() for it in items if it.get("item_name")]
                    combined_jobs = sorted(list(set(base_item_opts + saved_v_jobs))) + ["NEW"]
                    sel_v_job = st.selectbox("Job Work Item", options=combined_jobs, key=f"pop_v_job_{jid}")

                    if sel_v_job == "NEW":
                        new_v = st.text_input("Enter New Outsource Job Name *", key=f"pop_v_new_{jid}").strip()
                        if new_v and st.button("Save New Job Preset", key=f"btn_save_v_{jid}"):
                            add_custom_preset("VENDOR_JOB", new_v)
                            st.rerun()

                    v_sz1, v_sz2, v_sz3, v_sz4 = st.columns(4)
                    with v_sz1:
                        st.number_input("W", value=1.0, step=0.1, key=f"pop_vw_{jid}")
                    with v_sz2:
                        st.number_input("B", value=1.0, step=0.1, key=f"pop_vb_{jid}")
                    with v_sz3:
                        st.number_input("H", value=1.0, step=0.1, key=f"pop_vh_{jid}")
                    with v_sz4:
                        st.selectbox("Unit", ["Inch", "Ft", "mm"], key=f"pop_vu_{jid}")

                    st.number_input("Quantity", min_value=1, value=1, step=1, key=f"pop_vq_{jid}")

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
                    fab_sel = st.selectbox("Fabrication Task", options=all_fabs, key=f"pop_fab_{jid}")

                    if fab_sel == "NEW":
                        new_f = st.text_input("Enter New Fabrication Description *", key=f"pop_f_new_{jid}").strip()
                        if new_f and st.button("Save Fabrication Preset", key=f"btn_save_f_{jid}"):
                            add_custom_preset("FABRICATION", new_f)
                            st.rerun()

                    f_sz1, f_sz2, f_sz3, f_sz4 = st.columns(4)
                    with f_sz1:
                        st.number_input("W", value=1.0, step=0.1, key=f"pop_fw_{jid}")
                    with f_sz2:
                        st.number_input("B", value=1.0, step=0.1, key=f"pop_fb_{jid}")
                    with f_sz3:
                        st.number_input("H", value=1.0, step=0.1, key=f"pop_fh_{jid}")
                    with f_sz4:
                        st.selectbox("Unit", ["Inch", "Ft", "mm"], key=f"pop_fu_{jid}")

                    st.number_input("Quantity", min_value=1, value=1, step=1, key=f"pop_fq_{jid}")

        with r_date:
            st.markdown(f"<div class='tbl-cell-text'>{created_date}</div>", unsafe_allow_html=True)

        with r_client:
            st.markdown(f"<div class='tbl-cell-text' title='{client_name}'>{client_name}</div>", unsafe_allow_html=True)

        with r_contact:
            st.markdown(f"<div class='tbl-cell-text' title='{contact_p} ({contact_ph})'>{contact_p} <span style='color:#64748b; font-size:11px;'>({contact_ph})</span></div>", unsafe_allow_html=True)

        with r_due:
            st.markdown(f"<div class='tbl-cell-text'>{due_date_str}</div>", unsafe_allow_html=True)

        with r_val:
            st.markdown(f"<div class='tbl-cell-text' style='text-align: right; font-weight: 700;'>₹ {total_val:,.2f}</div>", unsafe_allow_html=True)

        with r_act:
            action_choice = st.selectbox(
                "Action",
                options=["Select Action", "✅ Production Completed (Send to QC)", "⚠️ Return / Flag Job"],
                index=0,
                key=f"act_prod_{jid}",
                label_visibility="collapsed"
            )

            if action_choice == "✅ Production Completed (Send to QC)":
                with st.popover(f"Confirm QC Handover #{job_no}", use_container_width=True):
                    st.success(f"Forward Job #{job_no} directly to the QC Desk?")
                    if st.button("Confirm Handover", key=f"btn_qc_confirm_{jid}", type="primary", use_container_width=True):
                        try:
                            supabase.table("jobs").update({
                                "current_stage": "QC",
                                "is_returned": False
                            }).eq("job_id", int(jid)).execute()
                            log_audit(user["user_id"], "PRODUCTION_COMPLETED", f"Job #{job_no} sent to QC Desk")
                            st.success(f"Job #{job_no} forwarded to QC Desk.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update status: {e}")

            elif action_choice == "⚠️ Return / Flag Job":
                with st.popover(f"Return Job #{job_no}", use_container_width=True):
                    st.markdown("#### Return Station")
                    return_target = st.selectbox(
                        "Return To Station",
                        ["PAYMENT", "DESIGN", "SALES"],
                        format_func=lambda x: {
                            "PAYMENT": "💳 Accounts / Advance Clearance",
                            "DESIGN": "🎨 Design & Proofs",
                            "SALES": "📝 Order Intake / Sales"
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
                            try:
                                supabase.table("jobs").update({
                                    "current_stage": return_target,
                                    "is_returned": True,
                                    "returned_by": f"{user['full_name']} (Production)",
                                    "return_reason": reason.strip()
                                }).eq("job_id", int(jid)).execute()
                                log_audit(user["user_id"], "PRODUCTION_RETURN", f"Job #{job_no} returned to {return_target}: {reason.strip()}")
                                st.warning(f"Job #{job_no} returned to {return_target}.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to return job: {e}")

    # --- PAGINATION CONTROLS AT BOTTOM ---
    if total_pages > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns([2, 1, 2, 1, 2])

        with p_c2:
            if st.button("◀ Previous", disabled=(curr_page <= 1), use_container_width=True, key="prod_pg_prev"):
                st.session_state.prod_page_num = max(1, curr_page - 1)
                st.rerun()

        with p_c3:
            st.markdown(
                f"<div style='text-align: center; padding-top: 6px; font-size: 14px; font-weight: 600; color: #475569;'>"
                f"Page {curr_page} of {total_pages}"
                f"</div>",
                unsafe_allow_html=True
            )

        with p_c4:
            if st.button("Next ▶", disabled=(curr_page >= total_pages), use_container_width=True, key="prod_pg_next"):
                st.session_state.prod_page_num = min(total_pages, curr_page + 1)
                st.rerun()