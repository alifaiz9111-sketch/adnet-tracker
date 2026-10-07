import streamlit as st
from datetime import datetime
import pytz
from database import (
    supabase,
    get_next_job_no,
    get_stage_job_count
)

IST = pytz.timezone('Asia/Kolkata')

def render(user):
    st.title("📝 Workstation 1: Order Intake & Sales")
    st.caption("Create verified job sheets, attach specifications, and track incoming client requests.")

    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])
    
    # Manager check: Super Admin, CEO, or employees with explicit view-all permissions
    is_sales_mgr = account_type in ["SUPER_ADMIN", "CEO"] or "VIEW_ALL_JOBS" in user_perms or "MOD_A_MGR" in user_perms

    tab_create, tab_view = st.tabs(["➕ Create New Job Sheet", "📋 Active Sales Orders"])

    # =========================================================================
    # TAB 1: CREATE NEW JOB SHEET (WITH STRICT DATA GATES)
    # =========================================================================
    with tab_create:
        next_no = get_next_job_no()
        st.subheader(f"New Order Entry (Job #{next_no})")

        with st.form("new_job_form", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                client_name = st.text_input("Client / Company Name*").strip()
                contact_person = st.text_input("Contact Person Name").strip()
                contact_phone = st.text_input("Contact Phone Number*").strip()
            with col_c2:
                payment_terms = st.selectbox("Payment Terms*", ["Full Advance", "50% Token Advance", "MNC Credit 30 Days", "MNC Credit 60 Days"])
                due_date = st.date_input("Delivery Due Date*", min_value=datetime.now(IST).date())
                delivery_mode = st.selectbox("Delivery Type*", ["Self Pickup", "Direct Hand Delivery", "Third-Party Logistics / Courier"])

            st.markdown("---")
            st.markdown("#### 📦 Job Line Items & Specifications")
            col_i1, col_i2 = st.columns([2, 1])
            with col_i1:
                item_desc = st.text_area("Item Description / Specifications*", placeholder="e.g. Star Flex Frontlit Banner with wooden frame").strip()
                media_substrate = st.text_input("Material / Substrate*", placeholder="e.g. 340 GSM Star Flex / Vinyl on 3mm Foam Sheet").strip()
            with col_i2:
                item_qty = st.number_input("Quantity*", min_value=1, value=1, step=1)
                item_rate = st.number_input("Unit Rate (₹)*", min_value=0.0, value=0.0, step=10.0)
                item_total = item_qty * item_rate
                st.metric("Total Line Amount (₹)", f"₹ {item_total:,.2f}")

            delivery_address = st.text_input("Delivery Address / Destination", placeholder="Leave blank if Self Pickup").strip()
            special_notes = st.text_area("Production / Finishing Remarks", placeholder="e.g. Center seam, eyelets every 2 feet").strip()

            submit = st.form_submit_button("🚀 Submit Job Sheet to Design", type="primary", use_container_width=True)

            if submit:
                # STRICT VALIDATION GATES (Requirement 5)
                if not client_name:
                    st.error("Client / Company Name is strictly required.")
                elif not contact_phone:
                    st.error("Contact Phone Number is mandatory.")
                elif not item_desc:
                    st.error("Item Description / Specifications cannot be empty.")
                elif not media_substrate:
                    st.error("Material / Substrate specification is required for the floor.")
                elif item_rate <= 0:
                    st.error("Unit Rate must be greater than ₹ 0.00.")
                else:
                    now_iso = datetime.now(IST).isoformat()
                    try:
                        # 1. Insert into jobs table
                        job_payload = {
                            "job_no": next_no,
                            "client_name": client_name,
                            "contact_person": contact_person,
                            "contact_phone": contact_phone,
                            "payment_terms": payment_terms,
                            "due_date": str(due_date),
                            "delivery_mode": delivery_mode,
                            "current_stage": "DESIGN",
                            "holding_employee_role": "GRAPHIC_DESIGNER",
                            "order_taken_by": user["username"],
                            "created_by": user["username"],
                            "created_at": now_iso,
                            "last_dispatched_by": user["username"],
                            "is_billed": False
                        }
                        job_res = supabase.table("jobs").insert(job_payload).execute()

                        if job_res.data:
                            created_job_id = job_res.data[0]["job_id"]

                            # 2. Insert line item
                            item_payload = {
                                "job_id": created_job_id,
                                "item_no": 1,
                                "description_spec": item_desc,
                                "material": media_substrate,
                                "qty": int(item_qty),
                                "unit_rate": float(item_rate),
                                "amount": float(item_total),
                                "delivery_address": delivery_address if delivery_address else "Self Pickup",
                                "remarks": special_notes
                            }
                            supabase.table("job_items").insert(item_payload).execute()

                            st.success(f"Job #{next_no} successfully generated and routed to Design Desk!")
                            st.rerun()
                        else:
                            st.error("Could not register job sheet. Please retry.")
                    except Exception as e:
                        st.error(f"Error creating job sheet: {str(e)}")

    # =========================================================================
    # TAB 2: ACTIVE SALES ORDERS (SCOPED VISIBILITY - Requirement 4)
    # =========================================================================
    with tab_view:
        if is_sales_mgr:
            st.info("👔 **Manager View:** Showing all sales jobs created across all employees.")
            jobs_query = supabase.table("jobs").select("*").order("created_at", desc=True)
        else:
            st.info(f"👤 **Staff View:** Showing sales jobs created by you (`@{user['username']}`).")
            jobs_query = supabase.table("jobs").select("*").eq("order_taken_by", user["username"]).order("created_at", desc=True)

        res = jobs_query.execute()
        sales_jobs = res.data or []

        if not sales_jobs:
            st.info("No active sales orders found.")
        else:
            for sj in sales_jobs:
                with st.container(border=True):
                    c_left, c_right = st.columns([3, 1])
                    with c_left:
                        st.subheader(f"Job #{sj.get('job_no')} — {sj.get('client_name')}")
                        st.caption(f"Created: `{sj.get('created_at')[:10]}` | Rep: `@{sj.get('order_taken_by')}` | Phone: `{sj.get('contact_phone', 'N/A')}`")
                        st.write(f"**Terms:** {sj.get('payment_terms')} | **Target Date:** {sj.get('due_date')}")
                    with c_right:
                        curr_stage = sj.get("current_stage", "UNKNOWN")
                        if curr_stage == "SETTLED":
                            st.success("✅ **SETTLED**")
                        else:
                            st.warning(f"📍 Desk: **{curr_stage}**")
                        if sj.get("is_returned"):
                            st.error(f"⚠️ Return Note: {sj.get('return_reason')}")