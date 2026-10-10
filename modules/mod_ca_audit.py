import streamlit as st
import pandas as pd
from datetime import date
from database import supabase, get_job_items


def render(user):
    st.subheader("🏛️ Module: CA & GST Tax Audit Desk")
    st.caption(
        f"Auditor / CA View | User: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    # 1. Fetch only GST Jobs
    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("billing_type", "GST")
            .order("job_id", desc=True)
            .execute()
        )
        gst_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching GST billing records: {e}")
        return

    if not gst_jobs:
        st.info("No GST billing records found in the system.")
        return

    # --- TOP METRICS BAR ---
    total_gst_orders = len(gst_jobs)
    
    # Pre-calculate aggregate taxable turnover
    total_taxable_turnover = 0.0
    for j in gst_jobs:
        items = get_job_items(j["job_id"])
        total_taxable_turnover += sum(float(it.get("amount", 0) or 0) for it in items)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total GST B2B Invoices", f"{total_gst_orders}")
    m2.metric("Total Taxable Value", f"₹ {total_taxable_turnover:,.2f}")
    m3.metric("Est. Total GST (18% avg)", f"₹ {(total_taxable_turnover * 0.18):,.2f}")

    st.markdown("---")

    # --- SEARCH & DATE FILTER BAR ---
    with st.container(border=True):
        st.markdown("##### 🔍 Audit Filter & Search")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            q_gstin = st.text_input("Filter by GSTIN", placeholder="e.g. 19AAAA...").strip().upper()
        with fc2:
            q_client = st.text_input("Filter by Client / Trade Name", placeholder="e.g. Apollo").strip().lower()
        with fc3:
            q_pos = st.selectbox(
                "Place of Supply",
                options=["All"] + sorted(list({str(j.get("place_of_supply") or "19 - West Bengal") for j in gst_jobs}))
            )

    # Filter application
    filtered = []
    for j in gst_jobs:
        if q_gstin and q_gstin not in str(j.get("gstin") or "").upper():
            continue
        if q_client and q_client not in str(j.get("client_name") or "").lower():
            continue
        if q_pos != "All" and str(j.get("place_of_supply")) != q_pos:
            continue
        filtered.append(j)

    st.caption(f"Showing **{len(filtered)}** verified GST record(s):")

    # --- EXPORT TO EXCEL / CSV BUTTON FOR CA FILING ---
    export_rows = []
    for j in filtered:
        items = get_job_items(j["job_id"])
        taxable_amt = sum(float(it.get("amount", 0) or 0) for it in items)
        
        # Check interstate (IGST vs CGST/SGST) assuming supplier in West Bengal (19)
        pos = str(j.get("place_of_supply") or "19 - West Bengal")
        is_interstate = not pos.startswith("19")
        
        gst_rate = 18.0  # Standard sign & print GST rate
        tax_amt = round(taxable_amt * (gst_rate / 100.0), 2)
        total_inv = taxable_amt + tax_amt

        # Ship to address fallback
        ship_to = items[0].get("delivery_address") if items and items[0].get("delivery_address") else j.get("billing_address")

        export_rows.append({
            "Job #": j.get("job_no"),
            "Challan #": j.get("challan_no") or f"CH-{j.get('job_no')}",
            "Client Name": j.get("client_name"),
            "GSTIN": j.get("gstin") or "N/A",
            "Bill-To Address": j.get("billing_address") or "N/A",
            "Ship-To Address": ship_to or "Same as Bill-To",
            "Place of Supply": pos,
            "Taxable Amount": taxable_amt,
            "CGST (9%)": 0.0 if is_interstate else round(tax_amt / 2, 2),
            "SGST (9%)": 0.0 if is_interstate else round(tax_amt / 2, 2),
            "IGST (18%)": tax_amt if is_interstate else 0.0,
            "Total Invoice Value": total_inv,
            "P.O. Number": j.get("po_no") or "N/A",
            "Order Date": str(j.get("created_at"))[:10],
            "Due Date": j.get("due_date")
        })

    if export_rows:
        df_export = pd.DataFrame(export_rows)
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export GST Report for GSTR-1 (CSV)",
            data=csv_data,
            file_name=f"GSTR1_Audit_Export_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")

    # --- DETAILED GST AUDIT CARDS ---
    for j in filtered:
        jid = j["job_id"]
        items = get_job_items(jid)
        taxable_amt = sum(float(it.get("amount", 0) or 0) for it in items)
        
        pos = str(j.get("place_of_supply") or "19 - West Bengal")
        is_interstate = not pos.startswith("19")
        tax_amt = round(taxable_amt * 0.18, 2)
        final_inv_val = taxable_amt + tax_amt

        # Destination / Ship-to address
        ship_addresses = [it.get("delivery_address") for it in items if it.get("delivery_address")]
        ship_to_str = ", ".join(set(ship_addresses)) if ship_addresses else (j.get("billing_address") or "Same as Bill-To Address")

        with st.container(border=True):
            # Header
            c_top1, c_top2, c_top3 = st.columns([3, 2, 2])
            with c_top1:
                st.markdown(f"### Job #{j.get('job_no')} — {j.get('client_name')}")
                st.markdown(f"🏛️ **GSTIN:** `{j.get('gstin') or 'NOT SPECIFIED'}`")
            with c_top2:
                st.markdown(f"📍 **Place of Supply:** `{pos}`")
                st.caption(f"Challan Ref: `{j.get('challan_no') or f'CH-{j.get('job_no')}'}`")
                if j.get("po_no"):
                    st.caption(f"Client P.O. #: `{j.get('po_no')}`")
            with c_top3:
                st.metric("Total Taxable Value", f"₹ {taxable_amt:,.2f}")
                st.caption(f"Gross Invoice (incl. 18% GST): **₹ {final_inv_val:,.2f}**")

            st.markdown("---")

            # Address Section
            a_col1, a_col2 = st.columns(2)
            with a_col1:
                st.markdown("##### 🏢 Bill To: Address")
                b_addr = j.get("billing_address") or "⚠️ No registered billing address entered"
                st.info(f"**{j.get('client_name')}**\n\n{b_addr}\n\n**GSTIN:** {j.get('gstin') or 'N/A'}")
            
            with a_col2:
                st.markdown("##### 🚚 Ship To: Address")
                st.success(f"**Consignee / Site:**\n\n{ship_to_str}\n\n**Contact:** {j.get('contact_person') or 'N/A'} ({j.get('contact_phone') or 'N/A'})")

            # Line Items & GST Computation Breakdown
            st.markdown("##### 📦 HSN & Line Items Breakdown")
            
            table_rows = []
            for it in items:
                amt = float(it.get("amount", 0) or 0)
                item_tax = round(amt * 0.18, 2)
                table_rows.append({
                    "Item Description": it.get("item_name"),
                    "HSN / SAC": "4911 / 9989",
                    "Qty": f"{it.get('quantity')} {it.get('unit')}",
                    "Rate (₹)": f"{float(it.get('rate', 0)):,.2f}",
                    "Taxable (₹)": f"{amt:,.2f}",
                    "CGST (9%)": "-" if is_interstate else f"₹ {round(item_tax/2, 2):,.2f}",
                    "SGST (9%)": "-" if is_interstate else f"₹ {round(item_tax/2, 2):,.2f}",
                    "IGST (18%)": f"₹ {item_tax:,.2f}" if is_interstate else "-",
                    "Total (₹)": f"{amt + item_tax:,.2f}"
                })

            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)