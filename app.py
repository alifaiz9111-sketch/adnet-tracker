import streamlit as st
from database import authenticate_user

# Page configuration
st.set_page_config(
    page_title="Signage & Print ERP Floor Manager",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None


def login_screen():
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("## 🏭 Signage & Print ERP")
            st.caption("Production Floor & Commercial Enterprise Management")

            username = st.text_input("Username", placeholder="e.g. admin or staff username").strip()
            password = st.text_input("Password / PIN", type="password").strip()

            if st.button("Sign In", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    success, user = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user
                        st.rerun()
                    else:
                        st.error("Invalid credentials or account inactive.")


def main():
    user = st.session_state.user
    role = user.get("account_type", "STAFF")
    perms = user.get("permissions") or []

    # Map workstations based on role and permissions
    module_catalog = {}

    if role in ["SUPER_ADMIN", "CEO", "MANAGER"] or "MOD_A" in perms:
        module_catalog["MOD_A"] = "📝 Sales & Order Intake"
    if role in ["SUPER_ADMIN", "CEO"] or "MOD_B" in perms:
        module_catalog["MOD_B"] = "🎨 Design & Pre-Press"
    if role in ["SUPER_ADMIN", "CEO"] or "MOD_C" in perms:
        module_catalog["MOD_C"] = "💳 Accounts & Advance"
    if role in ["SUPER_ADMIN", "CEO", "MANAGER"] or "MOD_D" in perms:
        module_catalog["MOD_D"] = "⚙️ Production Floor"
    if role in ["SUPER_ADMIN", "CEO", "MANAGER"] or "MOD_E" in perms:
        module_catalog["MOD_E"] = "🔍 Quality Check (QC)"
    if role in ["SUPER_ADMIN", "CEO", "MANAGER"] or "MOD_F" in perms:
        module_catalog["MOD_F"] = "🚚 Dispatch & Delivery"
    if role in ["SUPER_ADMIN", "CEO"] or "MOD_G" in perms:
        module_catalog["MOD_G"] = "🧾 Billing & Settlement"

    # Executive management panel
    if role in ["SUPER_ADMIN", "CEO"]:
        module_catalog["ADMIN_PANEL"] = "👑 Floor Overview & RBAC"

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown(f"### 👤 {user['full_name']}")
        st.caption(f"Role: `{role}` | Station: `{user.get('primary_station', 'General')}`")

        # --- MAIL TODAY'S JOBSHEET BUTTON ---
        if st.button("📧 Mail Today's Jobsheet", use_container_width=True, type="secondary"):
            with st.spinner("Compiling and sending digest..."):
                try:
                    from email_service import send_daily_jobsheet_digest
                    recipient = user.get("email")
                    ok, msg = send_daily_jobsheet_digest(recipient_email=recipient)
                    if ok:
                        st.toast(f"✅ {msg}", icon="📧")
                    else:
                        st.warning(msg)
                except Exception as ex:
                    st.error(f"Mail failed: {ex}")

        st.markdown("---")
        st.markdown("#### Workspaces")

        if not module_catalog:
            st.warning("No workstations assigned. Contact Admin.")
            selected_desk = None
        else:
            selected_desk = st.radio(
                "Workstations",
                options=list(module_catalog.keys()),
                format_func=lambda x: module_catalog[x],
                label_visibility="collapsed"
            )

        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    # --- MAIN ROUTING LOGIC ---
    if not selected_desk:
        st.info("Please select an accessible workstation from the sidebar.")
        return

    if selected_desk == "MOD_A":
        import modules.mod_a_sales as mod_a
        mod_a.render(user)
    elif selected_desk == "MOD_B":
        import modules.mod_b_design as mod_b
        mod_b.render(user)
    elif selected_desk == "MOD_C":
        import modules.mod_c_payment as mod_c
        mod_c.render(user)
    elif selected_desk == "ADMIN_PANEL":
        import modules.ceo_admin as ceo_adm
        t_dash, t_rbac = st.tabs(["📊 Floor Overview", "👥 User & Vendor RBAC"])
        with t_dash:
            ceo_adm.render_overview(user)
        with t_rbac:
            ceo_adm.render_user_management(user)
    else:
        st.info(f"Workstation desk `{module_catalog.get(selected_desk)}` is queued next in production development.")


if __name__ == "__main__":
    if not st.session_state.authenticated:
        login_screen()
    else:
        main()