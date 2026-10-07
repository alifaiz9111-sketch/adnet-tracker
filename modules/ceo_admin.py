from datetime import datetime
import streamlit as st
from database import (
    supabase, 
    get_all_users, 
    create_user, 
    update_user_status, 
    extend_job_deadline, 
    delete_job_sheet
)

def render_overview(user):
    st.subheader("👑 Executive Overview & Floor KPI Monitor")
    st.caption("High-level floor throughput and active job controls.")

    try:
        jobs_res = supabase.table("jobs").select("*").execute()
        all_jobs = jobs_res.data or []
        items_res = supabase.table("job_items").select("*").execute()
        all_items = items_res.data or []
    except Exception:
        all_jobs, all_items = [], []

    total_orders = len(all_jobs)
    active_jobs = [j for j in all_jobs if j.get("current_stage") != "SETTLED"]
    settled_jobs = [j for j in all_jobs if j.get("current_stage") == "SETTLED"]
    total_val = sum(float(it.get("amount", 0) or 0) for it in all_items)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Jobs Logged", total_orders)
    with k2:
        st.metric("Active On Floor", len(active_jobs))
    with k3:
        st.metric("Billed & Settled", len(settled_jobs))
    with k4:
        st.metric("Pipeline Value", f"₹ {total_val:,.2f}")

    st.markdown("---")
    st.markdown("#### 🛠️ Active Jobs Management & Deadline Extensions")

    if not active_jobs:
        st.info("No active jobs requiring administrative management.")
        return

    for job in active_jobs:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"**Job #{job['job_no']} - {job['client_name']}**")
                st.caption(f"Stage: `{job['current_stage']}` | Due: `{job['due_date']}`")
            with c2:
                with st.popover("📅 Extend Target Delivery Date"):
                    new_due = st.date_input("New Target Date", key=f"due_{job['job_id']}")
                    ext_reason = st.text_input("Extension Reason", key=f"ext_{job['job_id']}")
                    if st.button("Save New Date", key=f"btn_due_{job['job_id']}", type="primary"):
                        extend_job_deadline(job["job_id"], user["user_id"], new_due, ext_reason)
                        st.success("Target delivery date updated.")
                        st.rerun()
            with c3:
                if user.get("account_type") == "SUPER_ADMIN":
                    with st.popover("🗑️ Cascading Delete"):
                        st.warning("Permanently delete this entire jobsheet and all child records?")
                        if st.button("Confirm Delete", key=f"del_{job['job_id']}", type="primary"):
                            delete_job_sheet(job["job_id"])
                            st.success("Jobsheet deleted.")
                            st.rerun()

def render_user_management(user):
    st.subheader("👥 Staff & RBAC Administration")
    st.caption("Manage employee accounts, floor workstation assignments, and access control.")

    tab_users, tab_add = st.tabs(["Active Directory", "Add New Staff Member"])

    with tab_users:
        users = get_all_users()
        current_account_type = user.get("account_type")

        # The CEO cannot view or modify the root admin account
        display_users = [
            u for u in users 
            if not (current_account_type == "CEO" and u.get("username") == "admin")
        ]

        for u in display_users:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"**{u['full_name']}** (`@{u['username']}`)")
                    st.caption(f"Role: `{u['account_type']}` | Last Login: `{u.get('last_login', 'Never')}`")
                with c2:
                    st.write(f"**Workstations:** {', '.join(u.get('permissions', []) or ['None'])}")
                with c3:
                    if u["username"] != "admin":
                        is_active = u.get("is_active", True)
                        btn_txt = "Deactivate" if is_active else "Reactivate"
                        if st.button(btn_txt, key=f"usr_st_{u['user_id']}"):
                            update_user_status(u["user_id"], not is_active)
                            st.rerun()

    with tab_add:
        with st.form("add_user_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                new_username = st.text_input("Username *").strip()
                new_password = st.text_input("Temporary Password *", type="password").strip()
                new_name = st.text_input("Full Employee Name *").strip()
            with col_b:
                account_type = st.selectbox("Account Role", ["STAFF", "AUDITOR", "FREELANCER_CA", "CEO"])
                perms = st.multiselect(
                    "Workstation Desks Allowed", 
                    ["MOD_A", "MOD_B", "MOD_C", "MOD_D", "MOD_E", "MOD_F", "MOD_G", "MOD_BILL"],
                    default=["MOD_D"]
                )

            if st.form_submit_button("Create Employee Profile", type="primary", use_container_width=True):
                if not (new_username and new_password and new_name):
                    st.error("Please fill in all mandatory fields.")
                else:
                    success, res = create_user(new_username, new_password, new_name, account_type, perms)
                    if success:
                        st.success(f"Employee @{new_username} created successfully.")
                        st.rerun()
                    else:
                        st.error(f"Error: {res}")