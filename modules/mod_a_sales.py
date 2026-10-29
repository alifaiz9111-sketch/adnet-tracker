import uuid
from datetime import date, datetime
import streamlit as st
from database import (
    create_job_sheet,
    get_job_items,
    get_next_job_no,
    get_user_created_jobs,
    update_job_sheet_by_management,
    delete_job_sheet,
    request_job_deletion,
    get_all_designers,
    log_audit,
    flash,
)


def _make_empty_item():
    return {
        "uid": uuid.uuid4().hex[:8],
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
    }


def _sync_commercials(uid, trigger_field):
    item = next((i for i in st.session_state.sales_items if i["uid"] == uid), None)
    if not item:
        return

    qty = float(st.session_state.get(f"item_qty_{uid}", item["quantity"]))
    rate = float(st.session_state.get(f"item_rate_{uid}", item["rate"]))
    amount = float(st.session_state.get(f"item_amt_{uid}", item["amount"]))

    l_val = item["length"] if item["length"] > 0 else 1.0
    b_val = item["breadth"] if item["breadth"] > 0 else 1.0
    h_val = item["height"] if item["height"] > 0 else 1.0
    dim_factor = l_val * b_val * h_val

    if trigger_field in ["qty", "rate"]:
        new_amt = round(dim_factor * qty * rate, 2)
        st.session_state[f"item_amt_{uid}"] = new_amt
        item["quantity"] = qty
        item["rate"] = rate
        item["amount"] = new_amt
    elif trigger_field == "amount":
        item["amount"] = amount
        if qty > 0 and dim_factor > 0:
            new_rate = round(amount / (dim_factor * qty), 2)
            st.session_state[f"item_rate_{uid}"] = new_rate
            item["rate"] = new_rate
            item["quantity"] = qty
        elif rate > 0 and dim_factor > 0:
            new_qty = round(amount / (dim_factor * rate), 2)
            st.session_state[f"item_qty_{uid}"] = new_qty
            item["quantity"] = new_qty
            item["rate"] = rate


def _recalc_on_dim_change(uid):
    item = next((i for i in st.session_state.sales_items if i["uid"] == uid), None)
    if not item:
        return
    item["length"] = float(st.session_state.get(f"item_len_{uid}", item["length"]))
    item["breadth"] = float(st.session_state.get(f"item_brd_{uid}", item["breadth"]))
    item["height"] = float(st.session_state.get(f"item_hgt_{uid}", item["height"]))
    _sync_commercials(uid, "rate")


