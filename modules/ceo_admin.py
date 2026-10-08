import streamlit as st
from database import (
    supabase, 
    get_all_users, 
    create_user, 
    update_user_status, 
    update_user_permissions,
    delete_user,
    extend_job_deadline, 
    delete_job_sheet,
    get_all_vendors,
    create_vendor,
    update_vendor_status,
    delete_vendor,
    reject_job_deletion_request
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

    # --- PENDING DELETION REQUESTS FOR CEO / ADMIN ---
    del_requested_jobs = [
        j for j in all_jobs 
        if (j.get("return_reason") or "").startswith("[DELETION_REQ]")
    ]

    if del_requested_jobs:
        st.markdown("---")
        st.error(f"🚨 **{len(del_requested_jobs)} Jobsheet Deletion Request(s) Pending Approval**")
        for dj in del_requested_jobs:
            with st.container(border=True):
                dc1, dc2, dc3 = st.columns([3, 2, 2])
                with dc1:
                    st.markdown(f"**Job #{dj.get('job_no')} — {dj.get('client_name')}**")
                    clean_reason = dj.get("return_reason", "").replace("[DELETION_REQ]", "").strip()
                    st.caption(f"📝 {clean_reason}")
                with dc2:
                    st.caption(f"Stage: `{dj.get('current_stage')}` | Due: `{dj.get('due_date')}`")
                    st.caption(f"Booked by: `{dj.get('order_taken_by', 'N/A')}`")
                with dc3:
                    btn_a, btn_r = st.columns(2)
                    with btn_a:
                        if st.button("🗑️ Approve & Delete", key=f"appr_del_{dj['job_id']}", type="primary", use_container_width=True):
                            delete_job_sheet(dj["job_id"])
                            st.success(f"Job #{dj.get('job_no')} deleted permanently.")
                            st.rerun()
                    with btn_r:
                        if st.button("❌ Reject", key=f"rej_del_{dj['job_id']}", use_container_width=True):
                            reject_job_deletion_request(dj["job_id"])
                            st.info(f"Deletion request rejected for Job #{dj.get('job_no')}.")
                            st.rerun()

    st.markdown("---")
    st.markdown("#### 🛠️ Active Jobs Management & Deadline Extensions")

    if not active_jobs:
        st.info("No active jobs requiring administrative management.")
        return

    for job in active_jobs:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                st.markdown(f"**Job #{job.get('job_no')} - {job.get('client_name')}**")
                st.caption(f"Stage: `{job.get('current_stage')}` | Due: `{job.get('due_date')}`")
            with c2:
                with st.popover("📅 Extend Target Delivery Date"):
                    new_due = st.date_input("New Target Date", key=f"due_{job['job_id']}")
                    ext_reason = st.text_input("Extension Reason", key=f"ext_{job['job_id']}")
                    if st.button("Save New Date", key=f"btn_due_{job['job_id']}", type="primary"):
                        extend_job_deadline(job["job_id"], user["user_id"], new_due, ext_reason)
                        st.success("Target delivery date updated.")
                        st.rerun()
            with c3:
                if user.get("account_type") in ["SUPER_ADMIN", "CEO"]:
                    with st.popover("🗑️ Cascading Delete"):
                        st.warning("Permanently delete this entire jobsheet and all child records?")
                        if st.button("Confirm Delete", key=f"del_{job['job_id']}", type="primary"):
                            delete_job_sheet(job["job_id"])
                            st.success("Jobsheet deleted.")
                            st.rerun()


def render_user_management(user):
    st.subheader("👥 Staff & RBAC Administration")
    st.caption("Manage employee identities, workstation permissions, floor stations, and access status.")

    tab_users, tab_add, tab_vendors = st.tabs(["Active Staff Directory", "Add New Staff Member", "Vendor Lists"])

    # --- TAB 1: ACTIVE STAFF DIRECTORY ---
    with tab_users:
        users = get_all_users()
        current_account_type = user.get("account_type")

        display_users = [
            u for u in users 
            if not (current_account_type == "CEO" and u.get("username") == "admin")
        ]

        if not display_users:
            st.info("No staff members found.")
        else:
            for u in display_users:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 2, 1.5])
                    with c1:
                        emp_badge = f"`[{u.get('emp_code')}]` " if u.get("emp_code") else ""
                        st.markdown(f"### {emp_badge}{u.get('full_name')}")
                        st.caption(f"👤 Username: `@{u.get('username')}` | 📱 Mobile: `{u.get('phone', 'N/A')}`")
                        if u.get("email"):
                            st.caption(f"✉️ Email: `{u.get('email')}`")
                        st.caption(f"Role: `{u.get('account_type')}` | Last Login: `{u.get('last_login', 'Never')}`")
                    
                    with c2:
                        st.markdown(f"**Primary Station:** `{u.get('primary_station', 'Unassigned')}`")
                        vendor_badge = "✅ Allowed" if u.get("can_manage_vendors") else "❌ No Access"
                        st.markdown(f"**Manage Vendors:** {vendor_badge}")
                        st.write(f"**Allowed Modules:** {', '.join(u.get('permissions', []) or ['None'])}")

                    with c3:
                        if u.get("username") == "admin":
                            st.info("System Root Account")
                        else:
                            is_active = u.get("is_active", True)
                            status_label = "🟢 Active" if is_active else "🔴 Inactive"
                            st.markdown(f"**Status:** {status_label}")

                            with st.popover("✏️ Edit Role & Modules", use_container_width=True):
                                st.markdown(f"**Modify Access for @{u.get('username')}**")
                                
                                cur_perms = u.get("permissions") or []
                                cur_station = u.get("primary_station") or ""
                                cur_role = u.get("account_type", "STAFF")
                                
                                edit_station = st.text_input("Primary Station", value=cur_station, key=f"e_st_{u['user_id']}")
                                edit_can_vendor = st.checkbox("Can Manage / Assign Vendors?", value=bool(u.get("can_manage_vendors")), key=f"e_v_{u['user_id']}")
                                
                                st.markdown("##### Assigned Workstations & Permissions")
                                e_mod_a = st.checkbox("📝 Sales & Intake (Module 1)", value=("MOD_A" in cur_perms), key=f"e_ma_{u['user_id']}")
                                e_can_edit = st.checkbox("✏️ Allow Editing Existing Jobsheets", value=("CAN_EDIT_JOBS" in cur_perms), key=f"e_cej_{u['user_id']}")
                                e_mod_b = st.checkbox("🎨 Design / Pre-Press (Module 2)", value=("MOD_B" in cur_perms), key=f"e_mb_{u['user_id']}")
                                e_mod_c = st.checkbox("💳 Accounts & Advance (Module 3)", value=("MOD_C" in cur_perms), key=f"e_mc_{u['user_id']}")
                                e_mod_d = st.checkbox("⚙️ Production Floor (Module 4)", value=("MOD_D" in cur_perms), key=f"e_md_{u['user_id']}")
                                e_mod_e = st.checkbox("🔍 Quality Check - QC (Module 5)", value=("MOD_E" in cur_perms), key=f"e_me_{u['user_id']}")
                                e_mod_f = st.checkbox("🚚 Dispatch & Delivery (Module 6)", value=("MOD_F" in cur_perms), key=f"e_mf_{u['user_id']}")
                                e_mod_g = st.checkbox("🧾 Billing & Settlement (Module 7)", value=("MOD_G" in cur_perms), key=f"e_mg_{u['user_id']}")
                                
                                st.markdown("##### Role Elevation")
                                e_is_manager = st.checkbox("👔 Floor Manager Role", value=(cur_role == "MANAGER"), key=f"e_mgr_{u['user_id']}")
                                e_is_admin = st.checkbox("👑 Executive Access", value=(cur_role in ["SUPER_ADMIN", "CEO"]), key=f"e_adm_{u['user_id']}")

                                if st.button("Save Changes", key=f"btn_save_u_{u['user_id']}", type="primary", use_container_width=True):
                                    new_perms = []
                                    if e_mod_a: new_perms.append("MOD_A")
                                    if e_can_edit: new_perms.append("CAN_EDIT_JOBS")
                                    if e_mod_b: new_perms.append("MOD_B")
                                    if e_mod_c: new_perms.append("MOD_C")
                                    if e_mod_d: new_perms.append("MOD_D")
                                    if e_mod_e: new_perms.append("MOD_E")
                                    if e_mod_f: new_perms.append("MOD_F")
                                    if e_mod_g: new_perms.append("MOD_G")

                                    if e_is_admin:
                                        target_role = "SUPER_ADMIN" if user.get("account_type") == "SUPER_ADMIN" else "CEO"
                                    elif e_is_manager:
                                        target_role = "MANAGER"
                                    else:
                                        target_role = "STAFF"

                                    ok, msg = update_user_permissions(
                                        user_id=u["user_id"],
                                        account_type=target_role,
                                        permissions=new_perms,
                                        can_manage_vendors=edit_can_vendor,
                                        primary_station=edit_station
                                    )
                                    if ok:
                                        st.success("Updated successfully.")
                                        st.rerun()
                                    else:
                                        st.error(f"Update failed: {msg}")

                            btn_txt = "Deactivate" if is_active else "Reactivate"
                            if st.button(btn_txt, key=f"usr_st_{u['user_id']}", use_container_width=True):
                                update_user_status(u["user_id"], not is_active)
                                st.rerun()

                            with st.popover("🗑️ Delete User"):
                                st.warning(f"Permanently remove @{u.get('username')}?")
                                if st.button("Confirm Delete", key=f"del_u_{u['user_id']}", type="primary", use_container_width=True):
                                    delete_user(u["user_id"])
                                    st.success(f"User @{u.get('username')} deleted.")
                                    st.rerun()

    # --- TAB 2: ADD NEW STAFF MEMBER ---
    with tab_add:
        with st.form("add_user_form", clear_on_submit=True):
            st.markdown("#### 1. Basic Identity")
            i1, i2, i3 = st.columns(3)
            with i1:
                new_name = st.text_input("Full Name *", placeholder="e.g. Rahul Sharma").strip()
            with i2:
                new_phone = st.text_input("Mobile / Phone Number *", placeholder="e.g. 9830112233").strip()
            with i3:
                new_email = st.text_input("Email Address (Optional)", placeholder="e.g. rahul@adnet.com").strip()

            st.markdown("#### 2. Login & Security")
            l1, l2, l3 = st.columns(3)
            with l1:
                emp_code = st.text_input("Employee Code / ID *", placeholder="e.g. EMP-104").strip()
            with l2:
                new_username = st.text_input("Username *", placeholder="e.g. rahul104").strip()
            with l3:
                new_password = st.text_input("Temporary Password / PIN *", type="password", placeholder="Initial Password").strip()

            st.markdown("#### 3. Floor Assignment & Vendor Authority")
            f1, f2 = st.columns([2, 1])
            with f1:
                station = st.text_input("Primary Station / Department", placeholder="e.g. Solvent Machine 1, Flatbed Laser, Dispatch Godown").strip()
            with f2:
                st.markdown("<br>", unsafe_allow_html=True)
                can_manage_vendors = st.checkbox("Can Manage / Assign Vendors?", help="Check if this employee can outsource work.")

            st.markdown("#### 4. Assigned Workstation Desks (Checklist)")
            r1, r2 = st.columns(2)
            with r1:
                mod_a = st.checkbox("📝 Sales & Intake (Module 1)")
                can_edit_jobs = st.checkbox("✏️ Allow Editing Existing Jobsheets", help="Allows modifying existing jobsheet info and pricing.")
                mod_b = st.checkbox("🎨 Design / Pre-Press (Module 2)")
                mod_c = st.checkbox("💳 Accounts & Advance Clearance (Module 3)")
                mod_d = st.checkbox("⚙️ Production Floor / Machine Operator (Module 4)", value=True)

            with r2:
                mod_e = st.checkbox("🔍 Quality Check - QC (Module 5)")
                mod_f = st.checkbox("🚚 Dispatch & Field Delivery (Module 6)")
                mod_g = st.checkbox("🧾 Billing & Settlement (Module 7)")

            st.markdown("---")
            is_manager_role = st.checkbox("👔 Floor Manager Role (Full floor tracking visibility)")
            is_management = st.checkbox("👑 Executive / Management Level Access (Admin)")

            submit = st.form_submit_button("Create Employee Profile", type="primary", use_container_width=True)

            if submit:
                if not (new_name and new_phone and emp_code and new_username and new_password):
                    st.error("Please fill in all mandatory fields.")
                else:
                    permissions = []
                    if mod_a: permissions.append("MOD_A")
                    if can_edit_jobs: permissions.append("CAN_EDIT_JOBS")
                    if mod_b: permissions.append("MOD_B")
                    if mod_c: permissions.append("MOD_C")
                    if mod_d: permissions.append("MOD_D")
                    if mod_e: permissions.append("MOD_E")
                    if mod_f: permissions.append("MOD_F")
                    if mod_g: permissions.append("MOD_G")

                    if is_management:
                        account_type = "SUPER_ADMIN" if user.get("account_type") == "SUPER_ADMIN" else "CEO"
                    elif is_manager_role:
                        account_type = "MANAGER"
                    else:
                        account_type = "STAFF"

                    success, res = create_user(
                        username=new_username,
                        password=new_password,
                        full_name=new_name,
                        account_type=account_type,
                        permissions=permissions,
                        emp_code=emp_code,
                        phone=new_phone,
                        email=new_email,
                        primary_station=station,
                        can_manage_vendors=can_manage_vendors
                    )

                    if success:
                        st.success(f"Employee {new_name} [{emp_code}] created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to create employee: {res}")

    # --- TAB 3: VENDOR LISTS ---
    with tab_vendors:
        st.markdown("### 🏢 Vendor Master Directory")
        st.caption("Manage outsourced production vendors, contact details, and active status.")

        with st.expander("➕ Add New Vendor", expanded=False):
            with st.form("add_vendor_form", clear_on_submit=True):
                v_col1, v_col2 = st.columns(2)
                with v_col1:
                    v_name = st.text_input("Vendor / Company Name *", placeholder="e.g. Balaji Offset Printers").strip()
                    v_contact = st.text_input("Contact Person", placeholder="e.g. Ramesh Agarwal").strip()
                    v_phone = st.text_input("Phone / Mobile Number", placeholder="e.g. 9830112233").strip()
                with v_col2:
                    v_category = st.text_input("Specialization / Category", placeholder="e.g. Offset Commercial, Laser Cutting").strip()
                    v_city = st.text_input("City", value="Kolkata").strip()

                if st.form_submit_button("Add Vendor to Directory", type="primary", use_container_width=True):
                    if not v_name:
                        st.error("Vendor Name is mandatory.")
                    else:
                        ok, msg = create_vendor(v_name, v_contact, v_phone, v_category, v_city)
                        if ok:
                            st.success(f"Vendor '{v_name}' added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add vendor: {msg}")

        st.markdown("---")

        vendors = get_all_vendors()
        if not vendors:
            st.info("No vendors registered in the directory.")
        else:
            for v in vendors:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 2, 1.5])
                    with c1:
                        st.markdown(f"### 🏭 {v.get('vendor_name')}")
                        st.caption(f"👤 Contact Person: `{v.get('contact_person') or 'N/A'}` | 📱 Phone: `{v.get('phone') or 'N/A'}`")
                    with c2:
                        st.markdown(f"**Specialization:** `{v.get('category') or 'General Job-Work'}`")
                        st.caption(f"📍 City: `{v.get('city') or 'Kolkata'}`")
                    with c3:
                        is_active = v.get("is_active", True)
                        status_label = "🟢 Active" if is_active else "🔴 Inactive"
                        st.markdown(f"**Status:** {status_label}")

                        btn_txt = "Deactivate" if is_active else "Reactivate"
                        if st.button(btn_txt, key=f"vnd_st_{v['vendor_id']}", use_container_width=True):
                            update_vendor_status(v["vendor_id"], not is_active)
                            st.rerun()

                        with st.popover("🗑️ Delete Vendor"):
                            st.warning(f"Permanently delete '{v.get('vendor_name')}'?")
                            if st.button("Confirm Delete", key=f"del_v_{v['vendor_id']}", type="primary", use_container_width=True):
                                delete_vendor(v["vendor_id"])
                                st.success(f"Vendor '{v.get('vendor_name')}' deleted.")
                                st.rerun()