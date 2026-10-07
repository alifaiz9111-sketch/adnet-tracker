import streamlit as st
from database import supabase, get_job_items

def render(user):
    st.subheader("📋 Floor Operations & Multi-Filter Job Track")
    st.caption("Live monitoring of all active and past jobs across every stage, assignee/in-charge, and specifications.")

    try:
        res = supabase.table("jobs").select("*").order("job_id", desc=True).execute()
        all_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching jobs: {e}")
        return

    if not all_jobs:
        st.info("No jobs found in the system.")
        return

    # Multi-Filter Bar
    st.markdown("#### 🔍 Filter Job Directory")
    f_c1, f_c2, f_c3 = st.columns(3)
    with f_c1:
        f_job_no = st.text_input("Job Sheet #", placeholder="e.g. 1001").strip().lower()
        f_client = st.text_input("Client / Company Name", placeholder="e.g. Apollo").strip().lower()
    with f_c2:
        f_contact = st.text_input("Contact Person", placeholder="e.g. Subhashish").strip().lower()
        f_phone = st.text_input("Phone Number", placeholder="e.g. 9830").strip().lower()
    with f_c3:
        f_taken_by = st.text_input("Order Taken By", placeholder="e.g. Rahul").strip().lower()
        f_due_date = st.date_input("Target Delivery Date", value=None)

    filtered_jobs = []
    for j in all_jobs:
        if f_job_no and f_job_no not in str(j.get("job_no", "")).lower():
            continue
        if f_client and f_client not in str(j.get("client_name", "")).lower():
            continue
        if f_contact and f_contact not in str(j.get("contact_person", "")).lower():
            continue
        if f_phone and f_phone not in str(j.get("contact_phone", "")).lower():
            continue
        if f_taken_by and f_taken_by not in str(j.get("order_taken_by", "")).lower():
            continue
        if f_due_date and str(j.get("due_date", "")) != str(f_due_date):
            continue
        filtered_jobs.append(j)

    st.markdown(f"**Showing {len(filtered_jobs)} matching job(s):**")
    st.markdown("---")

    stage_display_map = {
        "SALES": ("📝 Order Intake", "#8B949E"),
        "DESIGN": ("🎨 Design & Proofs", "#58A6FF"),
        "PAYMENT": ("💳 Advance / Accounts", "#D29922"),
        "PRODUCTION": ("⚙️ Production Floor", "#BC8CFF"),
        "QC": ("🔍 Quality Check (QC)", "#DB6D28"),
        "DISPATCH": ("🚚 Dispatch & Delivery", "#3FB950"),
        "BILLING_REVIEW": ("🧾 Billing Review", "#F0883E"),
        "BILLING_QUEUE": ("💼 CA Invoicing Queue", "#1F6FEB"),
        "SETTLED": ("🗄️ Billed & Settled", "#238636")
    }

    for job in filtered_jobs:
        curr_stage = job.get("current_stage", "UNKNOWN")
        stage_label, stage_color = stage_display_map.get(curr_stage, (curr_stage, "#8B949E"))
        items = get_job_items(job["job_id"])

        with st.container(border=True):
            h_col1, h_col2, h_col3 = st.columns([2.5, 2.5, 2])
            with h_col1:
                st.markdown(f"### Job Sheet #{job.get('job_no')} `(ID: {job.get('job_id')})`")
                st.markdown(f"**Client / Company:** {job.get('client_name')}")
                st.caption(f"👤 Contact Person: `{job.get('contact_person') or 'N/A'}` | 📱 Phone: `{job.get('contact_phone') or 'N/A'}`")
            with h_col2:
                st.markdown(f"**Current Stage:** <span style='color:{stage_color}; font-weight:bold;'>{stage_label}</span>", unsafe_allow_html=True)
                holder_name = job.get("returned_by") if job.get("is_returned") else job.get("order_taken_by", "Floor Desk")
                st.markdown(f"**Currently Holding / In-Charge:** `{holder_name}`")
                st.caption(f"📅 Target Delivery Date: `{job.get('due_date') or 'N/A'}` | Order Taken By: `{job.get('order_taken_by') or 'N/A'}`")
            with h_col3:
                total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                if job.get("is_returned"):
                    st.error(f"⚠️ Returned by {job.get('returned_by')}: {job.get('return_reason')}")

            st.markdown("##### 📦 Ordered Line Items & Job Descriptions")
            if not items:
                st.caption("No line items logged for this job.")
            else:
                for idx, it in enumerate(items, 1):
                    del_status = "✅ Delivered" if it.get("is_delivered") else "⏳ Pending Delivery"
                    st.markdown(
                        f"**{idx}. {it.get('item_name', 'Unnamed Item')}** — "
                        f"Qty: `{it.get('quantity')} {it.get('unit')}` | "
                        f"Rate: `₹{float(it.get('rate', 0)):,.2f}` | "
                        f"Amount: `₹{float(it.get('amount', 0)):,.2f}` | "
                        f"Status: `{del_status}`"
                    )
                    if it.get("specifications"):
                        st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;📝 **Description / Specs:** {it.get('specifications')}")
                    if it.get("delivery_address"):
                        st.caption(f"&nbsp;&nbsp;&nbsp;&nbsp;📍 **Address / Branch:** {it.get('delivery_address')}")