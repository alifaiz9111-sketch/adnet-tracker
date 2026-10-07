import streamlit as st
import pandas as pd
from database import get_all_jobs_pipeline

def render(user):
    st.title("📊 Production Pipeline & Billing Monitor")
    st.caption("Track order throughput, stage bottlenecks, holding desk managers, and archived GST tax invoices.")

    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])
    is_manager = account_type in ["SUPER_ADMIN", "CEO"] or "VIEW_ALL_JOBS" in user_perms

    # Scope data: Managers see company-wide jobs; standard users see jobs they initiated
    user_scope = None if is_manager else user["username"]
    jobs = get_all_jobs_pipeline(user_filter=user_scope)

    if not jobs:
        st.info("No jobs recorded in the pipeline under your view scope.")
        return

    # High-Level Metrics
    total_created = len(jobs)
    total_completed = len([j for j in jobs if j.get("current_stage") == "SETTLED"])
    total_pending = total_created - total_completed
    total_billed = len([j for j in jobs if j.get("invoice_file_url")])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Jobs Created", total_created)
    m2.metric("In-Progress (Pending)", total_pending)
    m3.metric("Settled / Delivered", total_completed)
    m4.metric("GST Invoices Attached", total_billed)

    st.markdown("---")

    # Search & Filtering Bar
    c_search, c_stage, c_status = st.columns([2, 1.2, 1.2])
    with c_search:
        search_query = st.text_input("🔍 Search Job # or Client Name", placeholder="e.g. 0001 or AdNet").strip().lower()
    with c_stage:
        stage_options = ["All Stages", "DESIGN", "PAYMENT", "PRODUCTION", "QC", "DISPATCH", "BILLING_REVIEW", "SETTLED"]
        selected_stage = st.selectbox("Stage Filter", stage_options)
    with c_status:
        billing_filter = st.selectbox("Billing Status", ["All", "Billed (Invoice Uploaded)", "Unbilled"])

    # Filter Pipeline Data
    filtered_jobs = jobs
    if selected_stage != "All Stages":
        filtered_jobs = [j for j in filtered_jobs if j.get("current_stage") == selected_stage]
    
    if billing_filter == "Billed (Invoice Uploaded)":
        filtered_jobs = [j for j in filtered_jobs if j.get("invoice_file_url")]
    elif billing_filter == "Unbilled":
        filtered_jobs = [j for j in filtered_jobs if not j.get("invoice_file_url")]

    if search_query:
        filtered_jobs = [
            j for j in filtered_jobs 
            if search_query in str(j.get("job_no", "")).lower() 
            or search_query in str(j.get("client_name", "")).lower()
        ]

    st.markdown(f"**Showing {len(filtered_jobs)} Job Sheets**")

    # Job Cards Listing
    for job in filtered_jobs:
        with st.container(border=True):
            col_l, col_r = st.columns([3, 1.5])
            
            with col_l:
                st.subheader(f"Job #{job.get('job_no')} — {job.get('client_name')}")
                created_date = str(job.get("created_at", ""))[:10]
                created_by = job.get("order_taken_by") or job.get("created_by") or "Unknown"
                st.caption(f"🗓️ Created: `{created_date}` | 👤 Created By: `{created_by}`")

                if job.get("is_returned"):
                    st.error(f"⚠️ Flagged Return Reason: {job.get('return_reason')}")

            with col_r:
                curr_stage = job.get("current_stage", "UNKNOWN")
                
                if curr_stage == "SETTLED":
                    st.success("✅ **STATUS: SETTLED / CLOSED**")
                else:
                    st.warning(f"📍 **Current Desk:** `{curr_stage}`")
                    desk_manager = job.get("current_desk_manager") or job.get("last_dispatched_by") or "Floor Team"
                    st.info(f"👔 **Holding Desk Manager:** `{desk_manager}`")

                # Bill Viewer & Downloader (Requirement 3)
                inv_url = job.get("invoice_file_url")
                if inv_url:
                    st.link_button("📄 View & Download GST Bill", inv_url, use_container_width=True)
                else:
                    st.caption("🧾 Invoice: *Pending / Unbilled*")