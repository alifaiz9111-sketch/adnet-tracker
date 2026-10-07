import streamlit as st
from database import (
    supabase,
    get_all_users,
    create_user,
    update_user_status,
    get_user_permissions,
    update_user_profile,
    update_user_modules,
    delete_user_account,
    get_dynamic_dropdown_options,
    add_dynamic_option,
    delete_job_sheet,
    reset_invoice_attempts
)

SYSTEM_MODULES = [
    ("MOD_A", "Workstation 1: Order Intake & Sales (Self Only)"),
    ("MOD_A_MGR", "Workstation 1: Sales Manager (View All Intake Jobs)"),
    ("MOD_B", "Workstation 2: Design & Proofing"),
    ("MOD_C", "Workstation 3: Advance & Accounts"),
    ("MOD_D", "Workstation 4: Production Floor"),
    ("MOD_E", "Workstation 5: Quality Check (QC)"),
    ("MOD_F", "Workstation 6: Dispatch & Logistics"),
    ("MOD_G", "Workstation 7: Billing Review"),
    ("MOD_BILL", "Workstation 8: CA GST Invoicing Queue"),
    ("PERM_MONITOR", "General: Status Pipeline & Holding Desk Monitor"),
    ("VIEW_BILLS", "General: View & Download Completed GST Bills")
]

