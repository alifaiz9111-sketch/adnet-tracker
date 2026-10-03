import streamlit as st
import pandas as pd
from database import authenticate_user, get_stage_job_count
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

# Page configuration
st.set_page_config(
    page_title="Adnet Advertising - Workflow ERP",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None


def render_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🖨️ Adnet Print")
        st.subheader("Internal Workflow & Floor Tracker")
        st.caption("Sign in with your employee credentials to access your workstations.")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username").strip()
            password = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submit:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.toast(f"Welcome back, {user['full_name']}!", icon="👋")
                        st.rerun()
                    else:
                        st.error("Invalid credentials or deactivated account.")


def main():
    if not st.session_state.authenticated or not st.session_state.user:
        render_login()
        return

    user = st.session_state.user
    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])

    # Sidebar Header & User Profile
    with st.sidebar:
        st.markdown(f"### 👤 {user['full_name']}")
        st.caption(f"Role: **{account_type}** | User: `@{user['username']}`")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
        st.markdown("---")

    # Fetch live stage counts for menu badges
    cnt_b = get_stage_job_count("DESIGN")
    cnt_c = get_stage_job_count("ADVANCE_PAYMENT")
    cnt_d = get_stage_job_count("PRODUCTION")
    cnt_e = get_stage_job_count("QC")
    cnt_f = get_stage_job_count("DISPATCH")
    cnt_g = get_stage_job_count("BILLING_REVIEW")

    # Configure dynamic workspaces based on user role & assigned permissions
    menu_options = {}

    # Executive & Administration tools
    if account_type in ["SUPER_ADMIN", "CEO"]:
        menu_options["👑 Executive Overview"] = ceo_admin.render_overview
        menu_options["👥 Staff & RBAC Admin"] = ceo_admin.render_user_management

    # Floor Module A: Order Intake (Sales)
    if account_type == "SUPER_ADMIN" or "MOD_A" in user_perms:
        menu_options["📝 1. Order Intake (Sales)"] = mod_a_sales.render

    # Floor Module B: Design & Proofs
    if account_type == "SUPER_ADMIN" or "MOD_B" in user_perms:
        badge_b = f" ({cnt_b})" if cnt_b > 0 else ""
        menu_options[f"🎨 2. Design & Proofs{badge_b}"] = mod_b_design.render

    # Floor Module C: Advance / Accounts
    if account_type == "SUPER_ADMIN" or "MOD_C" in user_perms:
        badge_c = f" ({cnt_c})" if cnt_c > 0 else ""
        menu_options[f"💳 3. Advance / Accounts{badge_c}"] = mod_c_payment.render

    # Floor Module D: Production Floor
    if account_type == "SUPER_ADMIN" or "MOD_D" in user_perms:
        badge_d = f" ({cnt_d})" if cnt_d > 0 else ""
        menu_options[f"⚙️ 4. Production Floor{badge_d}"] = mod_d_production.render

    # Floor Module E: Quality Check (QC)
    if account_type == "SUPER_ADMIN" or "MOD_E" in user_perms:
        badge_e = f" ({cnt_e})" if cnt_e > 0 else ""
        menu_options[f"🔍 5. Quality Check (QC){badge_e}"] = mod_e_qc.render

    # Floor Module F: Dispatch & Delivery
    if account_type == "SUPER_ADMIN" or "MOD_F" in user_perms:
        badge_f = f" ({cnt_f})" if cnt_f > 0 else ""
        menu_options[f"🚚 6. Dispatch & Delivery{badge_f}"] = mod_f_dispatch.render

    # Floor Module G: Billing Review
    if account_type == "SUPER_ADMIN" or "MOD_G" in user_perms:
        badge_g = f" ({cnt_g})" if cnt_g > 0 else ""
        menu_options[f"🧾 7. Billing Review{badge_g}"] = mod_g_billing.render

    # 8. Accounts Billing & Audit Desk
    # Visible to CEO, Super Admin, Accounts Staff, and the Auditor / Freelancer CA
    if account_type == "CEO":
        menu_options["🧾 Accounts Billing Queue"] = accounts_queue.render
    elif account_type in ["SUPER_ADMIN", "AUDITOR", "FREELANCER_CA"] or "MOD_BILL" in user_perms:
        menu_options["🧾 8. Accounts Billing & Audit"] = accounts_queue.render
    # Render Sidebar Navigation
    with st.sidebar:
        st.markdown("#### 📂 Your Workspaces")
        if not menu_options:
            st.warning("No modules currently assigned to your account. Please contact administration.")
            return
        
        selected_menu = st.radio("Select Workspace", list(menu_options.keys()), label_visibility="collapsed")

    # Render Selected Module View
    selected_view_fn = menu_options[selected_menu]
    selected_view_fn(user)


if __name__ == "__main__":
    main()