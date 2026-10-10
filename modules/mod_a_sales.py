from datetime import date, datetime
import streamlit as st
from database import (
    create_job_sheet,
    get_job_items,
    get_next_job_no,
    get_user_created_jobs,
    update_job_sheet_by_management,
    request_job_deletion,
    get_all_designers,
)


def _sync_commercials(idx, trigger_field):
    item = st.session_state.sales_items[idx]
    qty = float(st.session_state.get(f"item_qty_{idx}", item["quantity"]))
    rate = float(st.session_state.get(f"item_rate_{idx}", item["rate"]))
    amount = float(st.session_state.get(f"item_amt_{idx}", item["amount"]))

    l_val = item["length"] if item["length"] > 0 else 1.0
    b_val = item["breadth"] if item["breadth"] > 0 else 1.0
    h_val = item["height"] if item["height"] > 0 else 1.0
    dim_factor = l_val * b_val * h_val

    if trigger_field in ["qty", "rate"]:
        new_amt = round(dim_factor * qty * rate, 2)
        st.session_state[f"item_amt_{idx}"] = new_amt
        item["quantity"] = qty
        item["rate"] = rate
        item["amount"] = new_amt

    elif trigger_field == "amount":
        item["amount"] = amount
        if qty > 0 and dim_factor > 0:
            new_rate = round(amount / (dim_factor * qty), 2)
            st.session_state[f"item_rate_{idx}"] = new_rate
            item["rate"] = new_rate
            item["quantity"] = qty
        elif rate > 0 and dim_factor > 0:
            new_qty = round(amount / (dim_factor * rate), 2)
            st.session_state[f"item_qty_{idx}"] = new_qty
            item["quantity"] = new_qty
            item["rate"] = rate


def _recalc_on_dim_change(idx):
    item = st.session_state.sales_items[idx]
    item["length"] = float(st.session_state.get(f"item_len_{idx}", item["length"]))
    item["breadth"] = float(st.session_state.get(f"item_brd_{idx}", item["breadth"]))
    item["height"] = float(st.session_state.get(f"item_hgt_{idx}", item["height"]))
    _sync_commercials(idx, "rate")


