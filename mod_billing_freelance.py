import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("💼 Module 8: Accounts Billing & Invoicing Desk")
    st.caption(f"Operator: **{user['full_name']}** | Role: `{user.get('account_type')}`")

    account_type = user.get("account_type", "STAFF")
    permissions = user.get("permissions") or []
    
    is_ca = (account_type == "FREELANCER_CA")
    is_view_only = ("VIEW_BILLS" in permissions and account_type == "STAFF" and "MOD_BILL" not in permissions)

    # 1. Fetch all jobs
    try:
        res = supabase.table("jobs").select("*").order("job_id", desc=True).execute()
        all_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching jobs: {e}")
        return

    # If CA, completely filter out Non-GST records from memory
    if is_ca:
        all_jobs = [j for j in all_jobs if j.get("billing_type") == "GST" or j.get("current_stage") == "BILLING_QUEUE"]

    # Categorize jobs
    pending_gst = [j for j in all_jobs if j.get("current_stage") == "BILLING_QUEUE"]
    settled_gst = [j for j in all_jobs if j.get("current_stage") == "SETTLED" and j.get("billing_type") == "GST"]
    settled_nongst = [j for j in all_jobs if j.get("current_stage") == "SETTLED" and j.get("billing_type") != "GST"]
    all_settled = [j for j in all_jobs if j.get("current_stage") == "SETTLED"]

    # 2. Top Summary KPI Cards (CA only sees GST metrics)
    if is_ca:
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Pending GST Queue", len(pending_gst))
        with m2:
            st.metric("GST Invoices Filed", len(settled_gst))
    else:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("All Settled Bills", len(all_settled))
        with m2:
            st.metric("Pending GST Queue", len(pending_gst))
        with m3:
            st.metric("GST Billed", len(settled_gst))
        with m4:
            st.metric("Non-GST Settled", len(settled_nongst))

    st.markdown("---")

    # 3. Dynamic Tabs based on Role
    if is_ca:
        tab_list = ["🏛️ GST Invoicing Desk", "📁 GST Invoices Archive"]
        t_desk, t_gst_arch = st.tabs(tab_list)
        t_all, t_nongst = None, None
    else:
        tab_list = ["📑 All Invoices Master", "🏛️ GST Desk & Invoices", "📦 Non-GST Bills Archive"]
        t_all, t_desk, t_nongst = st.tabs(tab_list)
        t_gst_arch = t_desk

    # --- TAB: ALL INVOICES MASTER (Admin / CEO / Manager / Assigned Staff) ---
    if t_all:
        with t_all:
            st.markdown("#### 📑 Combined Master Billing Ledger")
            if not all_settled:
                st.info("No settled bills in the system yet.")
            else:
                for j in all_settled:
                    items = get_job_items(j["job_id"])
                    total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                    b_type = j.get("billing_type", "NON_GST")
                    b_badge = "🏛️ GST" if b_type == "GST" else "📦 Non-GST"

                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2.5, 2, 1.5])
                        with c1:
                            st.markdown(f"**Job #{j.get('job_no')} - {j.get('client_name')}** `[{b_badge}]`")
                            st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                        with c2:
                            st.markdown(f"**Settled Value:** ₹ {total_val:,.2f}")
                            st.caption(f"Order Taken By: `{j.get('order_taken_by') or 'N/A'}`")
                        with c3:
                            if j.get("invoice_file_url"):
                                st.link_button("📥 Download Invoice", j["invoice_file_url"], use_container_width=True)
                            else:
                                st.caption("Direct Non-GST Settlement (No File)")

    # --- TAB: GST DESK & INVOICES (CA, Admin, Manager, Assigned Staff) ---
    with t_desk:
        st.markdown("#### ⏳ Pending GST Invoicing Queue")
        if not pending_gst:
            st.info("No jobs pending GST tax invoicing.")
        else:
            for j in pending_gst:
                items = get_job_items(j["job_id"])
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 2, 1.5])
                    with c1:
                        st.markdown(f"**Job #{j.get('job_no')} - {j.get('client_name')}**")
                        st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                        st.caption(f"Booked By: `{j.get('order_taken_by') or 'N/A'}` | Due: `{j.get('due_date')}`")
                    with c2:
                        st.markdown(f"**Taxable Value:** ₹ {total_val:,.2f}")
                        for it in items:
                            st.caption(f"• {it.get('item_name', 'Item')} ({it.get('quantity')} {it.get('unit')})")
                    with c3:
                        if is_view_only:
                            st.info("Pending CA Invoicing")
                        else:
                            with st.popover("📤 Upload GST Bill"):
                                inv_url = st.text_input("Invoice File / Google Drive URL", key=f"inv_url_{j['job_id']}")
                                if st.button("Complete & Settle", key=f"btn_set_{j['job_id']}", type="primary"):
                                    if not inv_url.strip():
                                        st.error("Please provide invoice link.")
                                    else:
                                        supabase.table("jobs").update({
                                            "current_stage": "SETTLED",
                                            "is_billed": True,
                                            "billing_type": "GST",
                                            "invoice_file_url": inv_url.strip(),
                                            "invoice_uploaded_by": user["full_name"]
                                        }).eq("job_id", j["job_id"]).execute()
                                        st.success("Invoice uploaded & job settled.")
                                        st.rerun()

        st.markdown("---")
        st.markdown("#### 📁 Filed GST Invoices Archive")
        if not settled_gst:
            st.info("No GST invoices recorded yet.")
        else:
            for j in settled_gst:
                items = get_job_items(j["job_id"])
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 2, 1.5])
                    with c1:
                        st.markdown(f"**Job #{j.get('job_no')} - {j.get('client_name')}**")
                        st.caption(f"Billed By: `{j.get('invoice_uploaded_by') or 'CA'}`")
                    with c2:
                        st.markdown(f"**Billed Value:** ₹ {total_val:,.2f}")
                    with c3:
                        if j.get("invoice_file_url"):
                            st.link_button("📥 Download Invoice", j["invoice_file_url"], use_container_width=True)

    # --- TAB: NON-GST ARCHIVE (Completely Hidden from CA) ---
    if t_nongst:
        with t_nongst:
            st.markdown("#### 📦 Non-GST Direct Settlements")
            if not settled_nongst:
                st.info("No Non-GST settlements recorded.")
            else:
                for j in settled_nongst:
                    items = get_job_items(j["job_id"])
                    total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2.5, 2, 1.5])
                        with c1:
                            st.markdown(f"**Job #{j.get('job_no')} - {j.get('client_name')}**")
                            st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                        with c2:
                            st.markdown(f"**Total Settled:** ₹ {total_val:,.2f}")
                            st.caption(f"Order Taken By: `{j.get('order_taken_by') or 'N/A'}`")
                        with c3:
                            st.success("✅ Direct Settled")