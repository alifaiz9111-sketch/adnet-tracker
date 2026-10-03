import streamlit as st
import pandas as pd
from database import (
    supabase,
    get_all_users,
    create_user,
    get_user_permissions,
    update_user_profile,
    update_user_modules,
    update_user_status,
    delete_user_account,
    get_all_active_jobs,
    extend_job_deadline,
    delete_job_sheet
)
from datetime import date

ALL_MODULES = {
    "MOD_A": "1. Order Intake (Sales)",
    "MOD_B": "2. Design & Proofs",
    "MOD_C": "3. Advance / Accounts",
    "MOD_D": "4. Production Floor",
    "MOD_E": "5. Quality Check (QC)",
    "MOD_F": "6. Dispatch & Delivery",
    "MOD_G": "7. Billing Review",
    "MOD_BILL": "Accounts Billing Queue"
}

def render_overview(user):
    st.title("👑 Executive Overview & Bottlenecks")

    # Fetch all active jobs from the floor
    jobs = get_all_active_jobs()
    df = pd.DataFrame(jobs) if jobs else pd.DataFrame()

    today_str = str(date.today())

    # --- TOP KPI METRICS ---
    c1, c2, c3, c4 = st.columns(4)
    total_active = len(df) if not df.empty else 0
    c1.metric("Active Jobs", total_active)

    # Compute Today's Booking
    today_booking = 0.0
    if not df.empty:
        date_col = "created_at" if "created_at" in df.columns else "date_received"
        if date_col in df.columns:
            today_jobs = df[df[date_col].astype(str).str.startswith(today_str)]
            for j_id in today_jobs["job_id"]:
                try:
                    items = supabase.table("job_items").select("amount").eq("job_id", j_id).execute().data
                    today_booking += sum([float(it.get("amount", 0) or 0) for it in items])
                except Exception:
                    pass
    c2.metric("Today's Booking (₹)", f"₹ {today_booking:,.2f}")

    # Overdue Jobs Counter
    overdue_count = 0
    if not df.empty and "due_date" in df.columns:
        overdue_count = len(df[df["due_date"].astype(str) < today_str])
    c3.metric("Critical Overdue", f"{overdue_count} Jobs")

    # Active Floor Stages
    floor_stages_count = df["current_stage"].nunique() if not df.empty and "current_stage" in df.columns else 0
    c4.metric("Floor Stages Active", floor_stages_count)

    st.markdown("---")

    # --- TAB NAVIGATION ---
    tab_floor, tab_manage = st.tabs(["⚠️ Active Floor Bottleneck Escalation Table", "🗑️ Delete Job Sheets"])

    # TAB 1: BOTTLENECK ESCALATION & EXTENSIONS
    with tab_floor:
        if df.empty:
            st.info("No active jobs currently on the floor.")
        else:
            display_cols = ["job_no", "client_name", "current_stage", "holding_employee_role", "due_date", "priority"]
            available_cols = [c for c in display_cols if c in df.columns]

            # Rename columns for presentation
            rename_map = {
                "job_no": "Job No.",
                "client_name": "Client Name",
                "current_stage": "Stage",
                "holding_employee_role": "Holding Desk",
                "due_date": "Due Date",
                "priority": "Priority"
            }
            view_df = df[available_cols].rename(columns=rename_map)
            st.dataframe(view_df, use_container_width=True, hide_index=True)

            st.markdown("#### ⏳ Authorize Deadline Extension")
            col_sel, col_date, col_rsn = st.columns([2, 1, 2])
            selected_job_no = col_sel.selectbox("Select Job to Extend", df["job_no"].astype(str).tolist(), key="extend_job_select")
            new_date = col_date.date_input("New Extended Due Date", key="extend_due_date")
            reason = col_rsn.text_input("Reason for Extension", placeholder="e.g. Design revision requested by client", key="extend_reason")

            if st.button("Authorize Deadline Extension", type="primary"):
                if not reason.strip():
                    st.warning("Please provide a reason for the extension.")
                else:
                    target_job = df[df["job_no"].astype(str) == selected_job_no].iloc[0]
                    extend_job_deadline(target_job["job_id"], str(new_date), reason, user["user_id"])
                    st.toast(f"Deadline updated for Job #{selected_job_no}!", icon="⏳")
                    st.success(f"Deadline updated for Job #{selected_job_no}!")
                    st.rerun()

    # TAB 2: JOB SHEET DELETION
    with tab_manage:
        st.markdown("#### 🗑️ Remove / Delete a Job Sheet")
        st.caption("Permanently deletes a job sheet, its specifications, and related floor records across all queues.")

        if df.empty:
            st.info("No active jobs available to delete.")
        else:
            job_choices = {
                f"Job #{row['job_no']} - {row['client_name']} ({row.get('current_stage', 'Unknown')})": row["job_id"] 
                for _, row in df.iterrows()
            }
            selected_label = st.selectbox("Select Job to Delete", list(job_choices.keys()), key="delete_job_select")
            selected_id = job_choices[selected_label]

            confirm_delete = st.checkbox("I confirm permanent deletion of this job sheet.", key="confirm_delete_chk")

            if st.button("🚨 Delete Selected Job Sheet", type="secondary"):
                if not confirm_delete:
                    st.warning("Please tick the confirmation checkbox above first.")
                else:
                    success, msg = delete_job_sheet(selected_id)
                    if success:
                        st.toast(msg, icon="🗑️")
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")