def render(user):
    st.title("🛠️ System Administration & Master Controls")
    st.caption("Central management for workforce accounts, role permissions, vendor master directory, and system dropdowns.")

    # Guard check: Only Super Admin and CEO can access this panel
    if user.get("account_type") not in ["CEO", "SUPER_ADMIN"]:
        st.error("⛔ Access Denied. Only Executive Management (CEO / Super Admin) can access this module.")
        return

    tab_users, tab_vendors, tab_masters, tab_ops = st.tabs([
        "👥 Workforce & Access",
        "🏢 Vendor Directory",
        "📋 Master Dropdowns",
        "⚙️ System Operations & Audit"
    ])

    # =========================================================================
    # TAB 1: WORKFORCE & ACCESS CONTROL
    # =========================================================================
    with tab_users:
        sub_tab1, sub_tab2 = st.tabs(["📋 Active Workforce", "➕ Register New User"])

        with sub_tab1:
            users_list = get_all_users()
            if not users_list:
                st.info("No workforce users found.")
            else:
                for u in users_list:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2.5, 2, 1.5])
                        with c1:
                            status_badge = "🟢 Active" if u.get("is_active") else "🔴 Deactivated"
                            st.markdown(f"### {u.get('full_name')} (`@{u.get('username')}`)")
                            st.caption(f"Role: **{u.get('account_type')}** | Email: `{u.get('email') or 'N/A'}` | Status: {status_badge}")
                        
                        with c2:
                            current_perms = get_user_permissions(u["user_id"])
                            with st.popover("🔑 Edit Access Permissions"):
                                st.markdown(f"**Permissions for @{u.get('username')}**")
                                selected_mods = []
                                for mod_code, mod_label in SYSTEM_MODULES:
                                    checked = mod_code in current_perms
                                    if st.checkbox(mod_label, value=checked, key=f"perm_{u['user_id']}_{mod_code}"):
                                        selected_mods.append(mod_code)
                                if st.button("Save Permissions", key=f"btn_save_perm_{u['user_id']}", type="primary"):
                                    update_user_modules(u["user_id"], selected_mods)
                                    st.success("Permissions updated!")
                                    st.rerun()

                        with c3:
                            with st.popover("⚙️ User Settings"):
                                new_name = st.text_input("Full Name", value=u.get("full_name", ""), key=f"nm_{u['user_id']}")
                                new_email = st.text_input("Email", value=u.get("email") or "", key=f"em_{u['user_id']}")
                                new_pass = st.text_input("Reset Password", type="password", placeholder="Leave blank to keep current", key=f"pw_{u['user_id']}")
                                
                                if st.button("Update Profile", key=f"btn_prof_{u['user_id']}"):
                                    update_user_profile(u["user_id"], new_name.strip(), new_email.strip(), new_pass)
                                    st.success("Profile updated.")
                                    st.rerun()

                                st.markdown("---")
                                if u.get("is_active"):
                                    if st.button("🚫 Deactivate Account", key=f"deact_{u['user_id']}"):
                                        update_user_status(u["user_id"], False)
                                        st.rerun()
                                else:
                                    if st.button("✅ Reactivate Account", key=f"react_{u['user_id']}"):
                                        update_user_status(u["user_id"], True)
                                        st.rerun()

                                if st.button("🗑️ Delete User Permanently", key=f"del_{u['user_id']}", type="primary"):
                                    delete_user_account(u["user_id"])
                                    st.warning("User permanently deleted.")
                                    st.rerun()

        with sub_tab2:
            st.subheader("Register New Employee Account")
            with st.form("create_user_form", clear_on_submit=True):
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    new_username = st.text_input("Username* (letters, numbers, underscores)").strip().lower()
                    new_fullname = st.text_input("Full Name*").strip()
                    new_password = st.text_input("Initial Password*", type="password").strip()
                with col_u2:
                    new_role = st.selectbox("System Account Role*", ["STAFF", "OPERATOR", "CA", "SUPER_ADMIN", "CEO"])
                    new_user_email = st.text_input("Email Address").strip()

                st.markdown("#### Initial Desk & Feature Permissions")
                init_perms = []
                for mod_code, mod_label in SYSTEM_MODULES:
                    if st.checkbox(mod_label, key=f"new_u_perm_{mod_code}"):
                        init_perms.append(mod_code)

                submit_user = st.form_submit_button("➕ Create Employee Account", type="primary", use_container_width=True)
                if submit_user:
                    if not new_username or not new_fullname or not new_password:
                        st.error("Username, Full Name, and Password are mandatory.")
                    else:
                        try:
                            create_user(
                                username=new_username,
                                password=new_password,
                                full_name=new_fullname,
                                account_type=new_role,
                                email=new_user_email,
                                modules=init_perms
                            )
                            st.success(f"User account @{new_username} created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating user: {str(e)}")

    # =========================================================================
    # TAB 2: VENDOR MASTER DIRECTORY
    # =========================================================================
    with tab_vendors:
        sub_v1, sub_v2 = st.tabs(["🏢 Registered Vendors", "➕ Add New Vendor"])

        with sub_v1:
            try:
                v_res = supabase.table("vendors").select("*").order("vendor_name", desc=False).execute()
                vendors = v_res.data or []
            except Exception:
                vendors = []

            if not vendors:
                st.info("No external vendors currently registered in the database.")
            else:
                for v in vendors:
                    with st.container(border=True):
                        col_v1, col_v2 = st.columns([3, 1.2])
                        with col_v1:
                            st.markdown(f"### {v.get('vendor_name')}")
                            st.caption(f"Contact Person: **{v.get('contact_person') or 'N/A'}** | Phone: `{v.get('phone') or 'N/A'}`")
                            st.write(f"**Category:** {v.get('category') or 'General Printing / Job-Work'} | **City:** {v.get('city') or 'Kolkata'}")
                        with col_v2:
                            if st.button("🗑️ Delete Vendor", key=f"del_v_{v['vendor_id']}", type="primary"):
                                try:
                                    supabase.table("vendors").delete().eq("vendor_id", v["vendor_id"]).execute()
                                    st.warning(f"Vendor '{v.get('vendor_name')}' removed.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Cannot delete vendor linked to production records: {str(e)}")

        with sub_v2:
            st.subheader("Register Outsource / Job-Work Partner")
            with st.form("add_vendor_form", clear_on_submit=True):
                col_vn1, col_vn2 = st.columns(2)
                with col_vn1:
                    v_name = st.text_input("Vendor / Company Name*").strip()
                    v_poc = st.text_input("Primary Contact Person").strip()
                    v_phone = st.text_input("Contact Phone Number").strip()
                with col_vn2:
                    v_cat = st.selectbox("Category*", ["Offset Printing", "Laser Cutting", "Acrylic Fabrication", "Neon Signage", "Binding & Finishing", "Raw Material Supplier"])
                    v_city = st.text_input("City / Location", value="Kolkata").strip()

                add_v_btn = st.form_submit_button("🏢 Save Vendor", type="primary", use_container_width=True)
                if add_v_btn:
                    if not v_name:
                        st.error("Vendor Name is mandatory.")
                    else:
                        try:
                            supabase.table("vendors").insert({
                                "vendor_name": v_name,
                                "contact_person": v_poc,
                                "phone": v_phone,
                                "category": v_cat,
                                "city": v_city,
                                "is_active": True
                            }).execute()
                            st.success(f"Vendor '{v_name}' successfully added to directory!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error registering vendor: {str(e)}")

    # =========================================================================
    # TAB 3: MASTER DROPDOWNS & ATTRIBUTES
    # =========================================================================
    with tab_masters:
        st.subheader("Manage Floor Dynamic Options")
        st.caption("Add or delete options available in workstation dropdown menus.")

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            with st.container(border=True):
                st.markdown("#### 🛠️ Vendor Job Types")
                v_jobs = get_dynamic_dropdown_options("vendor_job_types", "job_type")
                for vj in v_jobs:
                    c_txt, c_del = st.columns([3, 1])
                    c_txt.write(f"• {vj}")
                    if c_del.button("❌", key=f"del_vj_{vj}"):
                        supabase.table("vendor_job_types").delete().eq("job_type", vj).execute()
                        st.rerun()
                
                with st.form("add_vj_form", clear_on_submit=True):
                    new_vj = st.text_input("Add New Job Type").strip()
                    if st.form_submit_button("Add Job Type") and new_vj:
                        add_dynamic_option("vendor_job_types", "job_type", new_vj)
                        st.rerun()

        with col_m2:
            with st.container(border=True):
                st.markdown("#### 📜 Paper Fabrications & Finishing")
                fabs = get_dynamic_dropdown_options("paper_fabrications", "fabrication_name")
                for fb in fabs:
                    c_txt2, c_del2 = st.columns([3, 1])
                    c_txt2.write(f"• {fb}")
                    if c_del2.button("❌", key=f"del_fb_{fb}"):
                        supabase.table("paper_fabrications").delete().eq("fabrication_name", fb).execute()
                        st.rerun()
                
                with st.form("add_fb_form", clear_on_submit=True):
                    new_fb = st.text_input("Add New Finishing / Fabrication").strip()
                    if st.form_submit_button("Add Fabrication") and new_fb:
                        add_dynamic_option("paper_fabrications", "fabrication_name", new_fb)
                        st.rerun()

    # =========================================================================
    # TAB 4: SYSTEM OPERATIONS, OVERRIDES & AUDIT
    # =========================================================================
    with tab_ops:
        st.subheader("Operational Overrides & Maintenance")

        col_o1, col_o2 = st.columns(2)

        with col_o1:
            with st.container(border=True):
                st.markdown("#### 🗑️ Emergency Job Purge")
                st.caption("Completely deletes a test or corrupted job sheet along with all related child records.")
                purge_job_id = st.number_input("Enter Job ID to Purge", min_value=1, step=1, key="purge_id_input")
                confirm_purge = st.checkbox("I confirm this deletion is permanent and intentional", key="conf_purge")
                if st.button("Delete Job Sheet Permanently", type="primary", key="btn_purge_job"):
                    if confirm_purge:
                        success, msg = delete_job_sheet(purge_job_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Please confirm deletion before submitting.")

        with col_o2:
            with st.container(border=True):
                st.markdown("#### 🔄 CA Invoice Re-upload Reset")
                st.caption("Reset lockout counter for jobs that exceeded maximum CA invoice re-uploads.")
                reset_job_id = st.number_input("Enter Job ID to Reset", min_value=1, step=1, key="reset_id_input")
                if st.button("Reset Invoicing Attempts", key="btn_reset_inv"):
                    success, msg = reset_invoice_attempts(reset_job_id)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        st.markdown("---")

        st.markdown("#### 🛡️ Recent Security & Stage Audit Logs")
        try:
            logs_res = supabase.table("audit_logs").select("*").order("created_at", desc=True).limit(25).execute()
            logs = logs_res.data or []
            if logs:
                st.dataframe(logs, use_container_width=True)
            else:
                st.caption("No audit log events recorded yet.")
        except Exception:
            st.caption("Audit logs table not yet populated.")