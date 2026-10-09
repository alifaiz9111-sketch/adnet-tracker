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
    page_title="AdNet Operations ERP",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_customer" not in st.session_state:
    st.session_state.selected_customer = None
if "selected_vendor" not in st.session_state:
    st.session_state.selected_vendor = None


def inject_preadmin_dark_css():
    """Applies Preadmin deep-navy sidebar styling with brand red accents."""
    st.markdown("""
        <style>
        /* Overall Sidebar Background */
        section[data-testid="stSidebar"] {
            background-color: #0B0F19 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
            padding-top: 1rem !important;
        }

        /* Top Brand Logo & Title */
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 10px 18px 10px;
        }
        .sidebar-brand-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #E11D48 0%, #BE123C 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(225, 29, 72, 0.4);
        }
        .sidebar-brand-text {
            font-size: 20px;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -0.5px;
        }

        /* Category / Section Headers */
        .nav-category {
            font-size: 11px;
            font-weight: 700;
            color: #4B5563;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin: 18px 0 6px 12px;
        }

        /* Sidebar Navigation Radio Buttons */
        div[data-testid="stRadio"] {
            background: transparent !important;
        }
        div[data-testid="stRadio"] > div {
            gap: 3px !important;
        }

        /* Hide Native Radio Circle */
        div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        /* Default Inactive Nav Item */
        div[data-testid="stRadio"] label {
            background-color: transparent !important;
            padding: 10px 14px !important;
            border-radius: 8px !important;
            margin: 0 !important;
            cursor: pointer !important;
            transition: all 0.18s ease-in-out !important;
            border: none !important;
        }
        div[data-testid="stRadio"] label p {
            color: #9CA3AF !important;
            font-size: 13.5px !important;
            font-weight: 500 !important;
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            width: 100% !important;
        }

        /* Hover State */
        div[data-testid="stRadio"] label:hover {
            background-color: rgba(255, 255, 255, 0.05) !important;
        }
        div[data-testid="stRadio"] label:hover p {
            color: #FFFFFF !important;
        }

        /* BRAND RED ACTIVE SELECTED PILL */
        div[data-testid="stRadio"] label:has(input:checked),
        div[data-testid="stRadio"] label[data-checked="true"] {
            background-color: #E11D48 !important;
            box-shadow: 0 4px 14px rgba(225, 29, 72, 0.35) !important;
        }
        div[data-testid="stRadio"] label:has(input:checked) p,
        div[data-testid="stRadio"] label[data-checked="true"] p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }

        /* Action Buttons */
        .sidebar-action-btn button {
            background-color: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #D1D5DB !important;
            font-size: 12px !important;
            border-radius: 8px !important;
            margin-top: 4px;
        }
        .sidebar-action-btn button:hover {
            background-color: rgba(225, 29, 72, 0.15) !important;
            border-color: #E11D48 !important;
            color: #FFFFFF !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_signin_window():
    """Centered floating card login screen matching JIDOX design reference."""
    st.markdown("""
        <style>
        /* Hide sidebar on login screen */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        /* Style the card container */
        div[data-testid="stForm"] {
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 12px !important;
            background-color: #161B22 !important;
            padding: 34px 26px !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6) !important;
        }
        /* Custom Diamond Icon */
        .login-brand-box {
            text-align: center;
            margin-bottom: 20px;
        }
        .login-diamond {
            width: 18px;
            height: 18px;
            background: #E11D48;
            transform: rotate(45deg);
            border-radius: 3px;
            display: inline-block;
            margin-right: 8px;
            vertical-align: middle;
        }
        .login-brand-title {
            font-size: 22px;
            font-weight: 800;
            color: #FFFFFF !important;
            display: inline-block;
            vertical-align: middle;
            letter-spacing: 0.5px;
        }
        .login-subtext {
            font-size: 13px;
            color: #8B949E !important;
            margin-top: 6px;
            line-height: 1.4;
        }
        /* Submit button: Brand Red */
        div[data-testid="stForm"] button[kind="primary"] {
            background-color: #E11D48 !important;
            border: none !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            padding: 10px 0 !important;
            border-radius: 6px !important;
            margin-top: 10px !important;
        }
        div[data-testid="stForm"] button[kind="primary"]:hover {
            background-color: #BE123C !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_card, _ = st.columns([1, 1.2, 1])

    with col_card:
        with st.form("login_form"):
            st.markdown("""
                <div class="login-brand-box">
                    <div>
                        <span class="login-diamond"></span>
                        <span class="login-brand-title">ADNET ERP</span>
                    </div>
                    <div style="font-size: 18px; font-weight: 700; color: #FFFFFF; margin-top: 12px;">Sign In</div>
                    <div class="login-subtext">
                        Enter your credentials to access the floor management system.
                    </div>
                </div>
            """, unsafe_allow_html=True)

            username = st.text_input("Username / Staff ID", placeholder="e.g. admin").strip()
            password = st.text_input("Password / PIN", placeholder="••••••••", type="password").strip()

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submit:
                if not (username and password):
                    st.error("Please provide both username and password.")
                else:
                    user = authenticate_user(username, password)[cite: 16]
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        log_audit(user["user_id"], "LOGIN", f"User {username} logged into system.")[cite: 16]
                        st.rerun()
                    else:
                        st.error("Invalid credentials or deactivated account.")

        st.markdown("""
            <div style="text-align: center; font-size: 12px; color: #8B949E; margin-top: 16px;">
                Need workstation access? Contact Administrator<br>
                <span style="font-size: 11px; color: #4B5563;">2026 © AdNet Operations Systems</span>
            </div>
        """, unsafe_allow_html=True)


def main():
    inject_preadmin_dark_css()

    # --- RENDER SIGN-IN WINDOW IF NOT AUTHENTICATED ---
    if not st.session_state.authenticated:
        render_signin_window()
        return

    # --- LOGGED IN STATE ---
    current_user = st.session_state.user
    account_type = current_user.get("account_type", "STAFF")[cite: 20]
    user_perms = current_user.get("permissions") or [][cite: 20]

    p_counts = get_station_pending_counts()[cite: 20]

    # --- SIDEBAR (PREADMIN DARK STYLE) ---
    with st.sidebar:
        # 1. Top Brand Icon & Title
        st.markdown("""
            <div class="sidebar-brand">
                <div class="sidebar-brand-icon">A</div>
                <div class="sidebar-brand-text">AdNet ERP</div>
            </div>
        """, unsafe_allow_html=True)

        # 2. Email Digest Trigger Button
        st.markdown('<div class="sidebar-action-btn">', unsafe_allow_html=True)
        if st.button("✉️ Mail Today's Jobsheet", use_container_width=True):
            with st.spinner("Dispatching summary..."):
                try:
                    from email_service import send_daily_jobsheet_digest
                    recipient = current_user.get("email")[cite: 20]
                    ok, res_msg = send_daily_jobsheet_digest(recipient_email=recipient)[cite: 20]
                    if ok:
                        st.toast(f"✅ {res_msg}", icon="📧")[cite: 20]
                    else:
                        st.warning(res_msg)[cite: 20]
                except Exception as ex:
                    st.error(f"Failed to send email: {ex}")[cite: 20]
        st.markdown('</div>', unsafe_allow_html=True)

        menu_config = []

        def make_station_label(title: str, count: int = 0) -> str:
            if count > 0:
                return f"{title}  ({count})"
            return title

        # --- SECTION: MANAGEMENT ---
        if account_type in ["SUPER_ADMIN", "CEO", "MANAGER"]:[cite: 20]
            st.markdown('<div class="nav-category">DIRECTORIES</div>', unsafe_allow_html=True)
            
            if account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
                del_count = p_counts.get("DELETION_REQS", 0)[cite: 20]
                lbl_exec = make_station_label("👑 Executive Overview", del_count)[cite: 20]
                menu_config.append(("EXEC_OVERVIEW", lbl_exec, ceo_admin.render_overview))[cite: 20]
                menu_config.append(("EXEC_RBAC", "👥 Staff & RBAC Admin", ceo_admin.render_user_management))[cite: 20]

            menu_config.append(("MGR_TRACK", "🔍 Floor Track & Audit", manager_view.render))[cite: 20]

        # --- SECTION: OPERATIONS FLOOR ---
        st.markdown('<div class="nav-category">OPERATIONS</div>', unsafe_allow_html=True)

        if "MOD_A" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            menu_config.append(("MOD_A", "📝 Order Intake (Sales)", mod_a_sales.render))[cite: 20]

        if "MOD_B" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            c_b = p_counts.get("DESIGN", 0)[cite: 20]
            menu_config.append(("MOD_B", make_station_label("🎨 Design & Proofs", c_b), mod_b_design.render))[cite: 20]

        if "MOD_C" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            c_c = p_counts.get("PAYMENT", 0)[cite: 20]
            menu_config.append(("MOD_C", make_station_label("💳 Accounts Clearance", c_c), mod_c_payment.render))[cite: 20]

        if "MOD_D" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            c_d = p_counts.get("PRODUCTION", 0)[cite: 20]
            menu_config.append(("MOD_D", make_station_label("⚙️ Production Floor", c_d), mod_d_production.render))[cite: 20]

        if "MOD_E" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            c_e = p_counts.get("QC", 0)[cite: 20]
            menu_config.append(("MOD_E", make_station_label("🔍 Quality Check (QC)", c_e), mod_e_qc.render))[cite: 20]

        if "MOD_F" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            c_f = p_counts.get("DISPATCH", 0)[cite: 20]
            menu_config.append(("MOD_F", make_station_label("🚚 Dispatch & Delivery", c_f), mod_f_dispatch.render))[cite: 20]

        if "MOD_G" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:[cite: 20]
            c_g = p_counts.get("BILLING", 0)[cite: 20]
            menu_config.append(("MOD_G", make_station_label("🧾 Billing & Invoicing", c_g), mod_g_billing.render))[cite: 20]

        # --- SECTION: DIRECTORIES ---
        if account_type in ["SUPER_ADMIN", "CEO", "MANAGER"] or user_perms:[cite: 20]
            st.markdown('<div class="nav-category">DIRECTORIES</div>', unsafe_allow_html=True)
            menu_config.append(("CUSTOMERS", "🏢 Customers Directory", customer_dashboard.render))
            menu_config.append(("VENDORS", "🏭 Vendors & Outsource", vendor_dashboard.render))

        if not menu_config:
            st.warning("No active permissions assigned.")
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

        # --- SECTION: SETTINGS & USER FOOTER ---
        st.markdown('<div class="nav-