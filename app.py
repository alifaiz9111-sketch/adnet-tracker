import streamlit as st
from datetime import datetime
import pytz

from database import (
    authenticate_user,
    update_user_last_login,
    get_user_login_summary
)

st.set_page_config(
    page_title="AdNet Tracker",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Safe imports of modules
try:
    import modules.mod_a_sales as mod_a_sales
except ImportError:
    mod_a_sales = None

try:
    import modules.mod_b_design as mod_b_design
except ImportError:
    mod_b_design = None

try:
    import modules.mod_c_accounts as mod_c_accounts
except ImportError:
    mod_c_accounts = None

try:
    import modules.mod_d_production as mod_d_production
except ImportError:
    mod_d_production = None

try:
    import modules.mod_e_qc as mod_e_qc
except ImportError:
    mod_e_qc = None

try:
    import modules.mod_f_dispatch as mod_f_dispatch
except ImportError:
    mod_f_dispatch = None

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
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            try:
                st.image("assets/logo.png", width=220)
            except Exception:
                st.markdown("<h1 style='color: #E10600; font-weight: 900; margin-bottom: 0px;'>AdNet</h1>", unsafe_allow_html=True)
            
            st.markdown("### Internal Operations ERP")
            username = st.text_input("Username", key="login_user").strip()
            password = st.text_input("Password", type="password", key="login_pass").strip()

            if st.button("Sign In", type="primary", use_container_width=True):
                user = authenticate_user(username, password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user
                    update_user_last_login(user["user_id"])
                    st.rerun()
                else:
                    st.error("Invalid credentials.")


def main():
    if not st.session_state.get("authenticated", False):
        render_login()
        return

    user = st.session_state["user"]
    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])

    with st.sidebar:
        try:
            st.image("assets/logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h2 style='color: #E10600; font-weight: 900; margin-bottom: 0px;'>AdNet</h2>", unsafe_allow_html=True)

        st.caption(f"Logged in as **@{user['username']}** ({account_type})")
        st.markdown("---")

        nav = {}
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_A" in user_perms) and mod_a_sales:
            nav["📝 1. Order Intake & Sales"] = "MOD_A"
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_B" in user_perms) and mod_b_design:
            nav["🎨 2. Design & Proofing"] = "MOD_B"
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_C" in user_perms) and mod_c_accounts:
            nav["💳 3. Advance & Accounts"] = "MOD_C"
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_D" in user_perms) and mod_d_production:
            nav["⚙️ 4. Production Floor"] = "MOD_D"
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_E" in user_perms) and mod_e_qc:
            nav["🔍 5. Quality Check"] = "MOD_E"
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_F" in user_perms) and mod_f_dispatch:
            nav["🚚 6. Dispatch & Delivery"] = "MOD_F"
        if (account_type in ["CEO", "SUPER_ADMIN"] or "MOD_G" in user_perms) and mod_g_billing:
            nav["📋 7. Billing Review"] = "MOD_G"
        if (account_type in ["CEO", "SUPER_ADMIN", "CA"] or "MOD_BILL" in user_perms) and accounts_queue:
            nav["🧾 8. CA Billing Queue"] = "MOD_BILL"
        if account_type in ["CEO", "SUPER_ADMIN"] and admin_management:
            nav["🛠️ Admin Management"] = "ADMIN"

        if not nav:
            st.warning("No modules assigned.")
            if st.button("Log Out"):
                st.session_state.clear()
                st.rerun()
            return

        choice = st.radio("Navigation", list(nav.keys()))
        selected = nav[choice]

        st.markdown("---")
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Route
    if selected == "MOD_A": mod_a_sales.render(user)
    elif selected == "MOD_B": mod_b_design.render(user)
    elif selected == "MOD_C": mod_c_accounts.render(user)
    elif selected == "MOD_D": mod_d_production.render(user)
    elif selected == "MOD_E": mod_e_qc.render(user)
    elif selected == "MOD_F": mod_f_dispatch.render(user)
    elif selected == "MOD_G": mod_g_billing.render(user)
    elif selected == "MOD_BILL": accounts_queue.render(user)
    elif selected == "ADMIN": admin_management.render(user)


if __name__ == "__main__":
    main()