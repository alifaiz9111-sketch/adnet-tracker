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
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 👥 Customer & Client Master Directory")
    st.caption("Commercial accounts, lifetime booking totals, and active floor order tracking.")

    try:
        j_res = supabase.table("jobs").select("*").execute()
        all_jobs = j_res.data or []
        i_res = supabase.table("job_items").select("*").execute()
        all_items = i_res.data or []
    except Exception as e:
        st.error(f"Error fetching customer data: {e}")
        return

    # Map job totals
    job_val_map = {}
    for it in all_items:
        jid = it.get("job_id")
        job_val_map[jid] = job_val_map.get(jid, 0.0) + float(it.get("amount", 0) or 0)

    # Aggregate client metadata
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
                "last_order_date": str(j.get("created_at", ""))[:10]
            }

        client_dict[c_name]["orders_count"] += 1
        client_dict[c_name]["total_billed"] += j_val
        if j.get("current_stage") != "SETTLED":
            client_dict[c_name]["active_jobs"] += 1

    clients_list = list(client_dict.values())
    total_c = len(clients_list)
    total_val = sum(c["total_billed"] for c in clients_list)
    total_active_jobs = sum(c["active_jobs"] for c in clients_list)

    # --- TOP KPI RIBBON (Reference Image 1) ---
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

    # --- SEARCH & SORT CONTROLS ---
    s1, s2 = st.columns([3, 1])
    with s1:
        search_query = st.text_input("Search Clients", placeholder="Search by client name, contact person, or phone...", label_visibility="collapsed").strip().lower()
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

    # --- 3-COLUMN CARD GRID (Reference Image 1) ---
    grid = st.columns(3)
    for idx, c in enumerate(filtered_clients):
        with grid[idx % 3]:
            with st.container(border=True):
                st.markdown(f"#### 🏢 {c['client_name']}")
                st.caption(f"👤 Contact Person: **{c['contact_person']}**")
                st.caption(f"📱 Phone: `{c['contact_phone']}`")

                st.markdown("---")

                m1, m2 = st.columns(2)
                with m1:
                    st.caption("Lifetime Value")
                    st.markdown(f"**₹ {c['total_billed']:,.2f}**")
                with m2:
                    st.caption("Total Orders")
                    st.markdown(f"**{c['orders_count']} Jobs**")

                if c["active_jobs"] > 0:
                    st.markdown(f"<span style='color:#E10600; font-size:12px; font-weight:700;'>🔥 {c['active_jobs']} active order(s) on floor</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color:#34D399; font-size:12px; font-weight:700;'>✅ All orders settled</span>", unsafe_allow_html=True)