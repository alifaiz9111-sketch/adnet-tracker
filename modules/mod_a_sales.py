from datetime import date, datetime
import streamlit as st
from database import (
    create_job_sheet,
    get_job_items,
    get_next_job_no,
    get_user_created_jobs,
)


def render(user):
  st.subheader("📝 Module 1: Order Intake & Commercial Jobsheet Creation")
  st.caption(
      f"Sales Representative: **{user['full_name']}** | Code:"
      f" `{user.get('emp_code', 'N/A')}`"
  )

  t_create, t_history = st.tabs(
      ["➕ Create New Jobsheet", "📋 My Intake Order History"]
  )

  # --- TAB 1: CREATE NEW JOBSHEET ---
  with t_create:
    suggested_no = get_next_job_no()

    # Initialize dynamic item rows in session state
    if "sales_items" not in st.session_state:
      st.session_state.sales_items = [{
          "item_name": "",
          "specifications": "",
          "quantity": 1.0,
          "unit": "Pcs",
          "rate": 0.0,
          "amount": 0.0,
          "delivery_address": "",
      }]

    with st.container(border=True):
      st.markdown("#### 1. Client & Commercial Header")
      c1, c2, c3 = st.columns(3)
      with c1:
        job_no = st.text_input(
            "Jobsheet Number *", value=suggested_no, key="s_job_no"
        ).strip()
        client_name = st.text_input(
            "Client / Corporate Entity *",
            placeholder="e.g. Apollo Hospitals",
            key="s_client",
        ).strip()
      with c2:
        contact_person = st.text_input(
            "Contact Person *", placeholder="e.g. Amitava Ghosh", key="s_contact"
        ).strip()
        contact_phone = st.text_input(
            "Mobile / Contact Number *",
            placeholder="e.g. 9830112233",
            key="s_phone",
        ).strip()
      with c3:
        due_date = st.date_input(
            "Target Delivery Date *", min_value=date.today(), key="s_due"
        )
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

    # Item Row Controls
    btn_col1, btn_col2 = st.columns([1, 4])
    with btn_col1:
      if st.button("➕ Add Item Row", use_container_width=True):
        st.session_state.sales_items.append({
            "item_name": "",
            "specifications": "",
            "quantity": 1.0,
            "unit": "Pcs",
            "rate": 0.0,
            "amount": 0.0,
            "delivery_address": "",
        })
        st.rerun()

    # Dynamic line items
    rows_to_remove = []
    for idx, item in enumerate(st.session_state.sales_items):
      with st.container(border=True):
        r_c1, r_c2, r_c3, r_c4, r_c5, r_c6 = st.columns([2.5, 1, 1, 1, 1.2, 0.5])
        with r_c1:
          item["item_name"] = st.text_input(
              f"Item Name #{idx+1} *",
              value=item["item_name"],
              key=f"item_name_{idx}",
          )
        with r_c2:
          item["quantity"] = st.number_input(
              "Quantity",
              min_value=0.01,
              value=float(item["quantity"]),
              step=1.0,
              key=f"item_qty_{idx}",
          )
        with r_c3:
          item["unit"] = st.selectbox(
              "Unit",
              ["Pcs", "Sq.Ft", "R.Ft", "Sets", "Sheets", "Packets"],
              index=[
                  "Pcs",
                  "Sq.Ft",
                  "R.Ft",
                  "Sets",
                  "Sheets",
                  "Packets",
              ].index(item["unit"])
              if item["unit"]
              in ["Pcs", "Sq.Ft", "R.Ft", "Sets", "Sheets", "Packets"]
              else 0,
              key=f"item_unit_{idx}",
          )
        with r_c4:
          item["rate"] = st.number_input(
              "Rate (₹)",
              min_value=0.0,
              value=float(item["rate"]),
              step=50.0,
              key=f"item_rate_{idx}",
          )
        with r_c5:
          item["amount"] = round(item["quantity"] * item["rate"], 2)
          st.metric("Amount", f"₹ {item['amount']:,.2f}")
        with r_c6:
          if len(st.session_state.sales_items) > 1:
            if st.button("🗑️", key=f"del_row_{idx}"):
              rows_to_remove.append(idx)

        d_c1, d_c2 = st.columns(2)
        with d_c1:
          item["specifications"] = st.text_input(
              "Technical Specifications / Dimensions",
              value=item["specifications"],
              placeholder="e.g. 5mm Clear Acrylic, 3M reflective vinyl",
              key=f"item_spec_{idx}",
          )
        with d_c2:
          item["delivery_address"] = st.text_input(
              "Delivery Address / Branch Location",
              value=item["delivery_address"],
              placeholder="e.g. Salt Lake Sector V Office",
              key=f"item_addr_{idx}",
          )

    # Process removals
    if rows_to_remove:
      for r_idx in sorted(rows_to_remove, reverse=True):
        st.session_state.sales_items.pop(r_idx)
      st.rerun()

    # Total Pipeline Value
    grand_total = sum(it["amount"] for it in st.session_state.sales_items)
    st.markdown(f"### Grand Total Order Value: `₹ {grand_total:,.2f}`")

    if st.button(
        "🚀 Submit & Dispatch Jobsheet",
        type="primary",
        use_container_width=True,
    ):
      if not (job_no and client_name and contact_person and contact_phone):
        st.error(
            "Please fill in all required header fields (Job #, Client Name,"
            " Contact Person, and Phone)."
        )
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

        ok, msg = create_job_sheet(
            header_payload, st.session_state.sales_items
        )
        if ok:
          st.success(
              f"Job Sheet #{job_no} created successfully and routed to"
              f" `{routed_desk}`!"
          )
          st.session_state.sales_items = [{
              "item_name": "",
              "specifications": "",
              "quantity": 1.0,
              "unit": "Pcs",
              "rate": 0.0,
              "amount": 0.0,
              "delivery_address": "",
          }]
          st.rerun()
        else:
          st.error(f"Failed to create jobsheet: {msg}")

  # --- TAB 2: MY INTAKE ORDER HISTORY ---
  with t_history:
    is_admin = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]
    my_jobs = get_user_created_jobs(user["full_name"], is_management=is_admin)

    if not my_jobs:
      st.info("No orders found recorded by your desk.")
    else:
      for j in my_jobs:
        items = get_job_items(j["job_id"])
        total_val = sum(float(it.get("amount", 0) or 0) for it in items)

        with st.container(border=True):
          c1, c2, c3 = st.columns([2.5, 2, 1.5])
          with c1:
            st.markdown(
                f"**Job #{j.get('job_no')} — {j.get('client_name')}**"
            )
            st.caption(
                f"Contact: `{j.get('contact_person') or 'N/A'}` | 📱"
                f" `{j.get('contact_phone') or 'N/A'}`"
            )
            st.caption(
                f"Due: `{j.get('due_date')}` | Stage:"
                f" `{j.get('current_stage')}`"
            )
          with c2:
            st.markdown(f"**Value:** ₹ {total_val:,.2f}")
            for it in items:
              st.caption(
                  f"• {it.get('item_name')} ({it.get('quantity')}"
                  f" {it.get('unit')})"
              )
          with c3:
            if j.get("is_returned"):
              st.error(f"⚠️ Return: {j.get('return_reason')}")
            else:
              st.info(f"Desk: {j.get('current_stage')}")