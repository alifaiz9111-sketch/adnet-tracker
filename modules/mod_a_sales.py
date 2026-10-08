from datetime import date, datetime
import streamlit as st
from database import (
    create_job_sheet,
    get_job_items,
    get_next_job_no,
    get_user_created_jobs,
    update_job_sheet_by_management,
)


def render(user):
    st.subheader("📝 Module 1: Order Intake & Commercial Jobsheet Creation")
    st.caption(
        f"Sales Representative: **{user['full_name']}** | Code: `{user.get('emp_code', 'N/A')}` | Role: `{user.get('account_type')}`"
    )

    is_management = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]

    t_create, t_history = st.tabs(["➕ Create New Jobsheet", "📋 Order History & Modifications"])

    # --- TAB 1: CREATE NEW JOBSHEET ---
    with t_create:
        suggested_no = get_next_job_no()

        if "sales_items" not in st.session_state:
            st.session_state.sales_items = [{
                "item_name": "",
                "length": 1.0,
                "breadth": 1.0,
                "height": 1.0,
                "dim_unit": "Inch",
                "calc_mode": "By Rate",
                "quantity": 0.0,
                "rate": 0.0,
                "amount": 0.0,
                "specifications": "",
                "delivery_address": "",
            }]
        else:
            for itm in st.session_state.sales_items:
                if itm.get("dim_unit") not in ["Inch", "Ft"]:
                    itm["dim_unit"] = "Inch"
                if "calc_mode" not in itm:
                    itm["calc_mode"] = "By Rate"

        with st.container(border=True):
            st.markdown("#### 1. Client & Commercial Header")
            c1, c2, c3 = st.columns(3)
            with c1:
                job_no = st.text_input("Jobsheet Number *", value=suggested_no, key="s_job_no").strip()
                client_name = st.text_input("Client / Corporate Entity *", placeholder="e.g. Apollo Hospitals", key="s_client").strip()
            with c2:
                contact_person = st.text_input("Contact Person *", placeholder="e.g. Amitava Ghosh", key="s_contact").strip()
                contact_phone = st.text_input("Mobile / Contact Number *", placeholder="e.g. 9830112233", key="s_phone").strip()
            with c3:
                due_date = st.date_input("Target Delivery Date *", min_value=date.today(), key="s_due")
                routed_desk = st.selectbox(
                    "Routing Workflow Target *",
                    options=["DESIGN", "PAYMENT", "PRODUCTION"],
                    format_func=lambda x: {
                        "DESIGN": "🎨 Send to Design & Proofs",
                        "PAYMENT": "💳 Direct to Accounts / Advance",
                        "PRODUCTION": "⚙️ Skip to Production Floor",
                    }.get(x, x),
                    key="s_route",
                )

        st.markdown("---")
        st.markdown("#### 2. Commercial Line Items & Specs")

        btn_col1, _ = st.columns([1, 4])
        with btn_col1:
            if st.button("➕ Add Item Row", use_container_width=True):
                st.session_state.sales_items.append({
                    "item_name": "",
                    "length": 1.0,
                    "breadth": 1.0,
                    "height": 1.0,
                    "dim_unit": "Inch",
                    "calc_mode": "By Rate",
                    "quantity": 0.0,
                    "rate": 0.0,
                    "amount": 0.0,
                    "specifications": "",
                    "delivery_address": "",
                })
                st.rerun()

        rows_to_remove = []
        for idx, item in enumerate(st.session_state.sales_items):
            with st.container(border=True):
                # Header Row: Item Name & Delete Button
                top_c1, top_c2 = st.columns([5.5, 0.5])
                with top_c1:
                    item["item_name"] = st.text_input(
                        f"Item Name #{idx+1} *",
                        value=item.get("item_name", ""),
                        placeholder="e.g. Backlit Flex Signboard",
                        key=f"item_name_{idx}",
                    )
                with top_c2:
                    if len(st.session_state.sales_items) > 1:
                        if st.button("🗑️", key=f"del_row_{idx}"):
                            rows_to_remove.append(idx)

                # Row 1: Dimensions (Length, Breadth, Height & Unit)
                st.caption("📐 **Sizes / Dimensions** (Default: 1 × 1 × 1):")
                s_c1, s_c2, s_c3, s_c4 = st.columns(4)
                with s_c1:
                    item["length"] = st.number_input(
                        "Length (L)",
                        min_value=0.0,
                        value=float(item.get("length", 1.0)),
                        step=1.0,
                        key=f"item_len_{idx}",
                    )
                with s_c2:
                    item["breadth"] = st.number_input(
                        "Breadth / Width (B)",
                        min_value=0.0,
                        value=float(item.get("breadth", 1.0)),
                        step=1.0,
                        key=f"item_brd_{idx}",
                    )
                with s_c3:
                    item["height"] = st.number_input(
                        "Height / Depth (H)",
                        min_value=0.0,
                        value=float(item.get("height", 1.0)),
                        step=0.5,
                        key=f"item_hgt_{idx}",
                    )
                with s_c4:
                    unit_options = ["Inch", "Ft"]
                    cur_u = item.get("dim_unit", "Inch")
                    u_idx = unit_options.index(cur_u) if cur_u in unit_options else 0
                    item["dim_unit"] = st.selectbox(
                        "Size Unit",
                        unit_options,
                        index=u_idx,
                        key=f"item_dunit_{idx}",
                    )

                # Row 2: Pricing Option Toggle & Commercials
                calc_mode = st.radio(
                    "Calculation Method:",
                    ["Enter Rate (Calculate Amount)", "Enter Total Amount (Calculate Rate)"],
                    index=0 if item.get("calc_mode") == "By Rate" else 1,
                    horizontal=True,
                    key=f"calc_mode_{idx}",
                )
                item["calc_mode"] = "By Rate" if "Enter Rate" in calc_mode else "By Amount"

                l_val = item["length"] if item["length"] > 0 else 1.0
                b_val = item["breadth"] if item["breadth"] > 0 else 1.0
                h_val = item["height"] if item["height"] > 0 else 1.0
                dim_multiplier = l_val * b_val * h_val

                r_c1, r_c2, r_c3 = st.columns([1.5, 1.5, 2])
                with r_c1:
                    item["quantity"] = st.number_input(
                        "Quantity",
                        min_value=0.0,
                        value=float(item.get("quantity", 0.0)),
                        step=1.0,
                        key=f"item_qty_{idx}",
                    )

                if item["calc_mode"] == "By Rate":
                    with r_c2:
                        item["rate"] = st.number_input(
                            "Rate (₹)",
                            min_value=0.0,
                            value=float(item.get("rate", 0.0)),
                            step=10.0,
                            key=f"item_rate_{idx}",
                        )
                    with r_c3:
                        item["amount"] = round(dim_multiplier * item["quantity"] * item["rate"], 2)
                        st.metric("Total Line Amount", f"₹ {item['amount']:,.2f}")
                else:
                    with r_c2:
                        item["amount"] = st.number_input(
                            "Total Amount (₹)",
                            min_value=0.0,
                            value=float(item.get("amount", 0.0)),
                            step=50.0,
                            key=f"item_amt_in_{idx}",
                        )
                    with r_c3:
                        divisor = dim_multiplier * item["quantity"]
                        if divisor > 0:
                            item["rate"] = round(item["amount"] / divisor, 2)
                        else:
                            item["rate"] = 0.0
                        st.metric("Calculated Rate", f"₹ {item['rate']:,.2f} / unit")

                # Row 3: Specifications and Delivery Address
                d_c1, d_c2 = st.columns(2)
                with d_c1:
                    item["specifications"] = st.text_input(
                        "Technical Specifications / Material Notes",
                        value=item.get("specifications", ""),
                        placeholder="e.g. 5mm Clear Acrylic, 3M vinyl, LED modules",
                        key=f"item_spec_{idx}",
                    )
                with d_c2:
                    item["delivery_address"] = st.text_input(
                        "Delivery Address / Branch Location",
                        value=item.get("delivery_address", ""),
                        placeholder="e.g. Salt Lake Sector V Office",
                        key=f"item_addr_{idx}",
                    )

        if rows_to_remove:
            for r_idx in sorted(rows_to_remove, reverse=True):
                st.session_state.sales_items.pop(r_idx)
            st.rerun()

        grand_total = sum(it["amount"] for it in st.session_state.sales_items)
        st.markdown(f"### Grand Total Order Value: `₹ {grand_total:,.2f}`")

        if st.button("🚀 Submit & Dispatch Jobsheet", type="primary", use_container_width=True):
            if not (job_no and client_name and contact_person and contact_phone):
                st.error("Please fill in all required header fields (Job #, Client Name, Contact Person, and Phone).")
            elif any(not it["item_name"].strip() for it in st.session_state.sales_items):
                st.error("Please ensure every added line item has a valid name.")
            else:
                header_payload = {
                    "job_no": job_no,
                    "client_name": client_name,
                    "contact_person": contact_person,
                    "contact_phone": contact_phone,
                    "due_date": str(due_date),
                    "order_taken_by": user["full_name"],
                    "current_stage": routed_desk,
                    "is_returned": False,
                    "billing_type": "NON_GST",
                    "is_billed": False,
                }

                prepared_items = []
                for it in st.session_state.sales_items:
                    size_str = f"Size: {it.get('length', 1.0)} x {it.get('breadth', 1.0)} x {it.get('height', 1.0)} {it.get('dim_unit', 'Inch')}"
                    full_spec = it.get("specifications", "").strip()
                    if size_str:
                        full_spec = f"{size_str} | {full_spec}" if full_spec else size_str

                    prepared_items.append({
                        "item_name": it["item_name"].strip(),
                        "specifications": full_spec,
                        "quantity": it["quantity"],
                        "unit": "Pcs",
                        "rate": it["rate"],
                        "amount": it["amount"],
                        "delivery_address": it.get("delivery_address", "").strip(),
                    })

                ok, msg = create_job_sheet(header_payload, prepared_items)
                if ok:
                    try:
                        from email_service import send_new_jobsheet_alert
                        send_new_jobsheet_alert(header_payload, prepared_items)
                    except Exception:
                        pass

                    st.success(f"Job Sheet #{job_no} created successfully and routed to `{routed_desk}`!")
                    st.session_state.sales_items = [{
                        "item_name": "",
                        "length": 1.0,
                        "breadth": 1.0,
                        "height": 1.0,
                        "dim_unit": "Inch",
                        "calc_mode": "By Rate",
                        "quantity": 0.0,
                        "rate": 0.0,
                        "amount": 0.0,
                        "specifications": "",
                        "delivery_address": "",
                    }]
                    st.rerun()
                else:
                    st.error(f"Failed to create jobsheet: {msg}")

    # --- TAB 2: ORDER HISTORY & MANAGEMENT EDIT ---
    with t_history:
        my_jobs = get_user_created_jobs(user["full_name"], is_management=is_management)

        if not my_jobs:
            st.info("No orders found recorded.")
        else:
            for j in my_jobs:
                items = get_job_items(j["job_id"])
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 2, 1.5])
                    with c1:
                        st.markdown(f"**Job #{j.get('job_no')} — {j.get('client_name')}**")
                        st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                        st.caption(f"Due: `{j.get('due_date')}` | Stage: `{j.get('current_stage')}`")
                        st.caption(f"Created by: `{j.get('order_taken_by', 'N/A')}`")
                    with c2:
                        st.markdown(f"**Value:** ₹ {total_val:,.2f}")
                        for it in items:
                            st.caption(f"• {it.get('item_name')} ({it.get('quantity')} {it.get('unit')}) — ₹{float(it.get('amount', 0)):,.2f}")
                    with c3:
                        if j.get("is_returned"):
                            st.error(f"⚠️ Return: {j.get('return_reason')}")
                        else:
                            st.info(f"Desk: {j.get('current_stage')}")

                        if is_management:
                            with st.popover("✏️ Edit Jobsheet", use_container_width=True):
                                st.markdown(f"**Modify Job #{j.get('job_no')}**")
                                ed_client = st.text_input("Client Name", value=j.get("client_name", ""), key=f"ed_cl_{j['job_id']}")
                                ed_contact = st.text_input("Contact Person", value=j.get("contact_person", ""), key=f"ed_cp_{j['job_id']}")
                                ed_phone = st.text_input("Contact Phone", value=j.get("contact_phone", ""), key=f"ed_ph_{j['job_id']}")

                                cur_due = date.today()
                                if j.get("due_date"):
                                    try:
                                        cur_due = datetime.strptime(str(j.get("due_date")), "%Y-%m-%d").date()
                                    except Exception:
                                        cur_due = date.today()
                                ed_due = st.date_input("Target Due Date", value=cur_due, key=f"ed_due_{j['job_id']}")

                                stage_list = ["DESIGN", "PAYMENT", "PRODUCTION", "QC", "DISPATCH", "BILLING", "SETTLED"]
                                cur_st_idx = stage_list.index(j.get("current_stage")) if j.get("current_stage") in stage_list else 0
                                ed_stage = st.selectbox("Stage Desk", stage_list, index=cur_st_idx, key=f"ed_stg_{j['job_id']}")

                                st.markdown("---")
                                st.markdown("##### Line Items")
                                edited_items = []
                                for idx, it in enumerate(items):
                                    st.caption(f"Item #{idx+1}")
                                    ei_name = st.text_input("Item Name", value=it.get("item_name", ""), key=f"ei_nm_{j['job_id']}_{idx}")
                                    ei_spec = st.text_input("Specs / Dimensions", value=it.get("specifications", ""), key=f"ei_sp_{j['job_id']}_{idx}")
                                    ei_qty = st.number_input("Qty", value=float(it.get("quantity", 1)), min_value=0.01, step=1.0, key=f"ei_q_{j['job_id']}_{idx}")
                                    ei_rate = st.number_input("Rate (₹)", value=float(it.get("rate", 0)), min_value=0.0, step=10.0, key=f"ei_r_{j['job_id']}_{idx}")
                                    ei_amt = round(ei_qty * ei_rate, 2)
                                    st.write(f"Line Total: **₹ {ei_amt:,.2f}**")
                                    edited_items.append({
                                        "item_name": ei_name.strip(),
                                        "specifications": ei_spec.strip(),
                                        "quantity": ei_qty,
                                        "unit": it.get("unit", "Pcs"),
                                        "rate": ei_rate,
                                        "amount": ei_amt,
                                        "delivery_address": it.get("delivery_address", "")
                                    })

                                if st.button("Save Changes", key=f"btn_save_job_{j['job_id']}", type="primary", use_container_width=True):
                                    h_payload = {
                                        "client_name": ed_client,
                                        "contact_person": ed_contact,
                                        "contact_phone": ed_phone,
                                        "due_date": str(ed_due),
                                        "current_stage": ed_stage
                                    }
                                    ok, upd_msg = update_job_sheet_by_management(j["job_id"], h_payload, edited_items)
                                    if ok:
                                        st.success("Jobsheet updated successfully.")
                                        st.rerun()
                                    else:
                                        st.error(f"Update failed: {upd_msg}")