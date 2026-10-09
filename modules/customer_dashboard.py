import streamlit as st
from database import supabase, get_job_items


def render(user):
    st.markdown("""
        <style>
        .cust-kpi-card {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px 20px;
        }
        .cust-kpi-title {
            font-size: 11px;
            font-weight: 700;
            color: #8B949E;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .cust-kpi-val {
            font-size: 24px;
            font-weight: 800;
            color: #E6EDF3;
            margin-top: 4px;
        }
        .status-pill {
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 12px;
            display: inline-block;
        }
        .pill-green { background: rgba(16, 185, 129, 0.15); color: #34D399; }
        .pill-red { background: rgba(225, 6, 0, 0.15); color: #F87171; }
        .pill-amber { background: rgba(245, 158, 11, 0.15); color: #FBBF24; }
        </style>
    """, unsafe_allow_html=True)

    # Initialize drill-down session state
    if "selected_customer" not in st.session_state:
        st.session_state.selected_customer = None

    try:
        j_res = supabase.table("jobs").select("*").order("job_id", desc=True).execute()
        all_jobs = j_res.data or []
        i_res = supabase.table("job_items").select("*").execute()
        all_items = i_res.data or []
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return

    # Map job totals
    job_val_map = {}
    for it in all_items:
        jid = it.get("job_id")
        job_val_map[jid] = job_val_map.get(jid, 0.0) + float(it.get("amount", 0) or 0)

    # --- DRILL-DOWN VIEW: JOBS OF SELECTED CUSTOMER ---
    if st.session_state.selected_customer:
        c_name = st.session_state.selected_customer
        customer_jobs = [j for j in all_jobs if (j.get("client_name") or "").strip().lower() == c_name.lower()]

        c_header_col, c_back_col = st.columns([5, 1.2])
        with c_header_col:
            st.markdown(f"### 🏢 Order History: <span style='color:#E10600;'>{c_name}</span>", unsafe_allow_html=True)
            st.caption(f"Showing all {len(customer_jobs)} recorded jobsheets and deliverables for this account.")
        with c_back_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬅️ Back to Directory", use_container_width=True, type="secondary"):
                st.session_state.selected_customer = None
                st.rerun()

        st.markdown("---")

        if not customer_jobs:
            st.info("No recorded jobs found for this customer.")
            return

        for job in customer_jobs:
            jid = job["job_id"]
            items = get_job_items(jid)
            job_val = job_val_map.get(jid, 0.0)
            is_settled = job.get("current_stage") == "SETTLED"
            is_ret = job.get("is_returned", False)

            with st.container(border=True):
                r1, r2, r3, r4 = st.columns([2, 3, 2, 1.5])
                with r1:
                    st.markdown(f"#### #{job.get('job_no')}")
                    if is_ret:
                        st.markdown("<span class='status-pill pill-red'>● DEFECT / RETURN</span>", unsafe_allow_html=True)
                    elif is_settled:
                        st.markdown("<span class='status-pill pill-green'>● SETTLED</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='status-pill pill-amber'>● {job.get('current_stage')}</span>", unsafe_allow_html=True)
                    st.caption(f"Due: `{job.get('due_date')}`")

                with r2:
                    st.markdown(f"**Contact:** `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                    st.caption(f"Booked by: `{job.get('order_taken_by') or 'Sales'}` | Desk: `{job.get('current_stage')}`")
                    if items:
                        item_str = ", ".join([f"{it.get('item_name')} ({it.get('quantity')} {it.get('unit')})" for it in items])
                        st.caption(f"📦 {item_str[:80]}{'...' if len(item_str) > 80 else ''}")

                with r3:
                    st.metric("Order Value", f"₹ {job_val:,.2f}")
                    adv = float(job.get("advance_received", 0) or 0)
                    bal = float(job.get("balance_amount", 0) or 0)
                    st.caption(f"Adv: ₹{adv:,.0f} | Bal: ₹{bal:,.0f}")

                with r4:
                    st.caption("Billing Type")
                    st.markdown(f"`{job.get('billing_type', 'NON_GST')}`")
                    if job.get("invoice_file_url"):
                        st.link_button("📥 Tax Invoice", job["invoice_file_url"], use_container_width=True)

        return

    # --- DIRECTORY VIEW: LIST ALL CUSTOMERS ---
    client_dict = {}
    for j in all_jobs:
        c_name = (j.get("client_name") or "Unnamed Client").strip()
        jid = j.get("job_id")
        j_val = job_val_map.get(jid, 0.0)

        if c_name not in client_dict:
            client_dict[c_name] = {
                "client_name": c_name,
                "contact_person": j.get("contact_person") or "N/A",
                "contact_phone": j.get("contact_phone") or "N/A",
                "orders_count": 0,
                "total_billed": 0.0,
                "active_jobs": 0,
            }

        client_dict[c_name]["orders_count"] += 1
        client_dict[c_name]["total_billed"] += j_val
        if j.get("current_stage") != "SETTLED":
            client_dict[c_name]["active_jobs"] += 1

    clients_list = list(client_dict.values())
    total_c = len(clients_list)
    total_val = sum(c["total_billed"] for c in clients_list)
    total_active_jobs = sum(c["active_jobs"] for c in clients_list)

    # Top KPI Ribbon
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="cust-kpi-card">
                <div class="cust-kpi-title">Total Clients</div>
                <div class="cust-kpi-val">{total_c}</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="cust-kpi-card">
                <div class="cust-kpi-title">Cumulative Booked Value</div>
                <div class="cust-kpi-val">₹ {total_val:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="cust-kpi-card">
                <div class="cust-kpi-title">Orders on Floor</div>
                <div class="cust-kpi-val" style="color: #E10600;">{total_active_jobs}</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        top_c = max(clients_list, key=lambda x: x["total_billed"])["client_name"] if clients_list else "None"
        st.markdown(f"""
            <div class="cust-kpi-card">
                <div class="cust-kpi-title">Top Account</div>
                <div class="cust-kpi-val" style="font-size: 18px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{top_c}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Controls
    s1, s2 = st.columns([3, 1])
    with s1:
        search_query = st.text_input("Search Clients", placeholder="Search by name, contact, or phone...", label_visibility="collapsed").strip().lower()
    with s2:
        sort_choice = st.selectbox("Sort", ["Highest Value", "Most Orders", "Alphabetical"], label_visibility="collapsed")

    filtered_clients = []
    for c in clients_list:
        if search_query:
            comb = f"{c['client_name']} {c['contact_person']} {c['contact_phone']}".lower()
            if search_query not in comb:
                continue
        filtered_clients.append(c)

    if sort_choice == "Highest Value":
        filtered_clients.sort(key=lambda x: x["total_billed"], reverse=True)
    elif sort_choice == "Most Orders":
        filtered_clients.sort(key=lambda x: x["orders_count"], reverse=True)
    else:
        filtered_clients.sort(key=lambda x: x["client_name"])

    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered_clients:
        st.info("No customer records match your search.")
        return

    # 3-Column Grid with Click-to-Open Action
    grid = st.columns(3)
    for idx, c in enumerate(filtered_clients):
        with grid[idx % 3]:
            with st.container(border=True):
                st.markdown(f"#### 🏢 {c['client_name']}")
                st.caption(f"👤 Contact: **{c['contact_person']}** | 📱 `{c['contact_phone']}`")

                st.markdown("---")

                m1, m2 = st.columns(2)
                with m1:
                    st.caption("Lifetime Value")
                    st.markdown(f"**₹ {c['total_billed']:,.2f}**")
                with m2:
                    st.caption("Orders")
                    st.markdown(f"**{c['orders_count']} Jobs**")

                if c["active_jobs"] > 0:
                    st.markdown(f"<span style='color:#E10600; font-size:11px; font-weight:700;'>🔥 {c['active_jobs']} active order(s) on floor</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#34D399; font-size:11px; font-weight:700;'>✅ All orders settled</span>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Button to open jobs list for this customer
                if st.button(f"📂 View Jobs ({c['orders_count']})", key=f"btn_open_c_{idx}", use_container_width=True, type="primary"):
                    st.session_state.selected_customer = c["client_name"]
                    st.rerun()