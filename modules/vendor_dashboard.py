import streamlit as st
from database import (
    supabase,
    get_all_vendors,
    create_vendor,
    update_vendor_status,
    delete_vendor,
    get_job_items
)


def render(user):
    st.markdown("""
        <style>
        .vnd-kpi-card {
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px 20px;
        }
        .vnd-kpi-title {
            font-size: 11px;
            font-weight: 700;
            color: #8B949E;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .vnd-kpi-val {
            font-size: 24px;
            font-weight: 800;
            color: #E6EDF3;
            margin-top: 4px;
        }
        .vnd-badge-active {
            background: rgba(16, 185, 129, 0.15);
            color: #34D399;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 12px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .vnd-badge-inactive {
            background: rgba(225, 6, 0, 0.15);
            color: #F87171;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 12px;
            border: 1px solid rgba(225, 6, 0, 0.3);
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
    if "selected_vendor" not in st.session_state:
        st.session_state.selected_vendor = None

    vendors = get_all_vendors() or []

    # Fetch jobs to match outsourced vendor assignments
    try:
        j_res = supabase.table("jobs").select("*").order("job_id", desc=True).execute()
        all_jobs = j_res.data or []
    except Exception:
        all_jobs = []

    # --- DRILL-DOWN VIEW: JOBS OUTSOURCED TO SELECTED VENDOR ---
    if st.session_state.selected_vendor:
        v_name = st.session_state.selected_vendor

        # Matches jobs assigned to this vendor via assigned_designer, return_reason or remarks
        vendor_jobs = [
            j for j in all_jobs
            if v_name.lower() in str(j.get("assigned_designer", "")).lower()
            or v_name.lower() in str(j.get("payment_remarks", "")).lower()
            or v_name.lower() in str(j.get("return_reason", "")).lower()
        ]

        v_header_col, v_back_col = st.columns([5, 1.2])
        with v_header_col:
            st.markdown(f"### 🏭 Outsourced Jobs: <span style='color:#E10600;'>{v_name}</span>", unsafe_allow_html=True)
            st.caption(f"Showing all floor jobs and subcontracted orders tied to {v_name}.")
        with v_back_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("⬅️ Back to Directory", use_container_width=True, type="secondary"):
                st.session_state.selected_vendor = None
                st.rerun()

        st.markdown("---")

        if not vendor_jobs:
            st.info(f"No outsourced jobs currently logged for '{v_name}'. When outsourcing from Module 4 (Production Floor), select this vendor to track tasks here.")
            return

        for job in vendor_jobs:
            items = get_job_items(job["job_id"])
            total_val = sum(float(it.get("amount", 0) or 0) for it in items)
            is_settled = job.get("current_stage") == "SETTLED"
            is_ret = job.get("is_returned", False)

            with st.container(border=True):
                r1, r2, r3, r4 = st.columns([2, 3, 2, 1.5])
                with r1:
                    st.markdown(f"#### #{job.get('job_no')} — {job.get('client_name')}")
                    if is_ret:
                        st.markdown("<span class='status-pill pill-red'>● REWORK REQUIRED</span>", unsafe_allow_html=True)
                    elif is_settled:
                        st.markdown("<span class='status-pill pill-green'>● SETTLED</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='status-pill pill-amber'>● {job.get('current_stage')}</span>", unsafe_allow_html=True)
                    st.caption(f"Due Date: `{job.get('due_date')}`")

                with r2:
                    st.markdown(f"**Contact:** `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
                    st.caption(f"Order Booked by: `{job.get('order_taken_by') or 'Sales'}`")
                    if items:
                        item_str = ", ".join([f"{it.get('item_name')} ({it.get('quantity')} {it.get('unit')})" for it in items])
                        st.caption(f"⚙️ Specs: {item_str[:75]}{'...' if len(item_str) > 75 else ''}")

                with r3:
                    st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                    adv = float(job.get("advance_received", 0) or 0)
                    bal = float(job.get("balance_amount", 0) or 0)
                    st.caption(f"Adv: ₹{adv:,.0f} | Bal: ₹{bal:,.0f}")

                with r4:
                    st.caption("Floor Status")
                    st.markdown(f"`{job.get('current_stage')}`")

        return

    # --- DIRECTORY VIEW: LIST ALL VENDORS ---
    total_v = len(vendors)
    active_v = sum(1 for v in vendors if v.get("is_active", True))
    inactive_v = total_v - active_v

    # Top KPI Ribbon
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class="vnd-kpi-card">
                <div class="vnd-kpi-title">Total Vendors</div>
                <div class="vnd-kpi-val">{total_v}</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class="vnd-kpi-card">
                <div class="vnd-kpi-title">Active Partners</div>
                <div class="vnd-kpi-val" style="color: #34D399;">{active_v}</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="vnd-kpi-card">
                <div class="vnd-kpi-title">Inactive / On Hold</div>
                <div class="vnd-kpi-val" style="color: #F87171;">{inactive_v}</div>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        top_name = vendors[0].get("vendor_name") if vendors else "None"
        st.markdown(f"""
            <div class="vnd-kpi-card">
                <div class="vnd-kpi-title">Primary Partner</div>
                <div class="vnd-kpi-val" style="font-size: 18px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{top_name}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Controls & Add New
    c_srch, c_flt, c_btn = st.columns([3, 1.5, 1.5])
    with c_srch:
        srch_query = st.text_input("Search Vendors", placeholder="Search by name, contact, category, city...", label_visibility="collapsed").strip().lower()
    with c_flt:
        status_filter = st.selectbox("Status", ["All Vendors", "Active Only", "Inactive Only"], label_visibility="collapsed")
    with c_btn:
        with st.popover("➕ Add New Vendor", use_container_width=True):
            st.markdown("#### Register New Vendor")
            v_name = st.text_input("Company / Trade Name *", key="vnd_add_nm").strip()
            v_contact = st.text_input("Contact Person", key="vnd_add_cp").strip()
            v_phone = st.text_input("Phone Number", key="vnd_add_ph").strip()
            v_cat = st.text_input("Specialization (e.g. Laser, CNC, Offset)", key="vnd_add_cat").strip()
            v_city = st.text_input("City", value="Kolkata", key="vnd_add_city").strip()

            if st.button("Save Vendor", type="primary", use_container_width=True, key="vnd_save_btn"):
                if not v_name:
                    st.error("Company Name is required.")
                else:
                    ok, msg = create_vendor(v_name, v_contact, v_phone, v_cat, v_city)
                    if ok:
                        st.success(f"Vendor '{v_name}' added successfully!")
                        st.rerun()
                    else:
                        st.error(msg)

    # Filter Logic
    display_vendors = []
    for v in vendors:
        is_act = v.get("is_active", True)
        if status_filter == "Active Only" and not is_act:
            continue
        if status_filter == "Inactive Only" and is_act:
            continue
        if srch_query:
            combined = f"{v.get('vendor_name', '')} {v.get('contact_person', '')} {v.get('category', '')} {v.get('city', '')}".lower()
            if srch_query not in combined:
                continue
        display_vendors.append(v)

    st.markdown("<br>", unsafe_allow_html=True)

    if not display_vendors:
        st.info("No vendor profiles found matching the criteria.")
        return

    # 3-Column Grid with Click-to-Open Action
    grid_cols = st.columns(3)
    for idx, v in enumerate(display_vendors):
        v_id = v.get("vendor_id")
        v_name = v.get("vendor_name", "Vendor")
        is_act = v.get("is_active", True)
        badge_html = '<span class="vnd-badge-active">● Active</span>' if is_act else '<span class="vnd-badge-inactive">● Inactive</span>'

        # Count outsourced jobs
        v_job_count = sum(
            1 for j in all_jobs 
            if v_name.lower() in str(j.get("assigned_designer", "")).lower()
            or v_name.lower() in str(j.get("payment_remarks", "")).lower()
            or v_name.lower() in str(j.get("return_reason", "")).lower()
        )

        with grid_cols[idx % 3]:
            with st.container(border=True):
                h1, h2 = st.columns([3.8, 2.2])
                with h1:
                    st.markdown(f"#### 🏭 {v_name}")
                    st.caption(f"Category: `{v.get('category') or 'General Job-Work'}`")
                with h2:
                    st.markdown(f"<div style='text-align: right;'>{badge_html}</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.caption(f"👤 Contact: **{v.get('contact_person') or 'N/A'}** | 📱 `{v.get('phone') or 'N/A'}`")
                st.caption(f"📍 City: {v.get('city') or 'Kolkata'}")

                st.markdown("<br>", unsafe_allow_html=True)

                # Button to open jobs list for this vendor
                if st.button(f"📋 View Outsourced Jobs ({v_job_count})", key=f"btn_open_v_{idx}", use_container_width=True, type="primary"):
                    st.session_state.selected_vendor = v_name
                    st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)

                act1, act2 = st.columns(2)
                with act1:
                    btn_lbl = "Deactivate" if is_act else "Reactivate"
                    if st.button(btn_lbl, key=f"tog_v_{v_id}", use_container_width=True):
                        update_vendor_status(v_id, not is_act)
                        st.rerun()
                with act2:
                    with st.popover("⚙️ Delete", use_container_width=True):
                        st.caption(f"Delete {v_name} permanently?")
                        if st.button("Confirm Delete", key=f"del_v_{v_id}", type="primary", use_container_width=True):
                            delete_vendor(v_id)
                            st.success("Deleted.")
                            st.rerun()