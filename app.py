import os
import streamlit as st
import time
from database import authenticate_user, supabase, log_audit, update_user_password
from modules import (
    mod_a_sales,
    mod_b_design,
    mod_c_payment,
    mod_d_production,
    mod_e_qc,
    mod_f_dispatch,
    mod_g_billing,
    manager_view,
    ceo_admin
)

st.set_page_config(
    page_title="AdNet Commercial Print & Sign Operations",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "ceo_modal_seen" not in st.session_state:
    st.session_state.ceo_modal_seen = False


def render_ceo_briefing_dialog(user):
    """Executive Morning Briefing Modal for Admin & CEO."""
    @st.dialog("👑 Executive Morning Briefing")
    def briefing():
        st.markdown(f"### Welcome back, {user['full_name']}")
        st.caption("Floor velocity and pipeline snapshot:")

        try:
            j_res = supabase.table("jobs").select("*").execute()
            jobs = j_res.data or []
            i_res = supabase.table("job_items").select("*").execute()
            items = i_res.data or []
        except Exception:
            jobs, items = [], []

        active = [j for j in jobs if j.get("current_stage") != "SETTLED"]
        returned = [j for j in jobs if j.get("is_returned")]
        val = sum(float(i.get("amount", 0) or 0) for i in items)

        c1, c2, c3 = st.columns(3)
        c1.metric("Active Floor Orders", len(active))
        c2.metric("QC Defect / Returns", len(returned))
        c3.metric("Live Order Value", f"₹ {val:,.2f}")

        st.markdown("---")
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("📧 Email Report to CEO", use_container_width=True):
                from email_service import send_ceo_daily_report
                ok, res_msg = send_ceo_daily_report()
                if ok:
                    st.success(res_msg)
                else:
                    st.error(res_msg)
        with btn_c2:
            if st.button("Enter Management Workspace", type="primary", use_container_width=True):
                st.session_state.ceo_modal_seen = True
                st.rerun()

    briefing()


def main():
    # Login Screen
    if not st.session_state.authenticated:
        _, logo_col, _ = st.columns([1, 1.2, 1])
        with logo_col:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            candidate_paths = [
                os.path.join(base_dir, "assets", "logo.png"),
                os.path.join(base_dir, "assets", "Logo.png"),
                os.path.join(base_dir, "assets", "logo.PNG"),
                os.path.join(base_dir, "logo.png"),
            ]
            resolved_logo = next((p for p in candidate_paths if os.path.exists(p)), None)

            if resolved_logo:
                st.image(resolved_logo, use_container_width=True)
            else:
                st.markdown("<h2 style='text-align: center;'>🖨️ AdNet Operations & Floor Management</h2>", unsafe_allow_html=True)

        st.caption("<p style='text-align: center;'>Login with ID - Password</p>", unsafe_allow_html=True)

        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            with st.form("login_form"):
                username = st.text_input("Username").strip()
                password = st.text_input("Password / PIN", type="password").strip()
                submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                if submit:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        log_audit(user["user_id"], "LOGIN", f"User {username} logged into system.")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or deactivated account.")
        return

    # Logged In State
    current_user = st.session_state.user
    account_type = current_user.get("account_type", "STAFF")
    user_perms = current_user.get("permissions") or []

    # CEO/Admin Briefing Modal Trigger
    if account_type in ["SUPER_ADMIN", "CEO"] and not st.session_state.ceo_modal_seen:
        render_ceo_briefing_dialog(current_user)

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(f"### 👤 {current_user['full_name']}")
        st.caption(f"Role: `{account_type}` | `@{current_user['username']}`")
        if current_user.get("primary_station"):
            st.caption(f"Station: `{current_user['primary_station']}`")

        st.markdown("---")
        st.markdown("### 📂 Workspaces")

        menu_options = {}

        # Executive Desks
        if account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["👑 Executive Floor KPI Overview"] = ceo_admin.render_overview
            menu_options["👥 Staff & RBAC Admin"] = ceo_admin.render_user_management

        # Manager Track & Audit
        if account_type in ["MANAGER", "SUPER_ADMIN", "CEO"]:
            menu_options["🔍 Manager Track & Audit"] = manager_view.render

        # Workstation Modules
        if "MOD_A" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["📝 1. Order Intake (Sales)"] = mod_a_sales.render

        if "MOD_B" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["🎨 2. Design & Proofs"] = mod_b_design.render

        if "MOD_C" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["💳 3. Advance / Accounts Clearance"] = mod_c_payment.render

        if "MOD_D" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["⚙️ 4. Production Floor"] = mod_d_production.render

        if "MOD_E" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["🔍 5. Quality Check (QC)"] = mod_e_qc.render

        if "MOD_F" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["🚚 6. Dispatch & Field Delivery"] = mod_f_dispatch.render

        if "MOD_G" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_options["🧾 7. Billing & Invoicing Desk"] = mod_g_billing.render

        if not menu_options:
            st.warning("No active module permissions assigned. Please contact the administrator.")
            selected_desk = None
        else:
            selected_desk = st.radio("Navigate Station", list(menu_options.keys()))

        st.markdown("---")
        with st.popover("🔑 Change Password", use_container_width=True):
            st.markdown("#### Update Password / PIN")
            old_p = st.text_input("Current Password *", type="password", key="chg_old_pwd").strip()
            new_p = st.text_input("New Password *", type="password", key="chg_new_pwd").strip()
            conf_p = st.text_input("Confirm New Password *", type="password", key="chg_conf_pwd").strip()

            if st.button("Update Password", type="primary", use_container_width=True, key="btn_update_pwd"):
                if not (old_p and new_p and conf_p):
                    st.error("Please fill in all password fields.")
                elif new_p != conf_p:
                    st.error("New password and confirmation do not match.")
                elif len(new_p) < 4:
                    st.error("Password must be at least 4 characters long.")
                else:
                    ok, msg = update_user_password(current_user["user_id"], old_p, new_p)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.ceo_modal_seen = False
            st.rerun()

    # Render Screen
    if selected_desk:
        menu_options[selected_desk](current_user)


if __name__ == "__main__":
    main()