def render(user):
    st.subheader("📝 Module 1: Order Intake & Commercial Jobsheet Creation")
    st.caption(
        f"Sales Representative: **{user['full_name']}** | Code: `{user.get('emp_code', 'N/A')}` | Role: `{user.get('account_type')}`"
    )

    user_perms = user.get("permissions") or []
    is_management = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]
    can_edit_jobsheets = is_management or ("CAN_EDIT_JOBS" in user_perms)

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

        with st.container(border=True):
            st.markdown("#### 1. Client & Commercial Header")
            
            # Side-by-side selection for Billing Type
            billing_choice = st.radio(
                "Billing Classification *",
                options=["Non-GST Bill", "GST Invoice (B2B Tax Invoice)"],
                index=0,
                horizontal=True,
                key="s_billing_mode"
            )
            is_gst = "GST Invoice" in billing_choice

            c1, c2, c3 = st.columns(3)
            with c1:
                job_no = st.text_input("Jobsheet Number *", value=suggested_no, key="s_job_no").strip()
                client_name = st.text_input("Client / Corporate Entity *", placeholder="e.g. Apollo Hospitals", key="s_client").strip()
            with c2:
                contact_person = st.text_input("Contact Person", placeholder="e.g. Amitava Ghosh", key="s_contact").strip()
                contact_phone = st.text_input("Mobile / Contact Number", placeholder="e.g. 9830112233", key="s_phone").strip()
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

            # Conditional GST Compliance Details
            gstin = ""
            billing_address = ""
            place_of_supply = "19 - West Bengal"

            if is_gst:
                st.markdown("##### 🏛️ GST Compliance Information")
                gc1, gc2, gc3 = st.columns([1.5, 1.5, 3])
                with gc1:
                    gstin = st.text_input("Client GSTIN *", placeholder="e.g. 19AAAAA0000A1Z5", key="s_gstin").strip().upper()
                with gc2:
                    place_of_supply = st.selectbox(
                        "Place of Supply (State) *",
                        options=[
                            "19 - West Bengal",
                            "10 - Bihar",
                            "20 - Jharkhand",
                            "21 - Odisha",
                            "18 - Assam",
                            "07 - Delhi",
                            "27 - Maharashtra",
                            "Other State"
                        ],
                        key="s_pos"
                    )
                with gc3:
                    billing_address = st.text_input("Registered GST Billing Address *", placeholder="e.g. 12/A Park Street, Kolkata - 700016", key="s_baddr").strip()

            # Designer Assignment option if routed to DESIGN
            target_designer = "OPEN_POOL"
            if routed_desk == "DESIGN":
                designers_list = get_all_designers()
                des_options = ["📢 Broadcast to All Designers (Open Claim)"] + [f"{d['full_name']} (@{d['username']})" for d in designers_list]
                chosen = st.selectbox("Assign Designer *", options=des_options, key="s_des_choice")
                if "📢" not in chosen:
                    target_designer = chosen.split(" (@")[0].strip()

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

                # Dimensions
                st.caption("📐 **Sizes / Dimensions** (Default: 1 × 1 × 1):")
                s_c1, s_c2, s_c3, s_c4 = st.columns(4)
                with s_c1:
                    item["length"] = st.number_input(
                        "Length (L)",
                        min_value=0.0,
                        value=float(item.get("length", 1.0)),
                        step=1.0,
                        key=f"item_len_{idx}",
                        on_change=_recalc_on_dim_change,
                        args=(idx,),
                    )
                with s_c2:
                    item["breadth"] = st.number_input(
                        "Breadth / Width (B)",
                        min_value=0.0,
                        value=float(item.get("breadth", 1.0)),
                        step=1.0,
                        key=f"item_brd_{idx}",
                        on_change=_recalc_on_dim_change,
                        args=(idx,),
                    )
                with s_c3:
                    item["height"] = st.number_input(
                        "Height / Depth (H)",
                        min_value=0.0,
                        value=float(item.get("height", 1.0)),
                        step=0.5,
                        key=f"item_hgt_{idx}",
                        on_change=_recalc_on_dim_change,
                        args=(idx,),
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

                st.caption("💰 **Commercials** (Fill any 2 fields to auto-calculate the 3rd):")
                r_c1, r_c2, r_c3 = st.columns(3)
                with r_c1:
                    item["quantity"] = st.number_input(
                        "Quantity",
                        min_value=0.0,
                        value=float(item.get("quantity", 0.0)),
                        step=1.0,
                        key=f"item_qty_{idx}",
                        on_change=_sync_commercials,
                        args=(idx, "qty"),
                    )
                with r_c2:
                    item["rate"] = st.number_input(
                        "Rate (₹)",
                        min_value=0.0,
                        value=float(item.get("rate", 0.0)),
                        step=10.0,
                        key=f"item_rate_{idx}",
                        on_change=_sync_commercials,
                        args=(idx, "rate"),
                    )
                with r_c3:
                    item["amount"] = st.number_input(
                        "Total Amount (₹)",
                        min_value=0.0,
                        value=float(item.get("amount", 0.0)),
                        step=50.0,
                        key=f"item_amt_{idx}",
                        on_change=_sync_commercials,
                        args=(idx, "amount"),
                    )

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

        grand_total = sum(float(it.get("amount", 0.0)) for it in st.session_state.sales_items)
        st.markdown(f"### Grand Total Order Value: `₹ {grand_total:,.2f}`")

        if st.button("🚀 Submit & Dispatch Jobsheet", type="primary", use_container_width=True):
            # Normalize and auto-fallback optional contact info
            j_no = str(job_no).strip() if job_no else ""
            c_name = str(client_name).strip() if client_name else ""
            c_person = str(contact_person).strip() if contact_person else "Direct Client"
            c_phone = str(contact_phone).strip() if contact_phone else "N/A"

            if not j_no or not c_name:
                missing = []
                if not j_no:
                    missing.append("Jobsheet Number")
                if not c_name:
                    missing.append("Client / Corporate Entity")
                st.error(f"Please fill in mandatory field(s): {', '.join(missing)}")
            elif is_gst and (not gstin or len(gstin) < 15):
                st.error("Please provide a valid 15-character GSTIN for GST Tax Invoices.")
            elif is_gst and not billing_address:
                st.error("Registered Billing Address is required for GST Tax Invoices.")
            elif any(not it.get("item_name", "").strip() for it in st.session_state.sales_items):
                st.error("Please ensure every added line item has a valid name.")
            else:
                header_payload = {
                    "job_no": j_no,
                    "client_name": c_name,
                    "contact_person": c_person,
                    "contact_phone": c_phone,
                    "due_date": str(due_date),
                    "order_taken_by": user["full_name"],
                    "current_stage": routed_desk,
                    "assigned_designer": target_designer if routed_desk == "DESIGN" else None,
                    "is_returned": False,
                    "billing_type": "GST" if is_gst else "NON_GST",
                    "gstin": gstin if is_gst else None,
                    "billing_address": billing_address if is_gst else None,
                    "place_of_supply": place_of_supply if is_gst else None,
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

                    des_msg = f" (Assigned to: `{target_designer}`)" if routed_desk == "DESIGN" else ""
                    st.success(f"Job Sheet #{job_no} created successfully and routed to `{routed_desk}`{des_msg}!")
                    st.session_state.sales_items = [{
                        "item_name": "",
                        "length": 1.0,
                        "breadth": 1.0,
                        "height": 1.0,
                        "dim_unit": "Inch",
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

        # --- DYNAMIC SEARCHABLE DROPDOWN FILTER BAR ---
        with st.container(border=True):
            st.markdown("#### 🔍 Filter & Search Orders")
            
            # CSS safeguard to ensure selectbox dropdowns and labels render visibly
            st.markdown("""
                <style>
                div[data-baseweb="select"] {
                    background-color: #161B22 !important;
                    border-radius: 6px !important;
                }
                div[data-baseweb="select"] * {
                    color: #FFFFFF !important;
                }
                </style>
            """, unsafe_allow_html=True)

            jobs_source = my_jobs or []

            # Populate distinct options
            opt_job_nos = ["All"] + sorted(list({str(j.get("job_no")) for j in jobs_source if j.get("job_no")}))
            opt_clients = ["All"] + sorted(list({str(j.get("client_name")).strip() for j in jobs_source if j.get("client_name")}))
            opt_contacts = ["All"] + sorted(list({str(j.get("contact_person")).strip() for j in jobs_source if j.get("contact_person")}))
            opt_phones = ["All"] + sorted(list({str(j.get("contact_phone")).strip() for j in jobs_source if j.get("contact_phone")}))
            opt_due_dates = ["All"] + sorted(list({str(j.get("due_date")) for j in jobs_source if j.get("due_date")}))
            opt_depts = ["All Departments", "DESIGN", "PAYMENT", "PRODUCTION", "QC", "DISPATCH", "BILLING", "SETTLED"]
            opt_designers = ["All"] + sorted(list({str(j.get("assigned_designer")).strip() for j in jobs_source if j.get("assigned_designer")}))

            sf_c1, sf_c2, sf_c3 = st.columns(3)
            with sf_c1:
                f_job_no = st.selectbox("Jobsheet Number", options=opt_job_nos, index=0, key="sf_drp_jno")
                f_client = st.selectbox("Client / Corporate Entity", options=opt_clients, index=0, key="sf_drp_cli")
                f_due_date = st.selectbox("Target Delivery Date", options=opt_due_dates, index=0, key="sf_drp_due")

            with sf_c2:
                f_contact = st.selectbox("Contact Person", options=opt_contacts, index=0, key="sf_drp_cnt")
                f_phone = st.selectbox("Mobile / Contact Number", options=opt_phones, index=0, key="sf_drp_phn")

            with sf_c3:
                f_dept = st.selectbox("Currently in Department", options=opt_depts, index=0, key="sf_drp_dpt")
                f_designer = st.selectbox("Assigned Designer", options=opt_designers, index=0, key="sf_drp_dsg")

            # Reset Button
            if st.button("🔄 Reset Filters", type="secondary", key="btn_rst_sf"):
                for k in ["sf_drp_jno", "sf_drp_cli", "sf_drp_due", "sf_drp_cnt", "sf_drp_phn", "sf_drp_dpt", "sf_drp_dsg"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

        # Apply Filters
        filtered_my_jobs = []
        for j in (my_jobs or []):
            if f_job_no != "All" and str(j.get("job_no")) != f_job_no:
                continue
            if f_client != "All" and str(j.get("client_name", "")).strip() != f_client:
                continue
            if f_contact != "All" and str(j.get("contact_person", "")).strip() != f_contact:
                continue
            if f_phone != "All" and str(j.get("contact_phone", "")).strip() != f_phone:
                continue
            if f_due_date != "All" and str(j.get("due_date", "")) != f_due_date:
                continue
            if f_dept != "All Departments" and j.get("current_stage") != f_dept:
                continue
            if f_designer != "All" and str(j.get("assigned_designer", "")).strip() != f_designer:
                continue
            filtered_my_jobs.append(j)

        st.caption(f"Showing **{len(filtered_my_jobs)}** matching order(s):")
        st.markdown("---")

        if not filtered_my_jobs:
            st.info("No matching orders found.")
        else:
            for j in filtered_my_jobs:
                items = get_job_items(j["job_id"])
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2.5, 2, 1.5])
                    with c1:
                        btype_badge = "🏛️ GST" if j.get("billing_type") == "GST" else "📄 Non-GST"
                        st.markdown(f"**Job #{j.get('job_no')} — {j.get('client_name')}** ({btype_badge})")
                        st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                        st.caption(f"Due: `{j.get('due_date')}` | Stage: `{j.get('current_stage')}`")
                        des_label = j.get("assigned_designer") or "None"
                        st.caption(f"Designer: `{des_label}` | Booked by: `{j.get('order_taken_by', 'N/A')}`")
                    with c2:
                        st.markdown(f"**Value:** ₹ {total_val:,.2f}")
                        for it in items:
                            st.caption(f"• {it.get('item_name')} ({it.get('quantity')} {it.get('unit')}) — ₹{float(it.get('amount', 0)):,.2f}")
                    with c3:
                        is_del_req = (j.get("return_reason") or "").startswith("[DELETION_REQ]")

                        if is_del_req:
                            st.warning("⏳ Deletion Pending Approval")
                        elif j.get("is_returned"):
                            st.error(f"⚠️ Return: {j.get('return_reason')}")
                        else:
                            st.info(f"Desk: {j.get('current_stage')}")

                        if can_edit_jobsheets:
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

                                # Option to reassign designer
                                designers_all = get_all_designers()
                                d_names = ["OPEN_POOL"] + [d["full_name"] for d in designers_all]
                                cur_des = j.get("assigned_designer") or "OPEN_POOL"
                                d_idx = d_names.index(cur_des) if cur_des in d_names else 0
                                ed_designer = st.selectbox("Assigned Designer", options=d_names, index=d_idx, key=f"ed_des_{j['job_id']}")

                                # Edit GST details
                                is_currently_gst = j.get("billing_type") == "GST"
                                ed_is_gst = st.checkbox("GST Tax Invoice Billing", value=is_currently_gst, key=f"ed_isgst_{j['job_id']}")
                                ed_gstin = j.get("gstin", "") or ""
                                ed_baddr = j.get("billing_address", "") or ""
                                ed_pos = j.get("place_of_supply", "19 - West Bengal") or "19 - West Bengal"

                                if ed_is_gst:
                                    ed_gstin = st.text_input("Client GSTIN", value=ed_gstin, key=f"ed_gstin_{j['job_id']}").strip().upper()
                                    ed_baddr = st.text_input("Billing Address", value=ed_baddr, key=f"ed_baddr_{j['job_id']}").strip()
                                    pos_opts = ["19 - West Bengal", "10 - Bihar", "20 - Jharkhand", "21 - Odisha", "18 - Assam", "07 - Delhi", "27 - Maharashtra", "Other State"]
                                    pos_idx = pos_opts.index(ed_pos) if ed_pos in pos_opts else 0
                                    ed_pos = st.selectbox("Place of Supply", pos_opts, index=pos_idx, key=f"ed_pos_{j['job_id']}")

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
                                        "current_stage": ed_stage,
                                        "assigned_designer": ed_designer,
                                        "billing_type": "GST" if ed_is_gst else "NON_GST",
                                        "gstin": ed_gstin if ed_is_gst else None,
                                        "billing_address": ed_baddr if ed_is_gst else None,
                                        "place_of_supply": ed_pos if ed_is_gst else None,
                                    }
                                    ok, upd_msg = update_job_sheet_by_management(j["job_id"], h_payload, edited_items)
                                    if ok:
                                        st.success("Jobsheet updated successfully.")
                                        st.rerun()
                                    else:
                                        st.error(f"Update failed: {upd_msg}")

                        if is_del_req:
                            st.caption("Request is awaiting review in Executive Overview.")
                        else:
                            with st.popover("🗑️ Request Deletion", use_container_width=True):
                                st.caption("Submit deletion request to CEO / Admin for approval.")
                                del_reason = st.text_input(
                                    "Reason for Deletion *", 
                                    placeholder="e.g. Client cancelled order", 
                                    key=f"req_del_r_{j['job_id']}"
                                )
                                if st.button("Submit Request", key=f"btn_req_del_{j['job_id']}", type="primary", use_container_width=True):
                                    if not del_reason.strip():
                                        st.error("Please provide a reason.")
                                    else:
                                        ok, msg = request_job_deletion(j["job_id"], user["full_name"], del_reason)
                                        if ok:
                                            st.success(msg)
                                            st.rerun()
                                        else:
                                            st.error(msg)