import os
import base64
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
    mod_ca_audit,
    manager_view,
    customer_dashboard,
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


def get_image_base64(image_path: str) -> str:
    """Helper to load a local image and return base64 string for CSS embedding."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""


def inject_custom_css():
    """Injects CSS for badges and sidebar elements."""
    st.markdown("""
        <style>
        /* Blinking Animation */
        @keyframes blinker {
            50% { opacity: 0.15; }
        }
        .badge-new {
            background-color: #ff2b2b;
            color: #ffffff !important;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            letter-spacing: 0.5px;
            animation: blinker 1s linear infinite;
            margin-left: 6px;
            vertical-align: middle;
            display: inline-block;
        }
        .badge-count {
            background-color: #1f2937;
            color: #38bdf8 !important;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 12px;
            border: 1px solid #38bdf8;
            margin-left: 6px;
            vertical-align: middle;
            display: inline-block;
        }
        div[data-testid="stRadio"] label p {
            display: inline !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_login_screen():
    """Renders the custom split-card AdNet login screen."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_logos = [
        os.path.join(base_dir, "assets", "logo.png"),
        os.path.join(base_dir, "assets", "Logo.png"),
        os.path.join(base_dir, "assets", "logo.PNG"),
        os.path.join(base_dir, "logo.png"),
    ]
    resolved_logo = next((p for p in candidate_logos if os.path.exists(p)), None)
    banner_path = os.path.join(base_dir, "assets", "login_banner.png")

    logo_b64 = get_image_base64(resolved_logo) if resolved_logo else ""
    banner_b64 = get_image_base64(banner_path)

    st.markdown(f"""
        <style>
        /* Global Page Background */
        .stApp {{
            background: linear-gradient(135deg, #f5f6f8 0%, #ebeef2 100%) !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        /* Login Outer Container */
        .login-wrapper {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px 0;
        }}

        .login-card {{
            display: flex;
            width: 960px;
            min-height: 540px;
            background: #ffffff;
            border-radius: 26px;
            border: 2px solid #e11d48;
            box-shadow: 0 16px 40px rgba(225, 29, 72, 0.2), 0 2px 10px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }}

        /* Left Side (Form Area) */
        .login-left {{
            flex: 1.4;
            padding: 40px 48px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .card-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}

        .card-topbar-links {{
            display: flex;
            gap: 20px;
            align-items: center;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}

        .card-topbar-links span.active-tab {{
            color: #e11d48;
            border-bottom: 2px solid #e11d48;
            padding-bottom: 2px;
        }}

        .login-title {{
            color: #e11d48;
            font-size: 32px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 20px;
        }}

        /* Streamlit Input Styling */
        div[data-testid="stForm"] {{
            border: none !important;
            padding: 0 !important;
        }}

        div[data-testid="stTextInput"] input {{
            border-radius: 22px !important;
            background-color: #f1f3f5 !important;
            border: 1px solid #d1d5db !important;
            color: #1f2937 !important;
            padding: 10px 18px !important;
            font-size: 14px !important;
        }}

        div[data-testid="stTextInput"] input:focus {{
            border: 1.5px solid #e11d48 !important;
            box-shadow: 0 0 0 1px #e11d48 !important;
            background-color: #ffffff !important;
        }}

        /* Red Pill Submit Button */
        div[data-testid="stFormSubmitButton"] > button {{
            background-color: #e11d48 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 22px !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            padding: 10px 0 !important;
            box-shadow: 0 4px 14px rgba(225, 29, 72, 0.35) !important;
            width: 100% !important;
            margin-top: 10px !important;
        }}

        div[data-testid="stFormSubmitButton"] > button:hover {{
            background-color: #be123c !important;
            box-shadow: 0 6px 18px rgba(225, 29, 72, 0.45) !important;
        }}

        /* Right Side (Red Graphic Banner) */
        .login-right {{
            flex: 1;
            background: linear-gradient(135deg, #a70000 0%, #670000 100%);
            {"background-image: url('data:image/png;base64," + banner_b64 + "'); background-size: cover; background-position: center;" if banner_b64 else ""}
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        </style>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([0.2, 3.6, 0.2])

    with center_col:
        st.markdown(f"""
            <div class="login-wrapper">
                <div class="login-card">
                    <div class="login-left">
                        <div class="card-topbar">
                            {"<img src='data:image/png;base64," + logo_b64 + "' style='height:36px; object-fit:contain;' />" if logo_b64 else "<h4 style='color:#e11d48; margin:0;'>Ad Net</h4>"}
                            <div class="card-topbar-links">
                                <span style="color:#6b7280;">CONTACT</span>
                                <span class="active-tab">LOG IN</span>
                            </div>
                        </div>
                        <div class="login-title">Log in</div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="👤 Username", label_visibility="collapsed").strip()
            password = st.text_input("Password", placeholder="🔒 Password", type="password", label_visibility="collapsed").strip()

            c_sub1, c_sub2 = st.columns([1, 1])
            with c_sub1:
                st.checkbox("Remember Me", value=False)
            with c_sub2:
                st.markdown("<p style='text-align: right; font-size: 13px; color: #6b7280; font-style: italic; margin-top: 4px;'>Forgot Password?</p>", unsafe_allow_html=True)

            submit = st.form_submit_button("Log in", type="primary", use_container_width=True)

            if submit:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    log_audit(user["user_id"], "LOGIN", f"User {username} logged into system.")
                    st.rerun()
                else:
                    st.error("Invalid credentials or deactivated account.")

        st.markdown("""
                    </div>
                    <div class="login-right">
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)


def main():
    inject_custom_css()

    # Login Screen
    if not st.session_state.authenticated:
        render_login_screen()
        return

    # Logged In State
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

        # --- BUTTON: MAIL TODAY'S JOBSHEET (ABOVE WORKSPACES) ---
        with st.popover("📧 Mail Today's Jobsheet", use_container_width=True):
            st.markdown("##### 📨 Send Digest")
            target_recipient = st.text_input(
                "Recipient Address",
                value="khalikhussain80@gmail.com",
                placeholder="Enter email address"
            ).strip()

            if st.button("Send Email", type="primary", use_container_width=True):
                with st.spinner("Connecting to SMTP server and dispatching..."):
                    try:
                        from email_service import send_daily_jobsheet_digest
                        ok, res_msg = send_daily_jobsheet_digest(recipient_email=target_recipient)
                        if ok:
                            st.success(res_msg)
                        else:
                            st.error(res_msg)
                    except Exception as ex:
                        st.error(f"Error: {ex}")

        st.markdown("### 📂 Workspaces")

        menu_config = []

        # Helper to construct label with badge count and blinking NEW tag
        def make_station_label(title, count=0):
            if count > 0:
                return f"{title} [{count}] 🔥NEW"
            return title

        # Executive Desks
        if account_type in ["SUPER_ADMIN", "CEO"]:
            del_count = p_counts.get("DELETION_REQS", 0)
            lbl_exec = make_station_label("👑 Executive Floor KPI Overview", del_count)
            menu_config.append(("EXEC_OVERVIEW", lbl_exec, ceo_admin.render_overview))
            menu_config.append(("EXEC_RBAC", "👥 Staff & RBAC Admin", ceo_admin.render_user_management))

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

        # --- MODULE 8: CA & GST AUDIT DESK ---
        if "MOD_CA" in user_perms or account_type in ["SUPER_ADMIN", "CEO", "MANAGER", "STAFF"]:
            menu_config.append(("CA_AUDIT", "🏛️ 8. CA & GST Audit Desk", mod_ca_audit.render))

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
                format_func=lambda k: labels_map[k]
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

    # Render Active Station Screen
    if selected_key and selected_key in handlers_map:
        handlers_map[selected_key](current_user)


if __name__ == "__main__":
    main()