from datetime import date, datetime
import streamlit as st
from database import supabase, get_job_items, claim_design_job, reject_job_to_sales


def render(user):
    st.subheader("🎨 Module 2: Design, Proofing & Pre-Press Desk")
    st.caption(
        f"Graphic Artist / Pre-Press: **{user['full_name']}** | Role: `{user.get('account_type')}`"
    )

    try:
        res = (
            supabase.table("jobs")
            .select("*")
            .eq("current_stage", "DESIGN")
            .order("job_id")
            .execute()
        )
        all_design_jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching design queue: {e}")
        return

    is_privileged = user.get("account_type") in ["SUPER_ADMIN", "CEO"]

    # --- TASK SEGREGATION QUEUES ---
    qc_returns = [j for j in all_design_jobs if j.get("is_returned")]
    
    my_active = [
        j for j in all_design_jobs 
        if not j.get("is_returned") and (
            is_privileged or j.get("assigned_designer") == user["full_name"]
        )
    ]
    
    open_pool = [
        j for j in all_design_jobs 
        if not j.get("is_returned") and (
            not j.get("assigned_designer") or j.get("assigned_designer") == "OPEN_POOL"
        )
    ]

    t_active, t_pool, t_returns = st.tabs([
        f"📌 My Active Desk ({len(my_active)})",
        f"📢 Open Claim Pool ({len(open_pool)})",
        f"🚨 QC Returns / Corrections ({len(qc_returns)})"
    ])

    def render_job_card(job, mode="active"):
        items = get_job_items(job["job_id"])
        assigned_to = job.get("assigned_designer")
        is_open = not assigned_to or assigned_to == "OPEN_POOL"
        is_mine = assigned_to == user["full_name"]

        # Urgent badge check (due within 24 hours or overdue)
        is_urgent = False
        if job.get("due_date"):
            try:
                due_d = datetime.strptime(str(job["due_date"]), "%Y-%m-%d").date()
                if (due_d - date.today()).days <= 1:
                    is_urgent = True
            except Exception:
                pass

        with st.container(border=True):
            # 1. Job Header Card
            c_head1, c_head2, c_head3 = st.columns([3, 2, 1.5])
            with c_head1:
                st.markdown(f"### Job #{job.get('job_no')} — {job.get('client_name')}")
                st.caption(f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`")
            with c_head2:
                due_display = f"📅 Target Due: **{job.get('due_date')}**"
                if is_urgent:
                    st.error(f"🔥 **URGENT** | {due_display}")
                else:
                    st.info(f"⏳ Normal | {due_display}")
                st.caption(f"Sales Rep: **{job.get('order_taken_by') or 'N/A'}**")
            with c_head3:
                if is_open:
                    st.warning("📢 Unclaimed")
                else:
                    st.success(f"🎨 `{assigned_to}`")

            if job.get("is_returned"):
                st.error(f"⚠️ **Flagged Issue / Return:** {job.get('return_reason')} (Reported by: {job.get('returned_by', 'Floor')})")

            st.markdown("---")

            # 2. Pre-Press Spec Viewer & Commercial Masking
            c_specs, c_actions = st.columns([4, 2])
            with c_specs:
                st.markdown("##### 📐 Pre-Press Production Specifications")
                for idx, it in enumerate(items, 1):
                    with st.container():
                        st.markdown(f"**{idx}. {it.get('item_name')}** — `Qty: {it.get('quantity')} {it.get('unit')}`")
                        raw_spec = it.get("specifications") or "No technical notes entered."
                        st.code(raw_spec, language="markdown")

            with c_actions:
                # Commercial Masking: Price ONLY visible to Super Admin / CEO
                if is_privileged:
                    total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                    st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                else:
                    st.caption("🔒 *Commercial pricing masked for Pre-Press.*")

                st.markdown("<br>", unsafe_allow_html=True)

                # 3. Action & Routing Controls
                if is_open and not is_privileged:
                    if st.button("✋ Claim Job", key=f"btn_claim_{job['job_id']}", type="primary", use_container_width=True):
                        ok, msg = claim_design_job(job["job_id"], user["full_name"])
                        if ok:
                            st.success("Job locked to your desk.")
                            st.rerun()
                        else:
                            st.error(msg)
                
                elif is_mine or is_privileged:
                    # Approved Button
                    if st.button("✅ Approved", key=f"btn_app_{job['job_id']}", type="primary", use_container_width=True):
                        try:
                            update_data = {
                                "current_stage": "PAYMENT",
                                "is_returned": False,
                                "return_reason": None
                            }
                            if is_open and is_privileged:
                                update_data["assigned_designer"] = user["full_name"]

                            supabase.table("jobs").update(update_data).eq("job_id", int(job["job_id"])).execute()
                            st.success(f"Job #{job.get('job_no')} approved and pushed to Accounts (PAYMENT).")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Approval failed: {e}")

                    # Flag Spec Issue Popover
                    with st.popover("⚠️ Flag Spec Issue", use_container_width=True):
                        st.caption("Send revision request back to Sales intake.")
                        issue_note = st.text_input("Discrepancy / Clarification Details *", key=f"iss_{job['job_id']}")
                        if st.button("Submit Issue to Sales", key=f"btn_flag_{job['job_id']}", type="secondary", use_container_width=True):
                            if not issue_note.strip():
                                st.error("Please enter specific discrepancy details.")
                            else:
                                ok, flag_msg = reject_job_to_sales(job["job_id"], user["full_name"], issue_note)
                                if ok:
                                    st.warning(flag_msg)
                                    st.rerun()
                                else:
                                    st.error(flag_msg)
                else:
                    st.caption(f"🔒 Locked to {assigned_to}")

    # Render each tab queue
    with t_active:
        if not my_active:
            st.info("No active design jobs assigned to your desk.")
        else:
            for j in my_active:
                render_job_card(j, mode="active")

    with t_pool:
        if not open_pool:
            st.info("Open claim pool is clear. No unassigned broadcasts.")
        else:
            for j in open_pool:
                render_job_card(j, mode="pool")

    with t_returns:
        if not qc_returns:
            st.success("No returned or flagged spec issues pending correction.")
        else:
            for j in qc_returns:
                render_job_card(j, mode="return")