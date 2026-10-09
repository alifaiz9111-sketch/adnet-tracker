import streamlit as st
from database import (
    get_all_vendors,
    create_vendor,
    update_vendor_status,
    delete_vendor
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
        .vnd-fin-box {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 12px;
            display: flex;
            justify-content: space-between;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏢 Vendor & Trade Partners Directory")
    st.caption(f"Commercial fabrication workshops, outsource printers & trade suppliers | In-charge: **{user['full_name']}**")

    vendors = get_all_vendors() or []
    total_v = len(vendors)
    active_v = sum(1 for v in vendors if v.get("is_active", True))
    inactive_v = total_v - active_v

    # --- TOP KPI RIBBON (Reference Image 3) ---
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

    # --- CONTROLS & ADD NEW VENDOR ---
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

    # --- 3-COLUMN CARD GRID (Reference Image 3) ---
    grid_cols = st.columns(3)
    for idx, v in enumerate(display_vendors):
        v_id = v.get("vendor_id")
        is_act = v.get("is_active", True)
        badge_html = '<span class="vnd-badge-active">● Active</span>' if is_act else '<span class="vnd-badge-inactive">● Inactive</span>'

        with grid_cols[idx % 3]:
            with st.container(border=True):
                h1, h2 = st.columns([3.8, 2.2])
                with h1:
                    st.markdown(f"#### 🏭 {v.get('vendor_name')}")
                    st.caption(f"Specialization: `{v.get('category') or 'General Job-Work'}`")
                with h2:
                    st.markdown(f"<div style='text-align: right;'>{badge_html}</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.caption(f"👤 Contact Person: **{v.get('contact_person') or 'N/A'}**")
                st.caption(f"📱 Phone: `{v.get('phone') or 'N/A'}`")
                st.caption(f"📍 City: `{v.get('city') or 'Kolkata'}`")

                st.markdown("""
                    <div class="vnd-fin-box">
                        <div>
                            <div style="font-size: 10px; color: #8B949E; font-weight: 700;">PAYMENT TERMS</div>
                            <div style="font-size: 12px; font-weight: 800; color: #E6EDF3;">Outsourced Trade</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #8B949E; font-weight: 700;">FLOOR STATUS</div>
                            <div style="font-size: 12px; font-weight: 800; color: #34D399;">Available</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                act1, act2 = st.columns(2)
                with act1:
                    btn_lbl = "Deactivate" if is_act else "Reactivate"
                    if st.button(btn_lbl, key=f"tog_v_{v_id}", use_container_width=True):
                        update_vendor_status(v_id, not is_act)
                        st.rerun()
                with act2:
                    with st.popover("⚙️ Options", use_container_width=True):
                        st.caption(f"Permanently remove {v.get('vendor_name')}?")
                        if st.button("🗑️ Delete Vendor", key=f"del_v_{v_id}", type="primary", use_container_width=True):
                            delete_vendor(v_id)
                            st.success("Deleted.")
                            st.rerun()