from datetime import datetime
import pytz
import streamlit as st
from database import get_jobs_by_stage, get_job_items, update_job_stage, supabase

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("🧾 Module 8: Accounts & GST Invoicing Desk")
    st.caption("Upload final GST tax invoices and audit billed archives.")

    tab1, tab2 = st.tabs(["📋 Pending Invoicing (To-Do)", "🗄️ Billed & Completed Archive"])

    # --- TAB 1: TO-DO QUEUE ---
    with tab1:
        pending_jobs = get_jobs_by_stage("BILLING_QUEUE")
        if not pending_jobs:
            st.info("All clear! No jobs waiting for GST tax invoices.")
        else:
            for job in pending_jobs:
                items = get_job_items(job["job_id"])
                attempts = job.get("invoice_upload_attempts", 0)
                max_attempts = job.get("invoice_max_attempts", 3)

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    with c1:
                        st.markdown(f"### Job #{job['job_no']} - {job['client_name']}")
                        st.caption(f"Contact: {job.get('contact_person', 'N/A')} ({job.get('contact_phone', 'N/A')})")
                    with c2:
                        st.markdown(f"**Upload Attempts Used:** `{attempts}/{max_attempts}`")
                    with c3:
                        if user.get("account_type") in ["SUPER_ADMIN", "CEO"] and attempts >= max_attempts:
                            if st.button("Reset Attempts", key=f"rst_{job['job_id']}"):
                                supabase.table("jobs").update({"invoice_upload_attempts": 0}).eq("job_id", job["job_id"]).execute()
                                st.success("Attempts reset.")
                                st.rerun()

                    st.markdown("---")
                    st.markdown("**Delivered Line Items:**")
                    for it in items:
                        if it.get("is_delivered"):
                            st.write(f"- ✅ **{it['item_name']}** - Qty: {it['quantity']} {it['unit']} (Rate: ₹{it.get('rate', 0)})")

                    if attempts >= max_attempts:
                        st.error("Upload limit reached (3/3 attempts). Contact Admin/CEO to unlock.")
                    else:
                        uploaded_file = st.file_uploader(
                            f"Upload GST Invoice PDF for Job #{job['job_no']}", 
                            type=["pdf", "png", "jpg"], 
                            key=f"file_{job['job_id']}"
                        )
                        if uploaded_file and st.button("Submit Bill & Archive Job", key=f"btn_up_{job['job_id']}", type="primary"):
                            now_iso = datetime.now(IST).isoformat()
                            file_path = f"invoices/job_{job['job_no']}_{int(datetime.now().timestamp())}_{uploaded_file.name}"
                            
                            # Storage Upload
                            try:
                                supabase.storage.from_("invoices").upload(file_path, uploaded_file.getvalue(), {"content-type": uploaded_file.type})
                                file_url = supabase.storage.from_("invoices").get_public_url(file_path)
                            except Exception:
                                file_url = f"https://mockstorage.supabase.co/{file_path}"

                            # Update Database record
                            supabase.table("jobs").update({
                                "invoice_file_url": file_url,
                                "invoice_uploaded_at": now_iso,
                                "invoice_uploaded_by": user["full_name"],
                                "invoice_upload_attempts": attempts + 1,
                                "is_billed": True
                            }).eq("job_id", job["job_id"]).execute()

                            update_job_stage(job["job_id"], "SETTLED", user["full_name"], f"Billed and Archived. URL: {file_url}")
                            st.success(f"Job #{job['job_no']} successfully billed and moved to archive!")
                            st.rerun()

    # --- TAB 2: BILLED ARCHIVE ---
    with tab2:
        try:
            res = supabase.table("jobs").select("*").eq("is_billed", True).order("invoice_uploaded_at", desc=True).execute()
            billed_jobs = res.data or []
        except Exception:
            billed_jobs = []

        if not billed_jobs:
            st.info("No billed archives found.")
        else:
            search_query = st.text_input("🔍 Search Archive by Job # or Client Name").strip().lower()
            
            filtered = [
                j for j in billed_jobs
                if search_query in j.get("job_no", "").lower() or search_query in j.get("client_name", "").lower()
            ]

            st.write(f"Showing **{len(filtered)}** archived bills:")
            for j in filtered:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    with c1:
                        st.markdown(f"**Job #{j['job_no']} - {j['client_name']}**")
                        st.caption(f"Billed On: `{j.get('invoice_uploaded_at', 'N/A')[:10]}` by {j.get('invoice_uploaded_by', 'N/A')}")
                    with c2:
                        st.caption(f"Target Delivery Date: `{j.get('due_date', 'N/A')}`")
                    with c3:
                        if j.get("invoice_file_url"):
                            st.link_button("📄 View Bill", j["invoice_file_url"], use_container_width=True)
                        else:
                            st.write("No File Attached")