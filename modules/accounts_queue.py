import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    supabase,
    get_unbilled_jobs,
    get_billed_jobs,
    upload_invoice_file,
    reset_invoice_attempts,
    get_today_uploaded_invoices_count
)

def render(user):
    st.title("🧾 Accounts & GST Invoicing Portal")
    user_role = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])
    can_override = user_role in ["SUPER_ADMIN", "CEO"]

    # Daily Upload Notification Banner (Auditors, Admins, CEOs)
    today_cnt = get_today_uploaded_invoices_count()
    if today_cnt > 0:
        st.info(f"🔔 **Notification:** **{today_cnt} new GST bill(s)** uploaded today!", icon="📢")

    # Fetch Data
    unbilled_jobs = get_unbilled_jobs()
    billed_jobs = get_billed_jobs()

    tab_unbilled, tab_billed = st.tabs([
        f"⏳ 1. Pending Invoicing ({len(unbilled_jobs)})",
        f"✅ 2. Billed & Completed Archive ({len(billed_jobs)})"
    ])

    # =========================================================================
    # SECTION 1: UNBILLED JOBS (FREELANCER UPLOAD SECTION)
    # =========================================================================
    with tab_unbilled:
        st.markdown("### 📋 Jobs Awaiting GST Bill Generation")
        st.caption("Upload the finalized GST Tax Invoice. All job details and delivery items are pre-filled and locked.")

        if not unbilled_jobs:
            st.success("🎉 All clear! There are no unbilled jobs pending.")
        else:
            for job in unbilled_jobs:
                job_id = job["job_id"]
                job_no = job["job_no"]
                client = job["client_name"]
                attempts = job.get("invoice_upload_attempts", 0) or 0
                max_attempts = job.get("invoice_max_attempts", 3) or 3
                rem_attempts = max(0, max_attempts - attempts)

                with st.expander(f"📦 Job #{job_no} — {client} (Upload attempts remaining: {rem_attempts}/{max_attempts})", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.text_input("Job No.", value=job_no, disabled=True, key=f"ub_no_{job_id}")
                    c1.text_input("Client Name", value=client, disabled=True, key=f"ub_cl_{job_id}")
                    
                    c2.text_input("GST No.", value=job.get("gst_no") or "N/A", disabled=True, key=f"ub_gst_{job_id}")
                    c2.text_input("Order Date", value=str(job.get("date_received")), disabled=True, key=f"ub_dt_{job_id}")

                    c3.text_input("Upload Desk", value=user["full_name"], disabled=True, key=f"ub_usr_{job_id}")
                    c3.text_input("System Timestamp", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), disabled=True, key=f"ub_ts_{job_id}")

                    # Display item delivery status so CA knows what was actually delivered
                    st.markdown("##### 📦 Items Delivered Verification")
                    items = supabase.table("job_items").select("*").eq("job_id", job_id).execute().data
                    if items:
                        item_rows = []
                        for it in items:
                            item_rows.append({
                                "Item": it.get("description_spec"),
                                "Material": it.get("material"),
                                "Ordered Qty": it.get("qty"),
                                "Delivered?": "✅ Delivered" if it.get("is_delivered") else "⏳ Not Yet Dispatched"
                            })
                        st.dataframe(pd.DataFrame(item_rows), use_container_width=True, hide_index=True)

                    # Single Upload Control
                    st.markdown("---")
                    if rem_attempts > 0:
                        st.markdown("##### 📤 Upload GST Tax Invoice Document")
                        uploaded_file = st.file_uploader(
                            f"Select Invoice File for Job #{job_no} (.pdf, .jpg, .png)",
                            type=["pdf", "png", "jpg", "jpeg"],
                            key=f"inv_upload_{job_id}"
                        )

                        if uploaded_file is not None:
                            if st.button(f"Confirm & Upload Invoice for Job #{job_no}", type="primary", key=f"btn_up_{job_id}"):
                                with st.spinner("Uploading and archiving..."):
                                    file_bytes = uploaded_file.read()
                                    ok, msg = upload_invoice_file(job_id, file_bytes, uploaded_file.name, user["full_name"])
                                    if ok:
                                        st.toast(msg, icon="✅")
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                    else:
                        st.error(f"⛔ Maximum upload attempts ({max_attempts}) reached for this job.")
                        if can_override:
                            if st.button(f"🔓 Authorize More Upload Attempts (Admin/CEO)", key=f"rst_{job_id}"):
                                reset_invoice_attempts(job_id)
                                st.success("Attempts reset! The CA can now upload again.")
                                st.rerun()
                        else:
                            st.caption("Please ask Admin or CEO to grant additional upload attempts.")

    # =========================================================================
    # SECTION 2: BILLED JOBS ARCHIVE (SEARCH, FILTER, VIEW, DOWNLOAD)
    # =========================================================================
    with tab_billed:
        st.markdown("### 📂 Billed & Settled Invoices Archive")
        st.caption("Filter, view, and download uploaded invoices.")

        if not billed_jobs:
            st.info("No billed jobs archived yet.")
        else:
            df_billed = pd.DataFrame(billed_jobs)

            col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 2])
            with col_f1:
                search_kw = st.text_input("🔍 Search Job # / Client", key="search_billed")
            with col_f2:
                client_list = ["All Clients"] + sorted(list(set(df_billed["client_name"].dropna().tolist())))
                selected_client = st.selectbox("Filter by Client", client_list, key="filter_client")
            with col_f3:
                date_filter = st.date_input("Filter Uploaded Date Range", value=[], key="filter_dates")

            filtered = df_billed.copy()
            if search_kw.strip():
                kw = search_kw.strip().lower()
                filtered = filtered[
                    filtered["job_no"].astype(str).str.lower().str.contains(kw) |
                    filtered["client_name"].astype(str).str.lower().str.contains(kw)
                ]
            if selected_client != "All Clients":
                filtered = filtered[filtered["client_name"] == selected_client]

            if len(date_filter) == 2:
                start_d, end_d = str(date_filter[0]), str(date_filter[1])
                filtered = filtered[
                    (filtered["invoice_uploaded_at"].astype(str) >= start_d) &
                    (filtered["invoice_uploaded_at"].astype(str) <= f"{end_d} 23:59:59")
                ]

            st.write(f"Showing **{len(filtered)}** billed job(s):")

            for _, row in filtered.iterrows():
                j_id = row["job_id"]
                j_no = row["job_no"]
                c_name = row["client_name"]
                up_by = row.get("invoice_uploaded_by", "CA")
                up_at = str(row.get("invoice_uploaded_at", ""))[:19]
                file_url = row.get("invoice_file_url")
                attempts_used = row.get("invoice_upload_attempts", 1)

                with st.expander(f"📄 Job #{j_no} — {c_name} (Uploaded: {up_at})"):
                    r1, r2 = st.columns([3, 1])
                    with r1:
                        st.markdown(f"**Client:** {c_name} | **GST:** {row.get('gst_no', 'N/A')}")
                        st.markdown(f"**Uploaded By:** {up_by} on `{up_at}` | **Attempts used:** {attempts_used}/3")
                    
                    with r2:
                        if file_url:
                            st.link_button("👁️ View / Download Bill", file_url, type="primary", use_container_width=True)
                        else:
                            st.caption("No file attached.")

                    if attempts_used < (row.get("invoice_max_attempts") or 3):
                        with st.popover("🔄 Re-upload Revision"):
                            st.caption(f"Attempts used: {attempts_used}/3")
                            reup_file = st.file_uploader("Replace invoice document", type=["pdf", "png", "jpg"], key=f"reup_{j_id}")
                            if reup_file and st.button("Confirm Replace", key=f"btn_re_{j_id}"):
                                ok, msg = upload_invoice_file(j_id, reup_file.read(), reup_file.name, user["full_name"])
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                    elif can_override:
                        if st.button(f"🔓 Reset Attempts for Job #{j_no}", key=f"rst_billed_{j_id}"):
                            reset_invoice_attempts(j_id)
                            st.success("Attempts reset!")
                            st.rerun()