def render(user):
    st.subheader("Module 1: Order Intake & Commercial Jobsheet Creation")
    st.caption(
        f"Sales Representative: **{user['full_name']}** | Code: `{user.get('emp_code', 'N/A')}` | Role: `{user.get('account_type')}`"
    )

    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions") or []
    is_management = account_type in ["SUPER_ADMIN", "CEO", "MANAGER"]
    can_edit_jobs = is_management or ("CAN_EDIT_JOBS" in user_perms)

    t_create, t_history = st.tabs(["Create New Jobsheet", "Order History & Modifications"])

    # =========================================================
    # TAB 1: CREATE NEW JOBSHEET
    # =========================================================
    with t_create:
        if "sales_items" not in st.session_state or not st.session_state.sales_items:
            st.session_state.sales_items = [_make_empty_item()]

        suggested_no = get_next_job_no()
        if "s_manual_job_no" not in st.session_state:
            st.session_state["s_manual_job_no"] = str(suggested_no)

        st.markdown("### Jobsheet Creation Form")

        with st.container(border=True):
            st.markdown("#### 1. Client & Commercial Header")
            r1_c1, r1_c2 = st.columns([6, 4])
            with r1_c1:
                billing_choice = st.radio(
                    "Billing Classification *",
                    options=["Non-GST Bill", "GST Invoice (B2B Tax Invoice)"],
                    index=0,
                    horizontal=True,
                    key="s_billing_mode"
                )
                is_gst = "GST Invoice" in billing_choice
            with r1_c2:
                st.text_input("Jobsheet Number *", key="s_manual_job_no", placeholder="e.g. 1081")

            r2_c1, r2_c2, r2_c3 = st.columns([6, 2, 2])
            with r2_c1:
                billing_address = st.text_input(
                    "Billing Address" + (" *" if is_gst else " (Optional)"),
                    placeholder="e.g. Park Street, Kolkata",
                    key="s_baddr"
                ).strip()
            with r2_c2:
                due_date = st.date_input("Target Delivery Date *", min_value=date.today(), key="s_due")
            with r2_c3:
                routed_desk = st.selectbox(
                    "Routing Workflow Target *",
                    options=["DESIGN", "PAYMENT", "PRODUCTION"],
                    format_func=lambda x: {
                        "DESIGN": "Send to Design & Proofs",
                        "PAYMENT": "Direct to Accounts / Advance",
                        "PRODUCTION": "Skip to Production Floor",
                    }.get(x, x),
                    key="s_route",
                )

            r3_c1, r3_c2, r3_c3, r3_c4 = st.columns([2.5, 2.5, 2.5, 2.5])
            with r3_c1:
                client_name = st.text_input("Client / Corporate Entity *", placeholder="e.g. Apollo Hospitals", key="s_client").strip()
            with r3_c2:
                contact_person = st.text_input("Contact Person", placeholder="e.g. Amitava Ghosh", key="s_contact").strip()
            with r3_c3:
                contact_phone = st.text_input("Mobile / Contact Number", placeholder="e.g. 9830112233", key="s_phone").strip()
            with r3_c4:
                target_designer = "OPEN_POOL"
                designers_list = get_all_designers()
                des_options = ["Broadcast to All Designers (Open Claim)"] + [
                    f"{d['full_name']} (@{d['username']})" for d in designers_list
                ]
                chosen = st.selectbox("Assign Designer *", options=des_options, key="s_des_choice")
                if "Broadcast" not in chosen:
                    target_designer = chosen.split(" (@")[0].strip()

            gstin = ""
            place_of_supply = "19 - West Bengal"
            if is_gst:
                st.markdown("##### GST Compliance Information")
                gc1, gc2 = st.columns([1, 1])
                with gc1:
                    gstin = st.text_input("Client GSTIN *", placeholder="e.g. 19AAAAA0000A1Z5", key="s_gstin").strip().upper()
                with gc2:
                    place_of_supply = st.selectbox(
                        "Place of Supply (State) *",
                        options=[
                            "19 - West Bengal", "10 - Bihar", "20 - Jharkhand",
                            "21 - Odisha", "18 - Assam", "07 - Delhi", "27 - Maharashtra", "Other State"
                        ],
                        key="s_pos"
                    )

        with st.container(border=True):
            head_c1, head_c2 = st.columns([7, 3])
            with head_c1:
                st.markdown("#### 2. Commercial Line Items & Specs")
            with head_c2:
                if st.button("+ Add Item Row", key="btn_add_item_top", use_container_width=True):
                    st.session_state.sales_items.append(_make_empty_item())
                    st.rerun()

            uids_to_remove = []
            for idx, item in enumerate(st.session_state.sales_items):
                u = item["uid"]
                with st.container(border=True):
                    top_c1, top_c2 = st.columns([9.2, 0.8])
                    with top_c1:
                        item["item_name"] = st.text_input(
                            f"Item Name #{idx+1} *",
                            value=item.get("item_name", ""),
                            placeholder="e.g. Backlit Flex Signboard",
                            key=f"item_name_{u}",
                        )
                    with top_c2:
                        if len(st.session_state.sales_items) > 1:
                            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                            if st.button("X", key=f"del_row_{u}", help="Remove Item"):
                                uids_to_remove.append(u)

                    s_c1, s_c2, s_c3, s_c4 = st.columns(4)
                    with s_c1:
                        item["length"] = st.number_input("Length (L)", min_value=0.0, value=float(item.get("length", 1.0)), step=1.0, key=f"item_len_{u}", on_change=_recalc_on_dim_change, args=(u,))
                    with s_c2:
                        item["breadth"] = st.number_input("Breadth (B)", min_value=0.0, value=float(item.get("breadth", 1.0)), step=1.0, key=f"item_brd_{u}", on_change=_recalc_on_dim_change, args=(u,))
                    with s_c3:
                        item["height"] = st.number_input("Height (H)", min_value=0.0, value=float(item.get("height", 1.0)), step=0.5, key=f"item_hgt_{u}", on_change=_recalc_on_dim_change, args=(u,))
                    with s_c4:
                        u_opts = ["Inch", "Ft"]
                        c_u = item.get("dim_unit", "Inch")
                        u_idx = u_opts.index(c_u) if c_u in u_opts else 0
                        item["dim_unit"] = st.selectbox("Size Unit", u_opts, index=u_idx, key=f"item_dunit_{u}")

                    r_c1, r_c2, r_c3 = st.columns(3)
                    with r_c1:
                        item["quantity"] = st.number_input("Quantity", min_value=0.0, value=float(item.get("quantity", 0.0)), step=1.0, key=f"item_qty_{u}", on_change=_sync_commercials, args=(u, "qty"))
                    with r_c2:
                        item["rate"] = st.number_input("Rate (INR)", min_value=0.0, value=float(item.get("rate", 0.0)), step=10.0, key=f"item_rate_{u}", on_change=_sync_commercials, args=(u, "rate"))
                    with r_c3:
                        item["amount"] = st.number_input("Total Amount (INR)", min_value=0.0, value=float(item.get("amount", 0.0)), step=50.0, key=f"item_amt_{u}", on_change=_sync_commercials, args=(u, "amount"))

                    d_c1, d_c2 = st.columns(2)
                    with d_c1:
                        item["specifications"] = st.text_input("Technical Specifications", value=item.get("specifications", ""), key=f"item_spec_{u}")
                    with d_c2:
                        item["delivery_address"] = st.text_input("Delivery Branch Location", value=item.get("delivery_address", ""), key=f"item_addr_{u}")

            if uids_to_remove:
                st.session_state.sales_items = [i for i in st.session_state.sales_items if i["uid"] not in uids_to_remove]
                st.rerun()

        grand_total = sum(float(it.get("amount", 0.0)) for it in st.session_state.sales_items)
        with st.container(border=True):
            sub_col1, sub_col2 = st.columns([7, 3])
            with sub_col1:
                st.markdown(f"#### Grand Total Order Value: ₹ {grand_total:,.2f}")
            with sub_col2:
                submit_clicked = st.button("Submit & Dispatch Jobsheet", type="primary", use_container_width=True)

        if submit_clicked:
            raw_input = st.session_state.get("s_manual_job_no", "").strip()
            clean_job_no = raw_input.lstrip("#").strip() if raw_input else str(get_next_job_no())
            c_name = str(client_name).strip()

            if not clean_job_no:
                st.error("Please provide a valid Jobsheet Number.")
            elif not c_name:
                st.error("Please fill in Client Entity.")
            elif is_gst and (not gstin or len(gstin) < 15):
                st.error("15-character GSTIN is required for GST Tax Invoices.")
            elif is_gst and not billing_address:
                st.error("Billing Address is required for GST Tax Invoices.")
            elif any(not it.get("item_name", "").strip() for it in st.session_state.sales_items):
                st.error("Please ensure every line item has a valid name.")
            elif grand_total <= 0:
                st.error("Order value cannot be zero. Fill quantity, rate, and amount.")
            else:
                header_payload = {
                    "job_no": clean_job_no,
                    "client_name": c_name,
                    "contact_person": contact_person.strip() or "Direct Client",
                    "contact_phone": contact_phone.strip() or "N/A",
                    "due_date": str(due_date),
                    "order_taken_by": user["full_name"],
                    "current_stage": routed_desk,
                    "assigned_designer": target_designer if routed_desk == "DESIGN" else None,
                    "is_returned": False,
                    "billing_type": "GST" if is_gst else "NON_GST",
                    "gstin": gstin if is_gst else None,
                    "billing_address": billing_address if billing_address else None,
                    "place_of_supply": place_of_supply if is_gst else None,
                    "is_billed": False,
                }

                # Bug 1 Fix: append inside the loop
                prepared_items = []
                for it in st.session_state.sales_items:
                    size_str = f"Size: {it.get('length', 1.0)} x {it.get('breadth', 1.0)} x {it.get('height', 1.0)} {it.get('dim_unit', 'Inch')}"
                    full_spec = it.get("specifications", "").strip()
                    if size_str:
                        full_spec = f"{size_str} | {full_spec}" if full_spec else size_str

                    prepared_items.append({
                        "item_name": it["item_name"].strip(),
                        "specifications": full_spec,
                        "quantity": float(it["quantity"]),
                        "unit": "Pcs",
                        "rate": float(it["rate"]),
                        "amount": float(it["amount"]),
                        "delivery_address": it.get("delivery_address", "").strip(),
                    })

                ok, msg = create_job_sheet(header_payload, prepared_items)
                if ok:
                    try:
                        from email_service import send_new_jobsheet_alert
                        send_new_jobsheet_alert(header_payload, prepared_items)
                    except Exception:
                        pass

                    flash(f"Jobsheet #{clean_job_no} created and routed to {routed_desk} successfully!")
                    st.session_state.sales_items = [_make_empty_item()]
                    if "s_manual_job_no" in st.session_state:
                        del st.session_state["s_manual_job_no"]
                    st.rerun()
                else:
                    st.error(f"Failed to create jobsheet: {msg}")

    # =========================================================
    # TAB 2: ORDER HISTORY & MODIFICATIONS
    # =========================================================
    with t_history:
        my_jobs = get_user_created_jobs(user["full_name"], is_management=is_management) or []

        floor_names = {
            "SALES": "Sales Desk (Returned)",
            "DESIGN": "Design Desk",
            "PAYMENT": "Accounts Desk",
            "PRODUCTION": "Production Floor",
            "QC": "Quality Check",
            "DISPATCH": "Dispatch Desk",
            "BILLING_REVIEW": "Billing Review",
            "BILLING_QUEUE": "CA Invoicing Queue",
            "SETTLED": "Settled & Closed"
        }

        # Filter bar
        with st.container(border=True):
            f1, f2, f3 = st.columns([4, 4, 2])
            with f1:
                search_kw = st.text_input("Search Orders", placeholder="Search Job No, Client...", key="sales_search_kw").strip().lower()
            with f2:
                sel_floor = st.selectbox("Filter Stage", options=["All Statuses"] + list(floor_names.values()), key="sales_floor_filter")
            with f3:
                sort_order = st.selectbox("Sort", ["Newest First", "Oldest First", "Due Soon"], key="sales_sort_filter")

        filtered_jobs = []
        for j in my_jobs:
            stg = j.get("current_stage", "DESIGN")
            stg_clean = floor_names.get(stg, stg)
            if sel_floor != "All Statuses" and stg_clean != sel_floor:
                continue
            if search_kw:
                txt = f"{j.get('job_no', '')} {j.get('client_name', '')} {j.get('contact_person', '')}".lower()
                if search_kw not in txt:
                    continue
            filtered_jobs.append(j)

        if sort_order == "Newest First":
            filtered_jobs.sort(key=lambda x: x.get("job_id", 0), reverse=True)
        elif sort_order == "Oldest First":
            filtered_jobs.sort(key=lambda x: x.get("job_id", 0))
        elif sort_order == "Due Soon":
            filtered_jobs.sort(key=lambda x: str(x.get("due_date", "9999-99-99")))

        if not filtered_jobs:
            st.info("No matching orders found.")
        else:
            for j in filtered_jobs:
                jid = j["job_id"]
                job_no = j.get("job_no", str(jid))
                stg = j.get("current_stage", "DESIGN")
                is_ret = j.get("is_returned", False)

                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 2])
                    with c1:
                        st.markdown(f"**Job #{job_no} — {j.get('client_name')}**")
                        st.caption(f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱 `{j.get('contact_phone') or 'N/A'}`")
                        if is_ret:
                            st.error(f"⚠️ Flagged Return: {j.get('return_reason')}")
                    with c2:
                        st.markdown(f"**Stage:** `{floor_names.get(stg, stg)}`")
                        st.caption(f"📅 Due: `{j.get('due_date')}` | Booked: `{str(j.get('created_at', ''))[:10]}`")
                    with c3:
                        items = get_job_items(jid)
                        j_val = sum(float(it.get("amount", 0) or 0) for it in items)
                        st.metric("Total Value", f"₹ {j_val:,.2f}")

                        # Action permissions
                        act_options = ["Select Action"]
                        if can_edit_jobs:
                            act_options.extend(["Edit Jobsheet", "Delete Jobsheet"])
                        else:
                            act_options.append("Request Deletion")

                        sel_action = st.selectbox("Action", act_options, key=f"act_j_{jid}")

                        if sel_action == "Delete Jobsheet":
                            with st.popover(f"Confirm Permanent Delete #{job_no}"):
                                st.warning("This will permanently remove the jobsheet and items.")
                                if st.button("Confirm Delete", key=f"btn_d_{jid}", type="primary"):
                                    delete_job_sheet(jid)
                                    log_audit(user["user_id"], "JOB_DELETED", f"Deleted job #{job_no}")
                                    flash(f"Job #{job_no} deleted.")
                                    st.rerun()

                        elif sel_action == "Request Deletion":
                            with st.popover("Submit Deletion Request"):
                                del_rsn = st.text_input("Reason for Deletion *", key=f"req_d_rsn_{jid}")
                                if st.button("Send Request to CEO", key=f"btn_req_d_{jid}", type="primary"):
                                    if not del_rsn.strip():
                                        st.error("Please state reason.")
                                    else:
                                        request_job_deletion(jid, user["full_name"], del_rsn)
                                        flash(f"Deletion request for #{job_no} submitted to CEO.")
                                        st.rerun()

                        elif sel_action == "Edit Jobsheet":
                            with st.popover(f"Edit Jobsheet #{job_no}", use_container_width=True):
                                st.markdown(f"#### Edit Jobsheet #{job_no}")
                                ed_client = st.text_input("Client Entity *", value=j.get("client_name") or "", key=f"e_cl_{jid}").strip()
                                ed_contact = st.text_input("Contact Person", value=j.get("contact_person") or "", key=f"e_cp_{jid}").strip()
                                ed_phone = st.text_input("Contact Phone", value=j.get("contact_phone") or "", key=f"e_ph_{jid}").strip()

                                stage_list = ["SALES", "DESIGN", "PAYMENT", "PRODUCTION", "QC", "DISPATCH", "BILLING_REVIEW", "BILLING_QUEUE", "SETTLED"]
                                cur_st_idx = stage_list.index(stg) if stg in stage_list else 1
                                ed_stage = st.selectbox("Routing Stage *", stage_list, index=cur_st_idx, key=f"e_stg_{jid}")

                                is_curr_gst = j.get("billing_type") == "GST"
                                ed_bchoice = st.radio("Billing", ["Non-GST", "GST"], index=1 if is_curr_gst else 0, horizontal=True, key=f"e_bc_{jid}")
                                ed_is_gst = (ed_bchoice == "GST")
                                ed_gstin = st.text_input("GSTIN", value=j.get("gstin") or "", key=f"e_gst_{jid}").strip().upper() if ed_is_gst else None
                                ed_baddr = st.text_input("Billing Address", value=j.get("billing_address") or "", key=f"e_ba_{jid}").strip()

                                st.markdown("##### Line Items")
                                edited_items = []
                                for idx, it in enumerate(items):
                                    with st.container(border=True):
                                        ei_name = st.text_input(f"Item #{idx+1} Name", value=it.get("item_name", ""), key=f"ei_n_{jid}_{idx}")
                                        ei_spec = st.text_input("Specifications", value=it.get("specifications", ""), key=f"ei_s_{jid}_{idx}")
                                        iq1, iq2, iq3 = st.columns(3)
                                        with iq1:
                                            ei_qty = st.number_input("Qty", value=float(it.get("quantity") or 0), min_value=0.0, step=1.0, key=f"ei_q_{jid}_{idx}")
                                        with iq2:
                                            ei_rate = st.number_input("Rate", value=float(it.get("rate") or 0), min_value=0.0, step=10.0, key=f"ei_r_{jid}_{idx}")
                                        with iq3:
                                            ei_amt = st.number_input("Amount (INR)", value=float(it.get("amount") or 0), min_value=0.0, step=50.0, key=f"ei_a_{jid}_{idx}")
                                        ei_addr = st.text_input("Destination", value=it.get("delivery_address", ""), key=f"ei_d_{jid}_{idx}")
                                        edited_items.append({
                                            "item_name": ei_name.strip(),
                                            "specifications": ei_spec.strip(),
                                            "quantity": ei_qty,
                                            "unit": it.get("unit", "Pcs"),
                                            "rate": ei_rate,
                                            "amount": ei_amt,
                                            "delivery_address": ei_addr.strip(),
                                            "is_delivered": it.get("is_delivered", False)
                                        })

                                if st.button("Save Changes", key=f"btn_sv_{jid}", type="primary", use_container_width=True):
                                    if not ed_client:
                                        st.error("Client name required.")
                                    else:
                                        h_upd = {
                                            "client_name": ed_client,
                                            "contact_person": ed_contact,
                                            "contact_phone": ed_phone,
                                            "current_stage": ed_stage,
                                            "billing_type": "GST" if ed_is_gst else "NON_GST",
                                            "gstin": ed_gstin,
                                            "billing_address": ed_baddr if ed_baddr else None,
                                        }
                                        ok, u_msg = update_job_sheet_by_management(jid, h_upd, edited_items)
                                        if ok:
                                            log_audit(user["user_id"], "JOB_MODIFIED", f"Updated jobsheet #{job_no}")
                                            flash(f"Jobsheet #{job_no} updated successfully.")
                                            st.rerun()
                                        else:
                                            st.error(u_msg)