def render_user_management(user):
    st.title("👥 Staff & Role Permission Administration")

    # Fetch users
    all_users = get_all_users()
    current_role = user.get("account_type")

    # 1. HIERARCHY FILTER: CEO never sees SUPER_ADMIN or 'admin'
    if current_role == "CEO":
        manageable_users = [
            u for u in all_users 
            if u["account_type"] not in ["SUPER_ADMIN"] and u["username"] != "admin"
        ]
    else:
        # SUPER_ADMIN sees all
        manageable_users = all_users

    # --- TABBED INTERFACE FOR CLEAN WORKFLOW ---
    tab_list, tab_edit, tab_create = st.tabs([
        "📋 Staff Directory", 
        "⚙️ Grant / Revoke / Edit Staff", 
        "➕ Add New Member"
    ])

    # TAB 1: VIEW DIRECTORY
    with tab_list:
        if not manageable_users:
            st.info("No manageable staff accounts found.")
        else:
            df_display = pd.DataFrame(manageable_users)
            df_display = df_display.rename(columns={
                "user_id": "ID",
                "username": "Username",
                "full_name": "Full Name",
                "account_type": "Role",
                "email": "Email",
                "is_active": "Active Status"
            })
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # TAB 2: GRANT / REVOKE / REMOVE CONTROLS
    with tab_edit:
        st.markdown("### 🛠️ Manage Employee Access")
        st.caption("Select any staff member to update their profile, change password, grant/revoke modules, or remove them.")

        if not manageable_users:
            st.info("No staff accounts to manage.")
        else:
            user_options = {
                f"{u['full_name']} (@{u['username']}) - [{u['account_type']}]": u 
                for u in manageable_users
            }
            selected_label = st.selectbox("Select Member to Manage", list(user_options.keys()))
            target_user = user_options[selected_label]
            target_id = target_user["user_id"]

            # Load user's current module permissions
            current_user_modules = get_user_permissions(target_id)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### 👤 Profile & Password")
                new_fname = st.text_input("Full Name", value=target_user["full_name"], key="edit_fn")
                new_email = st.text_input("Email Address", value=target_user.get("email") or "", key="edit_em")
                new_pwd = st.text_input("New Password (leave blank to keep current)", type="password", key="edit_pw")
                is_active = st.checkbox("Account Active (untick to deactivate)", value=bool(target_user.get("is_active", True)), key="edit_act")

                if st.button("💾 Save Profile Changes", type="primary"):
                    update_user_profile(target_id, new_fname, new_email, new_pwd)
                    update_user_status(target_id, is_active)
                    st.success(f"Profile updated for {new_fname}!")
                    st.rerun()

            with col2:
                st.markdown("##### 🔐 Assigned Workspaces / Permissions")
                st.caption("Tick to grant access, untick to revoke:")
                
                selected_modules = []
                for mod_code, mod_label in ALL_MODULES.items():
                    checked = mod_code in current_user_modules
                    if st.checkbox(mod_label, value=checked, key=f"mod_chk_{mod_code}"):
                        selected_modules.append(mod_code)

                if st.button("🔄 Update Module Permissions"):
                    update_user_modules(target_id, selected_modules)
                    st.success(f"Permissions updated for {target_user['full_name']}!")
                    st.rerun()

            st.markdown("---")
            st.markdown("##### 🚨 Danger Zone")
            c_del1, c_del2 = st.columns([3, 1])
            with c_del1:
                confirm_user_del = st.checkbox(
                    f"Confirm permanent deletion of {target_user['full_name']}'s account.", 
                    key="del_user_chk"
                )
            with c_del2:
                if st.button("🗑️ Delete Account", type="secondary"):
                    if not confirm_user_del:
                        st.warning("Please tick the confirmation checkbox.")
                    else:
                        delete_user_account(target_id)
                        st.success(f"User {target_user['full_name']} permanently deleted.")
                        st.rerun()

    # TAB 3: CREATE NEW MEMBER
    with tab_create:
        st.markdown("### ➕ Register New Team Member")
        with st.form("create_member_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            new_uname = f1.text_input("Username *")
            new_pass = f2.text_input("Password *", type="password")
            new_name = f3.text_input("Full Name *")

            new_mail = st.text_input("Email")

            # Hierarchy check on role creation
            if current_role == "SUPER_ADMIN":
                assigned_role = st.selectbox("Account Type", ["STAFF", "CEO"])
            else:
                assigned_role = "STAFF"  # CEO can only create Staff

            st.markdown("##### Select Initial Permissions:")
            p_cols = st.columns(2)
            chosen_mods = []
            for i, (m_code, m_name) in enumerate(ALL_MODULES.items()):
                target_col = p_cols[i % 2]
                if target_col.checkbox(m_name, key=f"new_mod_{m_code}"):
                    chosen_mods.append(m_code)

            submitted = st.form_submit_button("Create Account & Provision Access", type="primary")
            if submitted:
                if not new_uname or not new_pass or not new_name:
                    st.error("Please fill in Username, Password, and Full Name.")
                else:
                    create_user(new_uname, new_pass, new_name, assigned_role, new_mail, chosen_mods)
                    st.success(f"Successfully created {new_name} ({assigned_role})!")
                    st.rerun()