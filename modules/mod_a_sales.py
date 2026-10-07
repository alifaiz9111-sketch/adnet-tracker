from datetime import datetime, timedelta
import pytz
import streamlit as st
from database import create_job_sheet, get_next_job_no, get_job_items, get_user_created_jobs
from email_service import send_ceo_order_alert

IST = pytz.timezone("Asia/Kolkata")

def render(user):
    st.subheader("📝 Module 1: Order Intake & Sales")
    st.caption(f"Logged in as: **{user['full_name']}** (`@{user['username']}`)")

    is_management = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]
    tab_new, tab_my_jobs = st.tabs(["📝 Create New Job Sheet", "📊 My Booked Jobs & Live Status"])

    # --- TAB 1: CREATE NEW JOB SHEET ---
    with tab_new:
        next_no = get_next_job_no()

        with st.form("new_order_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                job_no = st.text_input("Job Sheet #", value=next_no, disabled=True)
                client_name = st.text_input("Client / Company Name *")
            with c2:
                contact_person = st.text_input("Contact Person")
                contact_phone = st.text_input("Phone Number")
            with c3:
                due_date = st.date_input(
                    "Target Delivery Date", 
                    min_value=datetime.now(IST).date(), 
                    value=datetime.now(IST).date() + timedelta(days=3)
                )
                order_taken_by = st.text_input("Order Taken By", value=user["full_name"], disabled=True)

            st.markdown("##### Line Items Specification")
            num_items = st.number_input("Number of Items", min_value=1, max_value=20, value=1, step=1)
            
            items_data = []
            for i in range(int(num_items)):
                with st.container(border=True):
                    st.markdown(f"**Line Item #{i+1}**")
                    col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 2])
                    with col_a:
                        item_name = st.text_input(f"Item Description *", key=f"name_{i}")
                        remarks = st.text_input(f"Print Specs / Dimensions", key=f"rem_{i}")
                    with col_b:
                        qty = st.number_input("Qty", min_value=1, value=1, key=f"qty_{i}")
                        unit = st.selectbox("Unit", ["Pcs", "Sq.Ft", "Sets", "Rolls"], key=f"unit_{i}")
                    with col_c:
                        rate = st.number_input("Rate (₹)", min_value=0.0, value=0.0, step=10.0, key=f"rate_{i}")
                        amount = qty * rate
                        st.markdown(f"Total: **₹ {amount:,.2f}**")
                    with col_d:
                        delivery_address = st.text_area("Delivery Address / Branch", key=f"addr_{i}", height=90)
                    
                    items_data.append({
                        "item_name": item_name,
                        "specifications": remarks,
                        "quantity": qty,
                        "unit": unit,
                        "rate": rate,
                        "amount": amount,
                        "delivery_address": delivery_address,
                        "is_delivered": False
                    })

            submit = st.form_submit_button("Submit & Dispatch to Design Desk", type="primary", use_container_width=True)

            if submit:
                if not client_name.strip():
                    st.error("Client name is required.")
                    return

                total_val = sum(it["amount"] for it in items_data)
                job_payload = {
                    "job_no": next_no,
                    "client_name": client_name.strip(),
                    "contact_person": contact_person.strip(),
                    "contact_phone": contact_phone.strip(),
                    "due_date": str(due_date),
                    "order_taken_by": user["full_name"],
                    "current_stage": "DESIGN",
                    "is_billed": False,
                    "created_at": datetime.now(IST).isoformat()
                }

                success, res = create_job_sheet(job_payload, items_data)
                if success:
                    st.success(f"Job Sheet #{next_no} registered successfully.")
                    send_ceo_order_alert(next_no, client_name, items_data, total_val, user["full_name"])
                    st.rerun()
                else:
                    st.error(f"Error registering job sheet: {res}")

    # --- TAB 2: MY BOOKED JOBS & LIVE STATUS ---
    with tab_my_jobs:
        header_title = "All Sales Bookings (Management View)" if is_management else f"Jobs Created by {user['full_name']}"
        st.markdown(f"#### 📋 {header_title}")
        
        my_jobs = get_user_created_jobs(user["full_name"], is_management=is_management)
        
        if not my_jobs:
            st.info("You haven't logged any job sheets yet.")
        else:
            stage_map = {
                "DESIGN": ("🎨 Design & Proofs", "#58A6FF"),
                "PAYMENT": ("💳 Advance / Payment Desk", "#D29922"),
                "PRODUCTION": ("⚙️ Production Floor", "#BC8CFF"),
                "QC": ("🔍 Quality Check (QC)", "#DB6D28"),
                "DISPATCH": ("🚚 Dispatch & Delivery", "#3FB950"),
                "BILLING_REVIEW": ("🧾 Billing Review", "#F0883E"),
                "BILLING_QUEUE": ("💼 CA Invoicing Queue", "#1F6FEB"),
                "SETTLED": ("✅ Completed & Billed", "#238636")
            }

            # Pre-calculate counts for quick status pills
            count_all = len(my_jobs)
            count_active = sum(1 for j in my_jobs if j.get("current_stage") != "SETTLED" and not j.get("is_billed", False))
            count_completed = sum(1 for j in my_jobs if j.get("current_stage") == "SETTLED" or j.get("is_billed", False))

            # Quick Status Pills / Radio Filter Bar
            filter_col, search_col = st.columns([1.8, 1.2])
            with filter_col:
                selected_status = st.pills(
                    "Filter by Status",
                    options=[
                        f"All Jobs ({count_all})", 
                        f"⏳ Active on Floor ({count_active})", 
                        f"✅ Completed & Settled ({count_completed})"
                    ],
                    default=f"All Jobs ({count_all})"
                )
            with search_col:
                search_txt = st.text_input("🔍 Search Job # / Client", key="sales_search").strip().lower()

            # Apply Status Filter
            status_filtered_jobs = []
            for j in my_jobs:
                is_settled = (j.get("current_stage") == "SETTLED" or j.get("is_billed", False))
                if selected_status and "Active on Floor" in selected_status and is_settled:
                    continue
                if selected_status and "Completed & Settled" in selected_status and not is_settled:
                    continue
                status_filtered_jobs.append(j)

            # Apply Search Query Filter
            final_filtered_jobs = [
                j for j in status_filtered_jobs
                if (search_txt in str(j.get("job_no", "")).lower() or search_txt in str(j.get("client_name", "")).lower())
            ]

            st.caption(f"Showing {len(final_filtered_jobs)} matching job sheet(s).")

            if not final_filtered_jobs:
                st.info("No job sheets match the selected filter or search term.")
            else:
                for j in final_filtered_jobs:
                    curr_st = j.get("current_stage", "DESIGN")
                    st_label, st_color = stage_map.get(curr_st, (curr_st, "#8B949E"))
                    items = get_job_items(j["job_id"])
                    total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                    with st.container(border=True):
                        c1, c2, c3 = st.columns([2.5, 2, 1.5])
                        with c1:
                            st.markdown(f"### Job #{j['job_no']} - {j['client_name']}")
                            st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                            st.caption(f"📅 Booked On: `{str(j.get('created_at', ''))[:10]}` | Target: `{j.get('due_date')}`")
                        with c2:
                            st.markdown(f"**Current Status:**")
                            st.markdown(f"<span style='color:{st_color}; font-size:1.05rem; font-weight:bold;'>{st_label}</span>", unsafe_allow_html=True)
                            if j.get("is_returned"):
                                st.error(f"⚠️ Returned to floor: {j.get('return_reason')}")
                        with c3:
                            st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                            if j.get("is_billed") or curr_st == "SETTLED":
                                st.caption("🟢 Invoice Generated / Settled")

                        # Expandable line items preview
                        with st.expander("📦 View Items Breakdown", expanded=False):
                            for idx, it in enumerate(items, 1):
                                st.write(f"**{idx}. {it['item_name']}** — {it['quantity']} {it['unit']} @ ₹{float(it['rate']):,.2f} = **₹{float(it['amount']):,.2f}**")
                                if it.get("specifications"):
                                    st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;Specs: {it['specifications']}")