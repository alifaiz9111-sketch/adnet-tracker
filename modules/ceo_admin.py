import streamlit as st
import pandas as pd
from database import (
    get_all_active_jobs,
    get_all_users,
    create_user,
    update_user_status,
    extend_job_deadline,
    supabase
)
from datetime import date

def render_overview(user):
    st.title("👑 Executive Overview & Bottlenecks")

    jobs = get_all_active_jobs()
    df = pd.DataFrame(jobs) if jobs else pd.DataFrame()

    today_str = str(date.today())
    today_jobs = supabase.table("jobs").select("job_id").eq("date_received", today_str).execute().data
    today_items = supabase.table("job_items").select("amount").execute().data
    today_val = sum(i["amount"] for i in today_items)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Jobs", len(jobs))
    col2.metric("Today's Booking (₹)", f"₹ {today_val:,.2f}")
    
    # Overdue calculation
    overdue_jobs = [j for j in jobs if j.get("due_date") and j["due_date"] < today_str and not j.get("next_due_date")]
    col3.metric("Critical Overdue", f"{len(overdue_jobs)} Jobs", delta_color="inverse")
    col4.metric("Floor Stages Active", len(set(j["current_stage"] for j in jobs)) if jobs else 0)

    # Active Bottleneck Table
    st.markdown("### ⚠️ Active Floor Bottleneck Escalation Table")
    if not df.empty:
        display_df = df[["job_no", "client_name", "due_date", "current_stage", "holding_employee_role", "priority"]]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No active jobs currently on floor.")

    # Overdue Deadline Extension
    if overdue_jobs:
        st.markdown("### 🔴 Deadline Extension Authorization (CEO / Admin Only)")
        for oj in overdue_jobs:
            with st.expander(f"⚠ Job #{oj['job_no']} - {oj['client_name']} (Due: {oj['due_date']})"):
                st.write(f"**Holding Stage:** {oj['holding_employee_role']}")
                new_date = st.date_input(f"Set Next Due Date for #{oj['job_no']}", key=f"nd_{oj['job_id']}")
                reason = st.text_input(f"Reason for Delay (#{oj['job_no']})", key=f"rs_{oj['job_id']}")
                if st.button(f"Approve Extension for #{oj['job_no']}", key=f"btn_{oj['job_id']}"):
                    extend_job_deadline(oj["job_id"], str(new_date), reason, user["user_id"])
                    st.success(f"Deadline updated for Job #{oj['job_no']}")
                    st.rerun()

def render_user_management(user):
    st.title("👥 Staff & Role Permission Administration")
    users = get_all_users()
    st.dataframe(pd.DataFrame(users), use_container_width=True)

    st.markdown("---")
    st.markdown("### ➕ Add New Employee")
    with st.form("new_emp_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        uname = c1.text_input("Username *")
        pwd = c2.text_input("Password *", type="password")
        fname = c3.text_input("Full Name *")

        email = st.text_input("Email")
        
        # Super Admin can create CEO or Staff; CEO can only create Staff
        if user["account_type"] == "SUPER_ADMIN":
            role = st.selectbox("Account Type", ["STAFF", "CEO", "SUPER_ADMIN"])
        else:
            role = "STAFF"

        st.markdown("##### Check Permitted Form Modules:")
        col_m1, col_m2 = st.columns(2)
        m_a = col_m1.checkbox("Module A: Order Intake (Emp A)")
        m_b = col_m1.checkbox("Module B: Design & Proofs (Emp B)")
        m_c = col_m1.checkbox("Module C: Advance Payment (Emp C)")
        m_d = col_m1.checkbox("Module D: Production Floor (Emp D)")
        m_e = col_m2.checkbox("Module E: Quality Check (Emp E)")
        m_f = col_m2.checkbox("Module F: Dispatch & Delivery (Emp F)")
        m_g = col_m2.checkbox("Module G: Billing Review (Emp G)")
        m_bill = col_m2.checkbox("Module BILL: Accounts Billing Desk")

        submit = st.form_submit_button("Create User & Assign Permissions", type="primary")
        if submit:
            mods = []
            if m_a: mods.append("MOD_A")
            if m_b: mods.append("MOD_B")
            if m_c: mods.append("MOD_C")
            if m_d: mods.append("MOD_D")
            if m_e: mods.append("MOD_E")
            if m_f: mods.append("MOD_F")
            if m_g: mods.append("MOD_G")
            if m_bill: mods.append("MOD_BILL")

            create_user(uname, pwd, fname, role, email, mods)
            st.success(f"User {uname} created successfully!")
            st.rerun()