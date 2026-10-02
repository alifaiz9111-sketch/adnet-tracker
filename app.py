import streamlit as st
from database import authenticate_user
from modules import (
    mod_a_sales,
    mod_b_design,
    mod_c_payment,
    mod_d_production,
    mod_e_qc,
    mod_f_dispatch,
    mod_g_billing,
    accounts_queue,
    ceo_admin
)

st.set_page_config(
    page_title="Adnet Print Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "user" not in st.session_state:
    st.session_state["user"] = None

def login_ui():
    st.title("🔐 Adnet Print - Employee Login")
    col1, col2, _ = st.columns([1, 1, 1])
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In", use_container_width=True, type="primary"):
            user = authenticate_user(username, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Invalid Username or Password")

def logout():
    st.session_state["user"] = None
    st.rerun()

def main():
    user = st.session_state["user"]
    if not user:
        login_ui()
        return

    # Sidebar Header
    st.sidebar.markdown(f"### 👤 {user['full_name']}")
    st.sidebar.caption(f"Role: **{user['account_type']}**")
    if st.sidebar.button("Logout", use_container_width=True):
        logout()

    # Dynamic Navigation Construction based on Permissions
    user_perms = user.get("permissions", [])
    account_type = user["account_type"]

    menu_options = {}

    if account_type in ["SUPER_ADMIN", "CEO"]:
        menu_options["📊 Executive Overview"] = ceo_admin.render_overview
        menu_options["👥 Staff & RBAC Admin"] = ceo_admin.render_user_management

    if account_type == "SUPER_ADMIN" or "MOD_A" in user_perms:
        menu_options["📝 1. Order Intake (Sales)"] = mod_a_sales.render
    if account_type == "SUPER_ADMIN" or "MOD_B" in user_perms:
        menu_options["🎨 2. Design & Proofs"] = mod_b_design.render
    if account_type == "SUPER_ADMIN" or "MOD_C" in user_perms:
        menu_options["💳 3. Advance / Accounts"] = mod_c_payment.render
    if account_type == "SUPER_ADMIN" or "MOD_D" in user_perms:
        menu_options["⚙️ 4. Production Floor"] = mod_d_production.render
    if account_type == "SUPER_ADMIN" or "MOD_E" in user_perms:
        menu_options["🔍 5. Quality Check (QC)"] = mod_e_qc.render
    if account_type == "SUPER_ADMIN" or "MOD_F" in user_perms:
        menu_options["🚚 6. Dispatch & Delivery"] = mod_f_dispatch.render
    if account_type == "SUPER_ADMIN" or "MOD_G" in user_perms:
        menu_options["📑 7. Billing Review"] = mod_g_billing.render
    if account_type == "SUPER_ADMIN" or "MOD_BILL" in user_perms or account_type == "CEO":
        menu_options["🧾 8. Accounts Billing Queue"] = accounts_queue.render

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 📂 Your Workspaces")
    choice = st.sidebar.radio("Navigation", list(menu_options.keys()), label_visibility="collapsed")

    # Render selected module
    menu_options[choice](user)

if __name__ == "__main__":
    main()