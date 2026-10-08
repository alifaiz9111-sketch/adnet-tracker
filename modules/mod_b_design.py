import streamlit as st
from database import supabase, get_job_items, claim_design_job


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
        jobs = res.data or []
    except Exception as e:
        st.error(f"Error fetching design queue: {e}")
        return

    is_privileged = user.get("account_type") in ["SUPER_ADMIN", "CEO"]

    # Filter queue: Privileged see all; individual designers see unclaimed jobs OR jobs assigned to them
    visible_jobs = []
    for j in jobs:
        assigned = j.get("assigned_designer")
        if is_privileged or not assigned or assigned == "OPEN_POOL" or assigned == user["full_name"]:
            visible_jobs.append(j)

    if not visible_jobs:
        st.info("No design jobs pending in your queue.")
        return

    for job in visible_jobs:
        items = get_job_items(job["job_id"])
        assigned_to = job.get("assigned_designer")
        is_open_pool = not assigned_to or assigned_to == "OPEN_POOL"
        is_my_job = assigned_to == user["full_name"]

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.5, 2.5, 2])
            with c1:
                st.markdown(f"### Job #{job.get('job_no')} - {job.get('client_name')}")
                st.caption(
                    f"👤 Contact: `{job.get('contact_person') or 'N/A'}` | 📱 `{job.get('contact_phone') or 'N/A'}`"
                )
                st.caption(
                    f"📅 Target Date: `{job.get('due_date')}` | Booked By: `{job.get('order_taken_by') or 'N/A'}`"
                )
                
                # Assignment badge
                if is_open_pool:
                    st.warning("📢 **Open Pool (Unclaimed)**")
                else:
                    st.info(f"🎨 Assigned Designer: **{assigned_to}**")

                if job.get("is_returned"):
                    st.error(
                        f"⚠️ Returned by {job.get('returned_by')}: {job.get('return_reason')}"
                    )

            with c2:
                st.markdown("##### 📦 Ordered Items & Design Specs")
                for idx, it in enumerate(items, 1):
                    st.markdown(
                        f"**{idx}. {it.get('item_name')}** ({it.get('quantity')} {it.get('unit')})"
                    )
                    if it.get("specifications"):
                        st.caption(f"&nbsp;&nbsp;📐 Specs: {it.get('specifications')}")

            with c3:
                # Price visible only to CEO and Admin
                if is_privileged:
                    total_val = sum(float(it.get("amount", 0) or 0) for it in items)
                    st.metric("Total Order Value", f"₹ {total_val:,.2f}")

                # If open pool, show Claim button first
                if is_open_pool and not is_privileged:
                    if st.button("✋ Claim Job", key=f"btn_claim_{job['job_id']}", type="primary", use_container_width=True):
                        ok, msg = claim_design_job(job["job_id"], user["full_name"])
                        if ok:
                            st.success(f"Job #{job.get('job_no')} assigned to you!")
                            st.rerun()
                        else:
                            st.error(msg)
                
                # If claimed/assigned to current user OR CEO/Admin, show Approved button
                elif is_my_job or is_privileged:
                    if st.button(
                        "Approved",
                        key=f"btn_app_{job['job_id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            update_data = {
                                "current_stage": "PAYMENT",
                                "is_returned": False,
                            }
                            # Ensure designer is noted
                            if is_open_pool and is_privileged:
                                update_data["assigned_designer"] = user["full_name"]

                            supabase.table("jobs").update(update_data).eq(
                                "job_id", int(job["job_id"])
                            ).execute()
                            st.success(
                                f"Job #{job.get('job_no')} approved and forwarded to Payment Desk."
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error approving job: {e}")
                else:
                    st.caption(f"🔒 Locked to {assigned_to}")