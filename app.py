import os
import streamlit as st
import time
from database import (
    authenticate_user, 
    supabase, 
    log_audit, 
    update_user_password,
    get_station_pending_counts
)
from modules import (
    mod_a_sales,
    mod_b_design,
    mod_c_payment,
    mod_d_production,
    mod_e_qc,
    mod_f_dispatch,
    mod_g_billing,
    manager_view,
    ceo_admin,
    vendor_dashboard,
    customer_dashboard
)

st.set_page_config(
    page_title="AdNet Operations",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None


def inject_custom_css():
    """Injects sleek navigation and badge styling."""
    st.markdown("""
        <style>
        @keyframes blinker {
            50% { opacity: 0.2; }
        }
        .badge-new {
            background-color: #E10600;
            color: #FFFFFF !important;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            animation: blinker 1s linear infinite;
            margin-left: 6px;
            display: inline-block;
        }
        .badge-count {
            background-color: rgba(255, 255, 255, 0.08);
            color: #38BDF8 !important;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 10px;
            margin-left: 6px;
            display: inline-block;
        }
        div[data-testid="stRadio"] > div {
            gap: 4px;
        }
        div[data-testid="stRadio"] label {
            padding: 5px 8px;
            border-radius: 6px;
        }
        </style>
    """, unsafe_allow_html=True)


def main():
    inject_custom_css()

    # --- LOGIN SCREEN ---
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

    # --- AUTHENTICATED SESSION ---
    current_user = st.session_state.user
    account_type = current_user.get("account_type", "STAFF")
    user_perms = current_user.get("permissions") or []

    # Pull real-time queue counts
    p_counts = get_station_pending_counts()

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(f"### 👤 {current_user['full_name']}")
        st.caption(f"Role: `{account_type}` | `@{current_user['username']}`")
        if current_user.get("primary_station"):
            st.caption(f"Station: `{current_user['primary_station']}`")

        st.markdown("---")

        # --- BUTTON: MAIL TODAY'S JOBSHEET ---
        if st.button("📧 Mail Today's Jobsheet", use_container_width=True, type="secondary"):
            with st.spinner("Compiling and sending today's jobsheets..."):
                try:
                    from email_service import send_daily_jobsheet_digest
                    recipient = current_user.get("email")
                    ok, res_msg = send_daily_jobsheet_digest(recipient_email=recipient)
                    if ok:
                        st.toast(f"✅ {res_msg}", icon="📧")
                    else:
                        st.warning(res_msg)
                except Exception as ex:
                    st.error(f"Failed to send email: {ex}")

        st.markdown("### 📂 Workspaces")

        menu_config = []

        # Label helper defined before any usage
        def make_station_label(title: str, count: int = 0) -> str:
            if count > 0:
                return f"{title}  ({count})  ●"
            return title

        # Executive Desks
        if account_type in ["SUPER_ADMIN", "CEO"]:
            del_count = p_counts.get("DELETION_REQS", 0)
            lbl_exec = make_station_label("👑 Executive Floor KPI Overview", del_count)
            menu_config.append(("EXEC_OVERVIEW", lbl_exec, ceo_admin.render_overview))
            menu_config.append(("EXEC_RBAC", "👥 Staff & RBAC Admin", ceo_admin.render_user_management))
            menu_config.append(("VENDORS", "🏢 Vendor Directory", vendor_dashboard.render))
            menu_config.append(("CUSTOMERS", "👥 Customer Directory", customer_dashboard.render))

        # Manager Track & Audit
        if account_type in ["MANAGER", "SUPER_ADMIN", "CEO"]:
            menu_config.append(("MGR_TRACK", "🔍 Manager Track & Audit", manager_view.render))

        # Workstation Modules with Pending Counters
        if "MOD_A" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_config.append(("MOD_A", "📝 1. Order Intake (Sales)", mod_a_sales.render))

        if "MOD_B" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c_b = p_counts.get("DESIGN", 0)
            menu_config.append(("MOD_B", make_station_label("🎨 2. Design & Proofs", c_b), mod_b_design.render))

        if "MOD_C" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c_c = p_counts.get("PAYMENT", 0)
            menu_config.append(("MOD_C", make_station_label("💳 3. Advance / Accounts Clearance", c_c), mod_c_payment.render))

        if "MOD_D" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c_d = p_counts.get("PRODUCTION", 0)
            menu_config.append(("MOD_D", make_station_label("⚙️ 4. Production Floor", c_d), mod_d_production.render))

        if "MOD_E" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c_e = p_counts.get("QC", 0)
            menu_config.append(("MOD_E", make_station_label("🔍 5. Quality Check (QC)", c_e), mod_e_qc.render))

        if "MOD_F" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c_f = p_counts.get("DISPATCH", 0)
            menu_config.append(("MOD_F", make_station_label("🚚 6. Dispatch & Field Delivery", c_f), mod_f_dispatch.render))

        if "MOD_G" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c_g = p_counts.get("BILLING", 0)
            menu_config.append(("MOD_G", make_station_label("🧾 7. Billing & Invoicing Desk", c_g), mod_g_billing.render))

        if not menu_config:
            st.warning("No active module permissions assigned. Please contact the administrator.")
            selected_key = None
        else:
            keys = [item[0] for item in menu_config]
            labels_map = {item[0]: item[1] for item in menu_config}
            handlers_map = {item[0]: item[2] for item in menu_config}

            selected_key = st.radio(
                "Navigate Station",
                options=keys,
                format_func=lambda k: labels_map[k],
                label_visibility="collapsed"
            )

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
            st.rerun()

    # Render Screen
    if selected_key and selected_key in handlers_map:
        handlers_map[selected_key](current_user)


if __name__ == "__main__":
    main()