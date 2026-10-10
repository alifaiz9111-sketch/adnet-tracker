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

    # --- MUTUALLY EXCLUSIVE TASK QUEUES ---
    # 1. Flagged or QC returns
    qc_returns = [j for j in all_design_jobs if j.get("is_returned")]

    # 2. Open broadcast jobs (not claimed by anyone)
    open_pool = [
        j for j in all_design_jobs 
        if not j.get("is_returned") and (
            not j.get("assigned_designer") or j.get("assigned_designer") == "OPEN_POOL"
        )
    ]

    # 3. Active assigned jobs:
    # For Admin/CEO: show all assigned jobs that are NOT open pool and NOT returned
    # For regular designer: show only jobs specifically assigned to them
    if is_privileged:
        my_active = [
            j for j in all_design_jobs 
            if not j.get("is_returned") and j.get("assigned_designer") and j.get("assigned_designer") != "OPEN_POOL"
        ]
    else:
        my_active = [
            j for j in all_design_jobs 
            if not j.get("is_returned") and j.get("assigned_designer") == user["full_name"]
        ]

    t_active, t_pool, t_returns, t_hist = st.tabs([
        f"📌 Active Assigned Desk ({len(my_active)})",
        f"📢 Open Claim Pool ({len(open_pool)})",
        f"🚨 QC Returns / Corrections ({len(qc_returns)})",
        "📜 Design Work History"
    ])

    def render_job_card(job, mode="active"):
        items = get_job_items(job["job_id"])
        assigned_to = job.get("assigned_designer")
        is_open = not assigned_to or assigned_to == "OPEN_POOL"
        is_mine = assigned_to == user["full_name"]

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
                if is_privileged:
                    total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                    st.metric("Total Order Value", f"₹ {total_val:,.2f}")
                else:
                    st.caption("🔒 *Commercial pricing masked for Pre-Press.*")

                st.markdown("<br>", unsafe_allow_html=True)

                # 3. Action & Routing Controls with Unique Keys per Tab Mode
                if is_open and not is_privileged:
                    if st.button("✋ Claim Job", key=f"btn_claim_{mode}_{job['job_id']}", type="primary", use_container_width=True):
                        ok, msg = claim_design_job(job["job_id"], user["full_name"])
                        if ok:
                            st.success("Job locked to your desk.")
                            st.rerun()
                        else:
                            st.error(msg)
                
                elif is_mine or is_privileged or mode == "return":
                    # Approved Button
                    if st.button("✅ Approved", key=f"btn_app_{mode}_{job['job_id']}", type="primary", use_container_width=True):
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
                        issue_note = st.text_input("Discrepancy Details *", key=f"iss_{mode}_{job['job_id']}")
                        if st.button("Submit Issue to Sales", key=f"btn_flag_{mode}_{job['job_id']}", type="secondary", use_container_width=True):
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

    # Render tabs
    with t_active:
        if not my_active:
            st.info("No active design jobs assigned.")
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

    with t_hist:
        st.markdown("#### 📜 Archive: Completed & Ongoing Design Work")

        # Fetch all jobs that have ever had a designer assigned, sorted latest first by date & time
        try:
            h_res = (
                supabase.table("jobs")
                .select("*")
                .not_.is_("assigned_designer", "null")
                .order("created_at", desc=True)
                .execute()
            )
            raw_history_jobs = h_res.data or []
        except Exception as e:
            st.error(f"Error loading design history: {e}")
            raw_history_jobs = []

        is_elevated = user.get("account_type") in ["SUPER_ADMIN", "CEO", "MANAGER"]

        # Dropdown filtering for Admin, Manager, and CEO
        if is_elevated:
            all_designer_names = sorted(list({
                str(j.get("assigned_designer")).strip()
                for j in raw_history_jobs
                if j.get("assigned_designer") and j.get("assigned_designer") != "OPEN_POOL"
            }))
            filter_options = ["All Designers"] + all_designer_names

            selected_designer = st.selectbox(
                "Filter by Designer",
                options=filter_options,
                index=0,
                key="des_hist_filter_dropdown"
            )

            if selected_designer == "All Designers":
                filtered_history = raw_history_jobs
            else:
                filtered_history = [
                    j for j in raw_history_jobs
                    if str(j.get("assigned_designer", "")).strip() == selected_designer
                ]
        else:
            # Regular designer sees only their completed/active design work
            filtered_history = [
                j for j in raw_history_jobs
                if str(j.get("assigned_designer", "")).strip().lower() == user["full_name"].lower()
            ]

        st.caption(f"Showing **{len(filtered_history)}** design record(s) sorted by latest date and time:")
        st.markdown("---")

        if not filtered_history:
            st.info("No design work records found matching the criteria.")
        else:
            for job in filtered_history:
                jid = job["job_id"]
                items = get_job_items(jid)
                stage = job.get("current_stage", "DESIGN")
                is_ret = job.get("is_returned", False)

                # Format created timestamp
                created_dt = str(job.get("created_at", ""))[:19].replace("T", " ")

                with st.container(border=True):
                    hc1, hc2, hc3 = st.columns([3, 3, 2])

                    with hc1:
                        st.markdown(f"#### #{job.get('job_no')} — {job.get('client_name')}")
                        st.caption(f"🕒 Created: `{created_dt}`")
                        st.caption(f"📅 Target Due: `{job.get('due_date')}`")
                        
                        if is_ret:
                            st.markdown("<span style='color:#F87171; font-weight:700;'>● Defect / Returned</span>", unsafe_allow_html=True)
                        elif stage == "SETTLED":
                            st.markdown("<span style='color:#34D399; font-weight:700;'>● Settled / Complete</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color:#FBBF24; font-weight:700;'>● Stage: {stage}</span>", unsafe_allow_html=True)

                    with hc2:
                        st.markdown(f"🎨 **Assigned Designer:** `{job.get('assigned_designer') or 'Unassigned'}`")
                        st.caption(f"👤 Contact: **{job.get('contact_person') or 'N/A'}** ({job.get('contact_phone') or 'N/A'})")
                        st.caption(f"Sales Rep: `{job.get('order_taken_by') or 'N/A'}`")
                        if items:
                            item_str = ", ".join([f"{it.get('item_name')} (Qty: {it.get('quantity')} {it.get('unit')})" for it in items])
                            st.caption(f"📦 Items: {item_str}")

                    with hc3:
                        proof_url = job.get("proof_file_url")
                        if proof_url:
                            st.link_button("👁️ View Proof File", proof_url, use_container_width=True)
                        else:
                            st.caption("No proof file attached")

                        if is_elevated:
                            tot_val = sum(float(it.get("amount", 0) or 0) for it in items)
                            st.caption(f"Order Value: **₹ {tot_val:,.2f}**")