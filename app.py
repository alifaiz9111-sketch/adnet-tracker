import streamlit as st
from datetime import datetime
import pytz

from database import (
    authenticate_user,
    update_user_last_login,
    get_user_login_summary
)

# Page configuration
st.set_page_config(
    page_title="AdNet Production & Operations ERP",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import Workstation Modules
import modules.mod_a_sales as mod_a_sales
import modules.mod_d_production as mod_d_production
import modules.mod_f_dispatch as mod_f_dispatch
import modules.mod_pipeline_monitor as mod_pipeline_monitor

# Attempt optional legacy module imports with fallbacks
try:
    import modules.mod_b_design as mod_b_design
except ImportError:
    mod_b_design = None

try:
    import modules.mod_c_accounts as mod_c_accounts
except ImportError:
    mod_c_accounts = None

try:
    import modules.mod_e_qc as mod_e_qc
except ImportError:
    mod_e_qc = None

try:
    import modules.mod_g_billing as mod_g_billing
except ImportError:
    mod_g_billing = None

try:
    import modules.accounts_queue as accounts_queue
except ImportError:
    accounts_queue = None

try:
    import modules.admin_management as admin_management
except ImportError:
    admin_management = None


def render_login():
    """Login card with company logo and secure credentials handling."""
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            # Safe company logo rendering
            try:
                st.image("assets/logo.png", width=220)
            except Exception:
                st.markdown("<h1 style='color: #E10600; font-weight: 900; letter-spacing: -1px; margin-bottom: 0px;'>AdNet</h1>", unsafe_allow_html=True)
            
            st.markdown("### Internal Operations & Production ERP")
            st.caption("Sign in with authorized workforce credentials to access assigned desks.")

            username = st.text_input("Username", key="login_user").strip()
            password = st.text_input("Password", type="password", key="login_pass").strip()

            if st.button("Sign In to Workstation", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        update_user_last_login(user["user_id"])
                        st.rerun()
                    else:
                        st.error("Invalid credentials or deactivated account. Contact Admin.")


def main():
    if not st.session_state.get("authenticated", False):
        render_login()
        return

    user = st.session_state["user"]
    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])

    # Sidebar Navigation & Branding
    with st.sidebar:
        try:
            st.image("assets/logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h2 style='color: #E10600; font-weight: 900; margin-bottom: 0px;'>AdNet</h2>", unsafe_allow_html=True)

        st.caption(f"Logged in as **@{user['username']}** ({account_type})")
        st.markdown("---")

        # Dynamic desk navigation based on permissions
        nav_options = {}

        # 1. Pipeline Monitor (Available to Managers or employees with PERM_MONITOR)
        if account_type in ["CEO", "SUPER_ADMIN"] or "PERM_MONITOR" in user_perms or "VIEW_ALL_JOBS" in user_perms:
            nav_options["📊 Pipeline & Status Monitor"] = "MONITOR"

        # 2. Operational Workstations
        if account_type in ["CEO", "SUPER_ADMIN"] or "MOD_A" in user_perms or "MOD_A_MGR" in user_perms:
            nav_options["📝 1. Order Intake & Sales"] = "MOD_A"

        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_B" in user_perms) and mod_b_design:
            nav_options["🎨 2. Design & Proofing"] = "MOD_B"

        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_C" in user_perms) and mod_c_accounts:
            nav_options["💳 3. Advance & Accounts"] = "MOD_C"

        if account_type in ["CEO", "SUPER_ADMIN"] or "MOD_D" in user_perms:
            nav_options["⚙️ 4. Production Floor"] = "MOD_D"

        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_E" in user_perms) and mod_e_qc:
            nav_options["🔍 5. Quality Check (QC)"] = "MOD_E"

        if account_type in ["CEO", "SUPER_ADMIN"] or "MOD_F" in user_perms:
            nav_options["🚚 6. Dispatch & Delivery"] = "MOD_F"

        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_G" in user_perms) and mod_g_billing:
            nav_options["📋 7. Billing Review"] = "MOD_G"

        # 3. CA / Invoicing Queue
        if (account_type in ["CEO", "SUPER_ADMIN", "CA"] or "MOD_BILL" in user_perms) and accounts_queue:
            nav_options["🧾 8. CA GST Billing Queue"] = "MOD_BILL"

        # 4. System Administration
        if account_type in ["CEO", "SUPER_ADMIN"] and admin_management:
            nav_options["🛠️ Admin Management"] = "ADMIN"

        if not nav_options:
            st.warning("No modules currently assigned to your account. Please contact the administrator.")
            if st.button("Log Out"):
                st.session_state.clear()
                st.rerun()
            return

        choice = st.radio("Navigation", list(nav_options.keys()), index=0)
        selected_module_key = nav_options[choice]

        st.markdown("---")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Top Login Summary Notification Banner
    summary = get_user_login_summary(user)
    if account_type in ["CEO", "SUPER_ADMIN"]:
        if summary.get("new_jobs_count", 0) > 0:
            st.toast(f"🔔 {summary['new_jobs_count']} new jobs created since last visit (₹{summary['new_jobs_total_val']:,.2f})", icon="ℹ️")
    elif summary.get("pending_stage_name") and summary.get("pending_stage_count", 0) > 0:
        st.info(f"📌 You have **{summary['pending_stage_count']}** pending task(s) in **{summary['pending_stage_name']}**.")

    # View Router
    if selected_module_key == "MONITOR":
        mod_pipeline_monitor.render(user)
    elif selected_module_key == "MOD_A":
        mod_a_sales.render(user)
    elif selected_module_key == "MOD_B" and mod_b_design:
        mod_b_design.render(user)
    elif selected_module_key == "MOD_C" and mod_c_accounts:
        mod_c_accounts.render(user)
    elif selected_module_key == "MOD_D":
        mod_d_production.render(user)
    elif selected_module_key == "MOD_E" and mod_e_qc:
        mod_e_qc.render(user)
    elif selected_module_key == "MOD_F":
        mod_f_dispatch.render(user)
    elif selected_module_key == "MOD_G" and mod_g_billing:
        mod_g_billing.render(user)
    elif selected_module_key == "MOD_BILL" and accounts_queue:
        accounts_queue.render(user)
    elif selected_module_key == "ADMIN" and admin_management:
        admin_management.render(user)


if __name__ == "__main__":
    main()