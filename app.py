import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from database import (
    authenticate_user, 
    get_stage_job_count,
    update_user_last_login,
    get_user_login_summary
)
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
    page_title="AdNet - Workflow ERP",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0D1117;
        color: #E6EDF3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px !important;
        border: 1px solid #30363D !important;
        background-color: #161B22 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important;
    }
    div[data-testid="stMetric"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-left: 4px solid #E10600;
        padding: 14px 18px;
        border-radius: 6px;
    }
    div[data-testid="stMetric"] label {
        color: #8B949E !important;
        font-size: 0.8rem !important;
        font-weight: 600;
        text-transform: uppercase;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #F0F6FC !important;
        font-weight: 700 !important;
    }
    button[kind="primary"] {
        background: linear-gradient(180deg, #E10600 0%, #B80500 100%) !important;
        border: 1px solid #E10600 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
    }
    button[kind="primary"]:hover {
        background: linear-gradient(180deg, #FF1A1A 0%, #D40500 100%) !important;
        border-color: #FF1A1A !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #090D13 !important;
        border-right: 1px solid #21262D !important;
    }
</style>
""", unsafe_allow_html=True)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "login_popup_shown" not in st.session_state:
    st.session_state.login_popup_shown = False

@st.dialog("🔔 Workspace Briefing")
def show_login_dialog(user):
    account_type = user.get("account_type", "STAFF")
    full_name = user.get("full_name", "User")
    summary = get_user_login_summary(user)

    if account_type == "CEO":
        st.markdown(f"### Welcome back Executive Director, **{full_name}** 👋")
        st.write("Here is your executive floor intake summary:")
        cnt = summary["new_jobs_count"]
        val = summary["new_jobs_total_val"]
        st.markdown(f"#### **{cnt} new job sheet(s) created till your last visit of total ₹ {val:,.2f}**")
        st.caption("Live floor progression, pipeline metrics, and bottleneck monitors are ready.")
    elif account_type == "SUPER_ADMIN":
        st.markdown(f"### Welcome back System Administrator, **{full_name}** 👋")
        cnt = summary["new_jobs_count"]
        val = summary["new_jobs_total_val"]
        st.markdown(f"#### **{cnt} new job sheet(s) logged across all floors of total ₹ {val:,.2f}**")
        st.caption("All administrative tools, cascading deletions, and RBAC permissions are active.")
    else:
        st.markdown(f"### Welcome back, **{full_name}** 👋")
        stage_name = summary.get("pending_stage_name") or "Your Assigned Desk"
        pending_cnt = summary.get("pending_stage_count", 0)
        st.markdown(f"#### **You have {pending_cnt} pending job(s) awaiting action in {stage_name}.**")
        st.caption("Please review and clear pending work tickets to prevent floor bottlenecks.")

    st.markdown("---")
    c_btn, c_timer = st.columns([1, 2])
    with c_btn:
        if st.button("Got it, Close", type="primary", use_container_width=True):
            st.rerun()
    with c_timer:
        st.caption("⏱️ This briefing closes automatically in 30 seconds.")

    components.html("""
    <script>
        setTimeout(function() {
            var closeButtons = window.parent.document.querySelectorAll('button[aria-label="Close"]');
            if (closeButtons.length > 0) {
                closeButtons[closeButtons.length - 1].click();
            }
        }, 30000);
    </script>
    """, height=0, width=0)

def render_login():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        try:
            st.image("assets/logo.png", width=220)
        except Exception:
            st.markdown("<h1 style='color: #E10600; font-weight: 900; letter-spacing: -1px; margin-bottom: 0px;'>AdNet</h1>", unsafe_allow_html=True)

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
                        st.session_state.login_popup_shown = False
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

    with st.sidebar:
        try:
            st.image("assets/logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h2 style='color: #E10600; font-weight: 900; margin-bottom: 0px;'>AdNet</h2>", unsafe_allow_html=True)

        st.caption("Workstation Floor Tracker")
        st.markdown(f"**👤 {user['full_name']}**")
        st.caption(f"Role: `{account_type}` | User: `@{user['username']}`")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.login_popup_shown = False
            st.rerun()
        st.markdown("---")

    if not st.session_state.login_popup_shown:
        st.session_state.login_popup_shown = True
        show_login_dialog(user)
        update_user_last_login(user["user_id"])

    cnt_b = get_stage_job_count("DESIGN")
    cnt_c = get_stage_job_count("PAYMENT")
    cnt_d = get_stage_job_count("PRODUCTION")
    cnt_e = get_stage_job_count("QC")
    cnt_f = get_stage_job_count("DISPATCH")
    cnt_g = get_stage_job_count("BILLING_REVIEW")

    menu_options = {}

    if account_type in ["SUPER_ADMIN", "CEO"]:
        menu_options["👑 Executive Overview"] = ceo_admin.render_overview
        menu_options["👥 Staff & RBAC Admin"] = ceo_admin.render_user_management

    if account_type == "SUPER_ADMIN" or "MOD_A" in user_perms:
        menu_options["📝 1. Order Intake (Sales)"] = mod_a_sales.render

    if account_type == "SUPER_ADMIN" or "MOD_B" in user_perms:
        badge_b = f" ({cnt_b})" if cnt_b > 0 else ""
        menu_options[f"🎨 2. Design & Proofs{badge_b}"] = mod_b_design.render

    if account_type == "SUPER_ADMIN" or "MOD_C" in user_perms:
        badge_c = f" ({cnt_c})" if cnt_c > 0 else ""
        menu_options[f"💳 3. Advance / Accounts{badge_c}"] = mod_c_payment.render

    if account_type == "SUPER_ADMIN" or "MOD_D" in user_perms:
        badge_d = f" ({cnt_d})" if cnt_d > 0 else ""
        menu_options[f"⚙️ 4. Production Floor{badge_d}"] = mod_d_production.render

    if account_type == "SUPER_ADMIN" or "MOD_E" in user_perms:
        badge_e = f" ({cnt_e})" if cnt_e > 0 else ""
        menu_options[f"🔍 5. Quality Check (QC){badge_e}"] = mod_e_qc.render

    if account_type == "SUPER_ADMIN" or "MOD_F" in user_perms:
        badge_f = f" ({cnt_f})" if cnt_f > 0 else ""
        menu_options[f"🚚 6. Dispatch & Delivery{badge_f}"] = mod_f_dispatch.render

    if account_type == "SUPER_ADMIN" or "MOD_G" in user_perms:
        badge_g = f" ({cnt_g})" if cnt_g > 0 else ""
        menu_options[f"🧾 7. Billing Review{badge_g}"] = mod_g_billing.render

    if account_type == "CEO":
        menu_options["🧾 Accounts Billing Queue"] = accounts_queue.render
    elif account_type in ["SUPER_ADMIN", "AUDITOR", "FREELANCER_CA"] or "MOD_BILL" in user_perms:
        menu_options["🧾 8. Accounts Billing & Audit"] = accounts_queue.render

    with st.sidebar:
        st.markdown("#### 📂 Workspaces")
        if not menu_options:
            st.warning("No modules currently assigned to your account. Please contact administration.")
            return

        selected_menu = st.radio("Select Workspace", list(menu_options.keys()), label_visibility="collapsed")

    selected_view_fn = menu_options[selected_menu]
    selected_view_fn(user)

if __name__ == "__main__":
    main()