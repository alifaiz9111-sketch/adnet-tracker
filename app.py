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
    ceo_admin
)

st.set_page_config(
    page_title="AdNet Operations",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None


def inject_adminator_css():
    """Injects high-end Adminator-inspired design system with Brand Red accents."""
    st.markdown("""
        <style>
        /* Base typography & Canvas */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #F8FAFC;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
            padding-top: 1rem;
        }

        /* Brand App Header */
        .brand-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
            padding: 0 4px;
        }
        .brand-avatar {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, #E11D48 0%, #BE123C 100%);
            color: #FFFFFF;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 4px 10px rgba(225, 29, 72, 0.25);
        }
        .brand-text-title {
            font-size: 16px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.1;
        }
        .brand-text-sub {
            font-size: 11px;
            font-weight: 600;
            color: #94A3B8;
            letter-spacing: 0.5px;
        }

        /* Section Headings */
        .sidebar-section-title {
            font-size: 11px;
            font-weight: 700;
            color: #94A3B8;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin: 20px 0 8px 4px;
        }

        /* Radio Navigation Items */
        div[data-testid="stRadio"] > div {
            gap: 2px !important;
        }
        div[data-testid="stRadio"] label {
            border-radius: 8px !important;
            padding: 7px 12px !important;
            transition: all 0.15s ease-in-out !important;
            border: 1px solid transparent !important;
            margin-bottom: 2px;
        }
        div[data-testid="stRadio"] label:hover {
            background-color: #FFF1F2 !important; /* Soft rose tint */
            color: #E11D48 !important;
        }

        /* Active radio selected item */
        div[data-testid="stRadio"] label[data-checked="true"],
        div[data-testid="stRadio"] label:has(input:checked) {
            background: #FFF1F2 !important;
            border-left: 3px solid #E11D48 !important;
        }
        div[data-testid="stRadio"] label[data-checked="true"] p,
        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #E11D48 !important;
            font-weight: 700 !important;
        }

        /* Adminator Tag Pills */
        .pill-badge {
            background-color: #E11D48;
            color: white;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 9999px;
            margin-left: auto;
            display: inline-block;
        }
        .pill-new {
            background-color: #FFE4E6;
            color: #E11D48;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 6px;
            margin-left: 6px;
        }

        /* Profile Footer Card */
        .user-footer-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #F1F5F9;
            background: #FAFAFA;
            margin-top: 15px;
        }
        .user-footer-avatar {
            width: 36px;
            height: 36px;
            background-color: #0F172A;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 13px;
        }
        .user-footer-meta {
            line-height: 1.2;
            flex-grow: 1;
        }
        .user-footer-name {
            font-size: 13px;
            font-weight: 700;
            color: #0F172A;
        }
        .user-footer-role {
            font-size: 11px;
            color: #64748B;
        }

        /* Custom buttons styling */
        button[kind="secondary"] {
            border: 1px solid #E2E8F0 !important;
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }
        button[kind="secondary"]:hover {
            border-color: #E11D48 !important;
            color: #E11D48 !important;
        }
        button[kind="primary"] {
            background-color: #E11D48 !important;
            border: none !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }
        button[kind="primary"]:hover {
            background-color: #BE123C !important;
        }
        </style>
    """, unsafe_allow_html=True)


def main():
    inject_adminator_css()

    # --- LOGIN SCREEN ---
    if not st.session_state.authenticated:
        _, logo_col, _ = st.columns([1, 1.2, 1])
        with logo_col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("""
                    <div style="text-align: center; margin-bottom: 20px;">
                        <div style="width: 48px; height: 48px; background: #E11D48; color: white; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 800; margin-bottom: 12px;">A</div>
                        <h3 style="margin: 0; font-weight: 800; color: #0F172A;">Adminator ERP</h3>
                        <p style="margin: 0; color: #64748B; font-size: 13px;">Commercial Print & Sign Floor Operations</p>
                    </div>
                """, unsafe_allow_html=True)

                with st.form("login_form"):
                    username = st.text_input("Username").strip()
                    password = st.text_input("Password / PIN", type="password").strip()
                    submit = st.form_submit_button("Sign In to Workspace", type="primary", use_container_width=True)

                    if submit:
                        user = authenticate_user(username, password)
                        if user:
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            log_audit(user["user_id"], "LOGIN", f"User {username} authenticated.")
                            st.rerun()
                        else:
                            st.error("Invalid credentials or deactivated account.")
        return

    # --- AUTHENTICATED SESSION ---
    current_user = st.session_state.user
    account_type = current_user.get("account_type", "STAFF")
    user_perms = current_user.get("permissions") or []

    # Real-time queue counters
    p_counts = get_station_pending_counts()

    # --- SIDEBAR (ADMINATOR DESIGN SYSTEM) ---
    with st.sidebar:
        # 1. Top Brand Icon & Version
        st.markdown("""
            <div class="brand-header">
                <div class="brand-avatar">A</div>
                <div>
                    <div class="brand-text-title">Adminator</div>
                    <div class="brand-text-sub">v3.1 • OPERATIONS</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 2. Daily Report Dispatcher Button (Styled like "Export / New report")
        if st.button("✉️ Export Daily Digest", use_container_width=True, type="secondary"):
            with st.spinner("Dispatching summary email..."):
                try:
                    from email_service import send_daily_jobsheet_digest
                    recipient = current_user.get("email")
                    ok, res_msg = send_daily_jobsheet_digest(recipient_email=recipient)
                    if ok:
                        st.toast(f"Digest dispatched: {res_msg}", icon="✉️")
                    else:
                        st.warning(res_msg)
                except Exception as ex:
                    st.error(f"Failed to dispatch: {ex}")

        st.markdown('<div class="sidebar-section-title">WORKSPACES</div>', unsafe_allow_html=True)

        menu_config = []

        def format_nav_item(name: str, count: int = 0, is_new: bool = False) -> str:
            badge = ""
            if count > 0:
                badge = f"  [{count}]"
                if is_new:
                    badge += "  NEW"
            return f"{name}{badge}"

        # Executive Desks
        if account_type in ["SUPER_ADMIN", "CEO"]:
            del_c = p_counts.get("DELETION_REQS", 0)
            menu_config.append(("EXEC_OVERVIEW", format_nav_item("👑 Executive Overview", del_c, is_new=(del_c > 0)), ceo_admin.render_overview))
            menu_config.append(("EXEC_RBAC", "👥 User & RBAC Master", ceo_admin.render_user_management))

        # Manager Desk
        if account_type in ["MANAGER", "SUPER_ADMIN", "CEO"]:
            menu_config.append(("MGR_TRACK", "🔍 Floor Track & Audit", manager_view.render))

        # Operational Floor Stations
        if "MOD_A" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            menu_config.append(("MOD_A", "📝 Order Intake (Sales)", mod_a_sales.render))

        if "MOD_B" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c = p_counts.get("DESIGN", 0)
            menu_config.append(("MOD_B", format_nav_item("🎨 Design & Proofs", c, is_new=(c > 0)), mod_b_design.render))

        if "MOD_C" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c = p_counts.get("PAYMENT", 0)
            menu_config.append(("MOD_C", format_nav_item("💳 Accounts Clearance", c, is_new=(c > 0)), mod_c_payment.render))

        if "MOD_D" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c = p_counts.get("PRODUCTION", 0)
            menu_config.append(("MOD_D", format_nav_item("⚙️ Production Floor", c, is_new=(c > 0)), mod_d_production.render))

        if "MOD_E" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c = p_counts.get("QC", 0)
            menu_config.append(("MOD_E", format_nav_item("🔍 Quality Check (QC)", c, is_new=(c > 0)), mod_e_qc.render))

        if "MOD_F" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c = p_counts.get("DISPATCH", 0)
            menu_config.append(("MOD_F", format_nav_item("🚚 Field Dispatch", c, is_new=(c > 0)), mod_f_dispatch.render))

        if "MOD_G" in user_perms or account_type in ["SUPER_ADMIN", "CEO"]:
            c = p_counts.get("BILLING", 0)
            menu_config.append(("MOD_G", format_nav_item("🧾 Invoicing & Billing", c, is_new=(c > 0)), mod_g_billing.render))

        if not menu_config:
            st.warning("No assigned workstation desks.")
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

        st.markdown('<div class="sidebar-section-title">ACCOUNT & SECURITY</div>', unsafe_allow_html=True)

        with st.popover("🔑 Change Password / PIN", use_container_width=True):
            st.markdown("##### Security Credentials")
            old_p = st.text_input("Current PIN", type="password", key="chg_old_pwd").strip()
            new_p = st.text_input("New PIN", type="password", key="chg_new_pwd").strip()
            conf_p = st.text_input("Confirm PIN", type="password", key="chg_conf_pwd").strip()

            if st.button("Save PIN", type="primary", use_container_width=True, key="btn_update_pwd"):
                if not (old_p and new_p and conf_p):
                    st.error("Please fill all fields.")
                elif new_p != conf_p:
                    st.error("PINs do not match.")
                elif len(new_p) < 4:
                    st.error("Minimum 4 characters required.")
                else:
                    ok, msg = update_user_password(current_user["user_id"], old_p, new_p)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        # 3. Bottom User Profile Card (Matching image footer avatar & title)
        user_initials = "".join([part[0] for part in current_user['full_name'].split()][:2]).upper()
        st.markdown(f"""
            <div class="user-footer-card">
                <div class="user-footer-avatar">{user_initials}</div>
                <div class="user-footer-meta">
                    <div class="user-footer-name">{current_user['full_name']}</div>
                    <div class="user-footer-role">{account_type.lower()}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("Sign Out", use_container_width=True, type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    # --- MAIN CONTENT AREA ---
    # Top Breadcrumb & Welcome Banner matching Adminator style
    top_c1, top_c2 = st.columns([4, 1.2])
    with top_c1:
        st.caption(f"Workspace › **{selected_key or 'Dashboard'}**")
        st.markdown(
            f"## Welcome back, <span style='color: #E11D48;'>{current_user['full_name'].split()[0]}</span>", 
            unsafe_allow_html=True
        )
    with top_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Fast indicator
        st.caption(f"Role: **{account_type}** | Station: **{current_user.get('primary_station') or 'General'}**")

    st.markdown("---")

    # Render selected desk
    if selected_key and selected_key in handlers_map:
        handlers_map[selected_key](current_user)


if __name__ == "__main__":
    main()