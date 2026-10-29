import re
from datetime import date, datetime
import streamlit as st
from database import (
    create_job_sheet,
    get_job_items,
    get_next_job_no,
    get_user_created_jobs,
    update_job_sheet_by_management,
    delete_job_sheet,
    get_all_designers,
    approve_and_forward_job,
    log_audit,
    supabase,
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


def _parse_spec_dimensions(spec_str):
    """Extracts (L, B, H, unit, clean_spec) from a formatted spec string."""
    if not spec_str:
        return 1.0, 1.0, 1.0, "Inch", ""
    pattern = r"Size:\s*([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)\s*(Inch|Ft)(?:\s*\|\s*(.*))?"
    m = re.match(pattern, spec_str.strip(), re.IGNORECASE)
    if m:
        try:
            l_val = float(m.group(1))
            b_val = float(m.group(2))
            h_val = float(m.group(3))
            unit_val = "Ft" if m.group(4).lower() == "ft" else "Inch"
            notes = (m.group(5) or "").strip()
            return l_val, b_val, h_val, unit_val, notes
        except Exception:
            pass
    return 1.0, 1.0, 1.0, "Inch", spec_str.strip()


def _sync_edit_commercials(jid, idx, trigger_field):
    l_val = float(st.session_state.get(f"ei_l_{jid}_{idx}", 1.0))
    b_val = float(st.session_state.get(f"ei_b_{jid}_{idx}", 1.0))
    h_val = float(st.session_state.get(f"ei_h_{jid}_{idx}", 1.0))
    dim_factor = (l_val if l_val > 0 else 1.0) * (b_val if b_val > 0 else 1.0) * (h_val if h_val > 0 else 1.0)

    qty = float(st.session_state.get(f"ei_q_{jid}_{idx}", 1.0))
    rate = float(st.session_state.get(f"ei_r_{jid}_{idx}", 0.0))
    amt = float(st.session_state.get(f"ei_amt_{jid}_{idx}", 0.0))

    if trigger_field in ["dim", "qty", "rate"]:
        new_amt = round(dim_factor * qty * rate, 2)
        st.session_state[f"ei_amt_{jid}_{idx}"] = new_amt
    elif trigger_field == "amount":
        if qty > 0 and dim_factor > 0:
            st.session_state[f"ei_r_{jid}_{idx}"] = round(amt / (dim_factor * qty), 2)


def render(user):
    st.subheader("Module 1: Order Intake & Commercial Jobsheet Creation")
    st.caption(
        f"Sales Representative: **{user['full_name']}** | Code: `{user.get('emp_code', 'N/A')}` | Role: `{user.get('account_type')}`"
    )

    is_management = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]
    t_create, t_history = st.tabs(["Create New Jobsheet", "Order History & Modifications"])

    # =========================================================
    # TAB 1: CREATE NEW JOBSHEET (MODERN DARK THEME)
    # =========================================================
    with t_create:
        # Styles for the left stepper navigation rail
        st.markdown("""
            <style>
            .stepper-container {
                display: flex;
                flex-direction: column;
                gap: 12px;
                padding-top: 10px;
            }
            .stepper-item {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 13px;
                font-weight: 500;
                color: #94a3b8;
            }
            .stepper-item.active {
                color: #f8fafc;
                font-weight: 600;
            }
            .step-dot {
                width: 14px;
                height: 14px;
                border-radius: 50%;
                border: 2px solid #475569;
                background-color: transparent;
                display: inline-block;
            }
            .step-dot.active {
                background-color: #E11D48;
                border-color: #E11D48;
                box-shadow: 0 0 10px rgba(225, 29, 72, 0.5);
            }
            .step-line {
                width: 2px;
                height: 32px;
                background-color: #334155;
                margin-left: 6px;
            }
            .step-line.active {
                background-color: #E11D48;
            }
            </style>
        """, unsafe_allow_html=True)

        suggested_no = get_next_job_no()
        if "s_manual_job_no" not in st.session_state:
            st.session_state["s_manual_job_no"] = str(suggested_no)

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

        st.markdown("### Jobsheet Creation Form")

        # Layout: Left Stepper Navigation Rail, Right Form Sections
        rail_col, form_col = st.columns([1.5, 8.5])

        with rail_col:
            st.markdown("""
                <div class="stepper-container">
                    <div class="stepper-item active">
                        <span class="step-dot active"></span>
                        <span>1. Client Details</span>
                    </div>
                    <div class="step-line active"></div>
                    <div class="stepper-item">
                        <span class="step-dot"></span>
                        <span>2. Item & Specifications</span>
                    </div>
                    <div class="step-line"></div>
                    <div class="stepper-item">
                        <span class="step-dot"></span>
                        <span>3. Commercials</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with form_col:
            # SECTION 1: CLIENT & COMMERCIAL HEADER
            with st.container(border=True):
                st.markdown("#### 1. Client & Commercial Header")

                # Row 1: Billing Classification (Left) & Jobsheet Number (Right)
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
                    st.text_input(
                        "Jobsheet Number *",
                        key="s_manual_job_no",
                        placeholder="e.g. 1081"
                    )

                # Row 2: Billing Address (Left) & Target Delivery Date / Routing Workflow Target (Right)
                r2_c1, r2_c2, r2_c3 = st.columns([6, 2, 2])
                with r2_c1:
                    billing_address = st.text_input(
                        "Billing Address" + (" *" if is_gst else " (Optional)"),
                        placeholder="e.g. 12/A Park Street, Kolkata - 700016",
                        key="s_baddr"
                    ).strip()
                with r2_c2:
                    due_date = st.date_input(
                        "Target Delivery Date *",
                        min_value=date.today(),
                        key="s_due"
                    )
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

                # Row 3: Client Entity, Contact, Phone, and Assigned Designer
                r3_c1, r3_c2, r3_c3, r3_c4 = st.columns([2.5, 2.5, 2.5, 2.5])
                with r3_c1:
                    client_name = st.text_input(
                        "Client / Corporate Entity *",
                        placeholder="e.g. Apollo Hospitals",
                        key="s_client"
                    ).strip()
                with r3_c2:
                    contact_person = st.text_input(
                        "Contact Person",
                        placeholder="e.g. Amitava Ghosh",
                        key="s_contact"
                    ).strip()
                with r3_c3:
                    contact_phone = st.text_input(
                        "Mobile / Contact Number",
                        placeholder="e.g. 9830112233",
                        key="s_phone"
                    ).strip()
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
                        gstin = st.text_input(
                            "Client GSTIN *",
                            placeholder="e.g. 19AAAAA0000A1Z5",
                            key="s_gstin"
                        ).strip().upper()
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

            # SECTION 2: COMMERCIAL LINE ITEMS & SPECS
            with st.container(border=True):
                head_c1, head_c2 = st.columns([7, 3])
                with head_c1:
                    st.markdown("#### 2. Commercial Line Items & Specs")
                with head_c2:
                    st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
                    if st.button("+ Add Item Row", key="btn_add_item_top", use_container_width=True):
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
                    st.markdown("</div>", unsafe_allow_html=True)

                rows_to_remove = []
                for idx, item in enumerate(st.session_state.sales_items):
                    with st.container(border=True):
                        top_c1, top_c2 = st.columns([9.2, 0.8])
                        with top_c1:
                            item["item_name"] = st.text_input(
                                f"Item Name #{idx+1} *",
                                value=item.get("item_name", ""),
                                placeholder="e.g. Backlit Flex Signboard",
                                key=f"item_name_{idx}",
                            )
                        with top_c2:
                            if len(st.session_state.sales_items) > 1:
                                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                                if st.button("X", key=f"del_row_{idx}", help="Remove Item"):
                                    rows_to_remove.append(idx)

                        st.caption("Sizes / Dimensions (Default: 1 x 1 x 1):")
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

                        st.caption("Commercials (Fill any 2 fields to auto-calculate the 3rd):")
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
                                "Rate (INR)",
                                min_value=0.0,
                                value=float(item.get("rate", 0.0)),
                                step=10.0,
                                key=f"item_rate_{idx}",
                                on_change=_sync_commercials,
                                args=(idx, "rate"),
                            )
                        with r_c3:
                            item["amount"] = st.number_input(
                                "Total Amount (INR)",
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

            # SECTION 3: BOTTOM GRAND TOTAL & DISPATCH BAR
            grand_total = sum(float(it.get("amount", 0.0)) for it in st.session_state.sales_items)

            with st.container(border=True):
                sub_col1, sub_col2 = st.columns([7, 3])
                with sub_col1:
                    st.markdown(
                        f"<div style='font-size: 20px; font-weight: 700; color: #f8fafc; padding-top: 6px;'>"
                        f"Grand Total Order Value: <span style='color: #ffffff;'>INR {grand_total:,.2f}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with sub_col2:
                    submit_clicked = st.button("Submit & Dispatch Jobsheet", type="primary", use_container_width=True)

            if submit_clicked:
                raw_input = st.session_state.get("s_manual_job_no", "").strip()
                clean_job_no = raw_input.lstrip("#").strip() if raw_input else str(get_next_job_no())
                c_name = str(client_name).strip() if client_name else ""
                c_person = str(contact_person).strip() if contact_person else "Direct Client"
                c_phone = str(contact_phone).strip() if contact_phone else "N/A"

                if not clean_job_no:
                    st.error("Please provide a valid Jobsheet Number.")
                elif not c_name:
                    st.error("Please fill in mandatory field: Client / Corporate Entity")
                elif is_gst and (not gstin or len(gstin) < 15):
                    st.error("Please provide a valid 15-character GSTIN for GST Tax Invoices.")
                elif is_gst and not billing_address:
                    st.error("Registered Billing Address is required for GST Tax Invoices.")
                elif any(not it.get("item_name", "").strip() for it in st.session_state.sales_items):
                    st.error("Please ensure every added line item has a valid name.")
                else:
                    header_payload = {
                        "job_no": clean_job_no,
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
                        st.success(f"Job Sheet #{clean_job_no} created successfully and routed to `{routed_desk}`{des_msg}!")
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
                        if "s_manual_job_no" in st.session_state:
                            del st.session_state["s_manual_job_no"]
                        st.rerun()
                    else:
                        st.error(f"Failed to create jobsheet: {msg}")

    # =========================================================
    # TAB 2: ORDER HISTORY & MODIFICATIONS (15-ROW PAGINATED TABLE)
    # =========================================================
    with t_history:
        my_jobs = get_user_created_jobs(user["full_name"], is_management=is_management) or []

        floor_names = {
            "DESIGN": "Design Desk",
            "PAYMENT": "Accounts Desk",
            "PRODUCTION": "Production Floor",
            "QC": "Quality Check",
            "DISPATCH": "Dispatch Desk",
            "BILLING_REVIEW": "Billing Review",
            "BILLING": "Billing Desk",
            "SETTLED": "Settled & Closed"
        }

        stage_progress = {
            "DESIGN": 15,
            "PAYMENT": 30,
            "PRODUCTION": 50,
            "QC": 75,
            "DISPATCH": 90,
            "BILLING_REVIEW": 100,
            "BILLING": 100,
            "SETTLED": 100
        }

        pill_classes = {
            "DESIGN": "pill-design",
            "PAYMENT": "pill-payment",
            "PRODUCTION": "pill-production",
            "QC": "pill-qc",
            "DISPATCH": "pill-dispatch",
            "BILLING_REVIEW": "pill-billing",
            "BILLING": "pill-billing",
            "SETTLED": "pill-settled"
        }

        # Callback to safely reset filter states before widgets re-instantiate
        def _reset_sales_filters():
            st.session_state["sales_search_kw"] = ""
            st.session_state["sales_floor_filter"] = "All Statuses"
            st.session_state["sales_sort_filter"] = "Recent Jobs (Newest First)"
            st.session_state["sales_page_num"] = 1

        # Top Filter Bar
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([2.5, 2.5, 2.5, 1.5])
            with f1:
                search_kw = st.text_input(
                    "Search Orders",
                    placeholder="Search Job No, Client, Contact...",
                    key="sales_search_kw"
                ).strip().lower()
            with f2:
                status_choices = ["All Statuses"] + list(floor_names.values())
                sel_floor = st.selectbox("Floor Status", options=status_choices, key="sales_floor_filter")
            with f3:
                sort_order = st.selectbox(
                    "Sort By",
                    options=["Recent Jobs (Newest First)", "Oldest Jobs", "Delivery Due Soonest"],
                    key="sales_sort_filter"
                )
            with f4:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                st.button(
                    "Reset Filters",
                    type="secondary",
                    use_container_width=True,
                    key="sales_reset_btn",
                    on_click=_reset_sales_filters
                )

        # Filter Logic
        filtered_jobs = []
        for j in my_jobs:
            stg = j.get("current_stage", "DESIGN")
            stg_clean = floor_names.get(stg, stg)

            if sel_floor != "All Statuses" and stg_clean != sel_floor:
                continue

            if search_kw:
                comb_text = f"{j.get('job_no', '')} {j.get('client_name', '')} {j.get('contact_person', '')} {j.get('contact_phone', '')}".lower()
                if search_kw not in comb_text:
                    continue

            filtered_jobs.append(j)

        # Sorting Logic
        if sort_order == "Recent Jobs (Newest First)":
            filtered_jobs.sort(key=lambda x: x.get("job_id", 0), reverse=True)
        elif sort_order == "Oldest Jobs":
            filtered_jobs.sort(key=lambda x: x.get("job_id", 0))
        elif sort_order == "Delivery Due Soonest":
            filtered_jobs.sort(key=lambda x: str(x.get("due_date", "9999-99-99")))

        # Fixed 15 Rows Per Page
        ROWS_PER_PAGE = 15
        total_records = len(filtered_jobs)
        total_pages = max(1, (total_records + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)

        if "sales_page_num" not in st.session_state:
            st.session_state.sales_page_num = 1

        if st.session_state.sales_page_num > total_pages:
            st.session_state.sales_page_num = total_pages

        curr_page = st.session_state.sales_page_num
        start_idx = (curr_page - 1) * ROWS_PER_PAGE
        end_idx = min(start_idx + ROWS_PER_PAGE, total_records)
        page_records = filtered_jobs[start_idx:end_idx]

        # Identify ticked jobs across the currently displayed page
        selected_job_ids = [
            j["job_id"] for j in page_records 
            if st.session_state.get(f"tbl_chk_{j['job_id']}", False)
        ]

        # Top Bar: Record Counter & Conditional Bulk Delete Button
        bar_col1, bar_col2 = st.columns([7, 3])
        with bar_col1:
            st.caption(f"Showing **{start_idx + 1 if total_records else 0} to {end_idx}** of **{total_records}** records")
        with bar_col2:
            if selected_job_ids:
                with st.popover(f"Delete Selected ({len(selected_job_ids)})", use_container_width=True):
                    st.warning(f"Permanently delete {len(selected_job_ids)} selected job(s)?")
                    if st.button("Confirm Bulk Delete", type="primary", use_container_width=True, key="btn_bulk_del_confirm"):
                        for del_jid in selected_job_ids:
                            delete_job_sheet(del_jid)
                            if f"tbl_chk_{del_jid}" in st.session_state:
                                del st.session_state[f"tbl_chk_{del_jid}"]
                        log_audit(user["user_id"], "BULK_DELETE", f"Deleted jobs: {selected_job_ids}")
                        st.success(f"{len(selected_job_ids)} job(s) deleted successfully.")
                        st.rerun()

        if not page_records:
            st.info("No matching job orders found.")
        else:
            # Shared Typography Styles
            st.markdown("""
                <style>
                .tbl-cell-text {
                    font-size: 13px !important;
                    font-family: inherit !important;
                    color: #1e293b !important;
                    font-weight: 500 !important;
                    line-height: 1.4 !important;
                    padding-top: 8px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .tbl-cell-header {
                    font-size: 13px !important;
                    font-family: inherit !important;
                    font-weight: 700 !important;
                    color: #475569 !important;
                    letter-spacing: 0.3px;
                    text-transform: uppercase;
                }
                .adnet-progress-circle-red {
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 11px;
                    font-weight: 700;
                    margin: auto;
                }
                </style>
            """, unsafe_allow_html=True)

            # Table Header Bar (Blank space instead of '[ ]')
            st.markdown("""
                <div class="adnet-table-header" style="padding: 10px 14px;">
                    <div style="display: grid; grid-template-columns: 0.3fr 1fr 1fr 1.8fr 1.6fr 1.1fr 0.9fr 1.3fr 1.6fr; align-items: center; gap: 8px;">
                        <div class="tbl-cell-header">&nbsp;</div>
                        <div class="tbl-cell-header">Job No.</div>
                        <div class="tbl-cell-header">Date</div>
                        <div class="tbl-cell-header">Client</div>
                        <div class="tbl-cell-header">Contact</div>
                        <div class="tbl-cell-header">Delivery Date</div>
                        <div class="tbl-cell-header" style="text-align: center;">Progress</div>
                        <div class="tbl-cell-header" style="text-align: center;">Status</div>
                        <div class="tbl-cell-header" style="text-align: center;">Action</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Table Rows
            for j in page_records:
                jid = j["job_id"]
                job_no = j.get("job_no", str(jid))
                created_date = str(j.get("created_at", ""))[:10] or "N/A"
                client_name = j.get("client_name") or "N/A"
                contact_p = j.get("contact_person") or "N/A"
                contact_ph = j.get("contact_phone") or "N/A"
                due_date_str = str(j.get("due_date") or "N/A")
                stg = j.get("current_stage", "DESIGN")
                stg_display = floor_names.get(stg, stg)
                pill_style = pill_classes.get(stg, "pill-design")
                pct = stage_progress.get(stg, 15)

                r_chk, r_no, r_date, r_client, r_contact, r_due, r_prog, r_stat, r_act = st.columns(
                    [0.3, 1, 1, 1.8, 1.6, 1.1, 0.9, 1.3, 1.6]
                )

                with r_chk:
                    st.checkbox(" ", key=f"tbl_chk_{jid}", label_visibility="collapsed")

                with r_no:
                    st.markdown(f"<div class='tbl-cell-text' style='font-weight: 700 !important;'>JOB-{job_no}</div>", unsafe_allow_html=True)

                with r_date:
                    st.markdown(f"<div class='tbl-cell-text'>{created_date}</div>", unsafe_allow_html=True)

                with r_client:
                    st.markdown(f"<div class='tbl-cell-text' title='{client_name}'>{client_name}</div>", unsafe_allow_html=True)

                with r_contact:
                    st.markdown(f"<div class='tbl-cell-text' title='{contact_p} ({contact_ph})'>{contact_p} <span style='color:#64748b; font-size:11px;'>({contact_ph})</span></div>", unsafe_allow_html=True)

                with r_due:
                    st.markdown(f"<div class='tbl-cell-text'>{due_date_str}</div>", unsafe_allow_html=True)

                with r_prog:
                    st.markdown(
                        f"<div class='adnet-progress-circle-red' style='background: conic-gradient(#E11D48 {pct}%, #e2e8f0 0); border: 2px solid #ffffff;'>"
                        f"<div style='background: #ffffff; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #BE123C; font-size: 10px; font-weight: 700;'>"
                        f"{pct}%</div></div>",
                        unsafe_allow_html=True
                    )

                with r_stat:
                    st.markdown(
                        f"<div style='text-align: center; padding-top: 6px;'>"
                        f"<span class='adnet-pill {pill_style}'>{stg_display}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with r_act:
                    action_choice = st.selectbox(
                        "Action",
                        options=["Select Action", "Edit", "Delete"],
                        index=0,
                        key=f"act_drp_{jid}",
                        label_visibility="collapsed"
                    )

                    if action_choice == "Delete":
                        with st.popover(f"Confirm Delete Job #{job_no}", use_container_width=True):
                            st.warning(f"Are you sure you want to delete Job #{job_no}?")
                            if st.button("Confirm Delete", key=f"btn_confirm_del_{jid}", type="primary", use_container_width=True):
                                delete_job_sheet(jid)
                                log_audit(user["user_id"], "JOB_DELETED", f"Deleted job #{job_no} from Order History")
                                st.success(f"Job #{job_no} deleted successfully.")
                                st.rerun()

                    elif action_choice == "Edit":
                        with st.popover(f"Edit Jobsheet #{job_no}", use_container_width=True):
                            st.markdown(f"#### Edit Jobsheet #{job_no}")
                            items = get_job_items(jid)

                            is_currently_gst = j.get("billing_type") == "GST"
                            ed_billing_choice = st.radio(
                                "Billing Classification *",
                                options=["Non-GST Bill", "GST Invoice (B2B Tax Invoice)"],
                                index=1 if is_currently_gst else 0,
                                horizontal=True,
                                key=f"ed_bchoice_{jid}"
                            )
                            ed_is_gst = "GST Invoice" in ed_billing_choice

                            ed_client = st.text_input("Client / Corporate Entity *", value=j.get("client_name") or "", key=f"ed_cl_{jid}").strip()
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                ed_contact = st.text_input("Contact Person", value=j.get("contact_person") or "", key=f"ed_cp_{jid}").strip()
                            with ec2:
                                ed_phone = st.text_input("Contact Phone", value=j.get("contact_phone") or "", key=f"ed_ph_{jid}").strip()

                            cur_due = date.today()
                            if j.get("due_date"):
                                try:
                                    cur_due = datetime.strptime(str(j.get("due_date")), "%Y-%m-%d").date()
                                except Exception:
                                    cur_due = date.today()

                            ed1, ed2 = st.columns(2)
                            with ed1:
                                ed_due = st.date_input("Target Delivery Date *", value=cur_due, key=f"ed_due_{jid}")
                            with ed2:
                                stage_list = ["DESIGN", "PAYMENT", "PRODUCTION", "QC", "DISPATCH", "BILLING_REVIEW", "SETTLED"]
                                cur_st_idx = stage_list.index(j.get("current_stage")) if j.get("current_stage") in stage_list else 0
                                ed_stage = st.selectbox("Routing Stage *", stage_list, index=cur_st_idx, key=f"ed_stg_{jid}")

                            designers_all = get_all_designers()
                            d_names = ["OPEN_POOL"] + [d["full_name"] for d in designers_all]
                            cur_des = j.get("assigned_designer") or "OPEN_POOL"
                            d_idx = d_names.index(cur_des) if cur_des in d_names else 0
                            ed_designer = st.selectbox("Assigned Designer", options=d_names, index=d_idx, key=f"ed_des_{jid}")

                            ed_gstin = j.get("gstin", "") or ""
                            ed_baddr = j.get("billing_address", "") or ""
                            ed_pos = j.get("place_of_supply", "19 - West Bengal") or "19 - West Bengal"

                            if ed_is_gst:
                                eg1, eg2 = st.columns(2)
                                with eg1:
                                    ed_gstin = st.text_input("Client GSTIN *", value=ed_gstin, key=f"ed_gstin_{jid}").strip().upper()
                                with eg2:
                                    pos_opts = ["19 - West Bengal", "10 - Bihar", "20 - Jharkhand", "21 - Odisha", "18 - Assam", "07 - Delhi", "27 - Maharashtra", "Other State"]
                                    pos_idx = pos_opts.index(ed_pos) if ed_pos in pos_opts else 0
                                    ed_pos = st.selectbox("Place of Supply *", pos_opts, index=pos_idx, key=f"ed_pos_{jid}")

                            ed_baddr = st.text_input(
                                "Billing Address" + (" *" if ed_is_gst else " (Optional)"),
                                value=ed_baddr,
                                key=f"ed_baddr_{jid}"
                            ).strip()

                            st.markdown("---")
                            st.markdown("##### Ordered Line Items & Deliverables")
                            edited_items = []
                            for idx, it in enumerate(items):
                                with st.container(border=True):
                                    st.caption(f"Item #{idx+1}")
                                    ei_name = st.text_input("Item Name *", value=it.get("item_name", ""), key=f"ei_nm_{jid}_{idx}")

                                    def_l, def_b, def_h, def_u, def_notes = _parse_spec_dimensions(it.get("specifications", ""))

                                    st.caption("Sizes / Dimensions (Default: 1 x 1 x 1):")
                                    ed_s1, ed_s2, ed_s3, ed_s4 = st.columns(4)
                                    with ed_s1:
                                        ei_l = st.number_input(
                                            "Length (L)",
                                            min_value=0.0,
                                            value=def_l,
                                            step=1.0,
                                            key=f"ei_l_{jid}_{idx}",
                                            on_change=_sync_edit_commercials,
                                            args=(jid, idx, "dim"),
                                        )
                                    with ed_s2:
                                        ei_b = st.number_input(
                                            "Breadth / Width (B)",
                                            min_value=0.0,
                                            value=def_b,
                                            step=1.0,
                                            key=f"ei_b_{jid}_{idx}",
                                            on_change=_sync_edit_commercials,
                                            args=(jid, idx, "dim"),
                                        )
                                    with ed_s3:
                                        ei_h = st.number_input(
                                            "Height / Depth (H)",
                                            min_value=0.0,
                                            value=def_h,
                                            step=0.5,
                                            key=f"ei_h_{jid}_{idx}",
                                            on_change=_sync_edit_commercials,
                                            args=(jid, idx, "dim"),
                                        )
                                    with ed_s4:
                                        unit_opts = ["Inch", "Ft"]
                                        u_idx = unit_opts.index(def_u) if def_u in unit_opts else 0
                                        ei_unit = st.selectbox(
                                            "Size Unit",
                                            unit_opts,
                                            index=u_idx,
                                            key=f"ei_u_{jid}_{idx}",
                                        )

                                    st.caption("Commercials (Fill any 2 fields to auto-calculate the 3rd):")
                                    iq1, iq2, iq3 = st.columns(3)
                                    with iq1:
                                        ei_qty = st.number_input(
                                            "Quantity",
                                            value=float(it.get("quantity", 1.0)),
                                            min_value=0.0,
                                            step=1.0,
                                            key=f"ei_q_{jid}_{idx}",
                                            on_change=_sync_edit_commercials,
                                            args=(jid, idx, "qty"),
                                        )
                                    with iq2:
                                        ei_rate = st.number_input(
                                            "Rate (INR)",
                                            value=float(it.get("rate", 0.0)),
                                            min_value=0.0,
                                            step=10.0,
                                            key=f"ei_r_{jid}_{idx}",
                                            on_change=_sync_edit_commercials,
                                            args=(jid, idx, "rate"),
                                        )
                                    with iq3:
                                        ei_amt = st.number_input(
                                            "Total Amount (INR)",
                                            value=float(it.get("amount", 0.0)),
                                            min_value=0.0,
                                            step=50.0,
                                            key=f"ei_amt_{jid}_{idx}",
                                            on_change=_sync_edit_commercials,
                                            args=(jid, idx, "amount"),
                                        )

                                    ei_spec_notes = st.text_input(
                                        "Technical Specifications / Material Notes",
                                        value=def_notes,
                                        placeholder="e.g. 5mm Clear Acrylic, 3M vinyl",
                                        key=f"ei_sp_{jid}_{idx}",
                                    )

                                    ei_addr = st.text_input(
                                        "Delivery Destination",
                                        value=it.get("delivery_address", ""),
                                        key=f"ei_ad_{jid}_{idx}",
                                    )

                                    size_str = f"Size: {ei_l} x {ei_b} x {ei_h} {ei_unit}"
                                    full_spec = f"{size_str} | {ei_spec_notes.strip()}" if ei_spec_notes.strip() else size_str

                                    edited_items.append({
                                        "item_name": ei_name.strip(),
                                        "specifications": full_spec,
                                        "quantity": ei_qty,
                                        "unit": it.get("unit", "Pcs"),
                                        "rate": ei_rate,
                                        "amount": ei_amt,
                                        "delivery_address": ei_addr.strip(),
                                    })

                            if st.button("Save Changes", key=f"btn_save_edit_{jid}", type="primary", use_container_width=True):
                                if not ed_client:
                                    st.error("Client name is required.")