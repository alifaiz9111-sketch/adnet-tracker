import os
from datetime import datetime
import pytz
import streamlit as st
from supabase import create_client, Client

IST = pytz.timezone("Asia/Kolkata")

# Credentials strictly via secrets or env (No hardcoded fallback secrets)
SUPABASE_URL = ""
SUPABASE_KEY = ""

try:
    if "supabase" in st.secrets:
        SUPABASE_URL = st.secrets["supabase"].get("url", "")
        SUPABASE_KEY = st.secrets["supabase"].get("key", "")
    elif "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
except Exception:
    pass

if not SUPABASE_URL:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
if not SUPABASE_KEY:
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase credentials missing! Configure SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets or Environment Variables.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- FLASH MESSAGE UTILITY ---

def flash(msg: str, kind: str = "success"):
    """Stores temporary banner/toast messages across st.rerun()."""
    st.session_state["_flash"] = (kind, msg)

def show_flash():
    """Displays queued message at the top of the workspace."""
    f = st.session_state.pop("_flash", None)
    if f:
        kind, msg = f
        if kind == "success":
            st.toast(msg, icon="✅")
        elif kind == "error":
            st.error(msg)
        elif kind == "warning":
            st.warning(msg)
        else:
            st.info(msg)


# --- BATCH QUERY HELPERS (BYPASS 1000 ROW LIMIT) ---

def fetch_all(query_fn, page_size: int = 1000):
    """Paginates queries through Supabase to bypass the hard 1000-record threshold."""
    rows = []
    start = 0
    while True:
        res = query_fn().range(start, start + page_size - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows

def get_items_for_jobs(job_ids: list):
    """Batched query returning items mapped by job_id."""
    out = {}
    ids = list(set(job_ids))
    if not ids:
        return out
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        res = supabase.table("job_items").select("*").in_("job_id", chunk).order("item_id").execute()
        for it in (res.data or []):
            out.setdefault(it["job_id"], []).append(it)
    return out


# --- AUDIT & AUTHENTICATION ---

def log_audit(user_id, action, details=""):
    try:
        u_id = int(user_id) if user_id and str(user_id).isdigit() else None
        payload = {
            "user_id": u_id,
            "action": action,
            "details": details,
            "created_at": datetime.now(IST).isoformat()
        }
        supabase.table("audit_logs").insert(payload).execute()
        return True
    except Exception:
        return False

def authenticate_user(username, password):
    try:
        res = (
            supabase.table("users")
            .select("*")
            .eq("username", username.strip())
            .eq("password_hash", password.strip())
            .eq("is_active", True)
            .execute()
        )
        users = res.data or []
        if users:
            user = users[0]
            try:
                supabase.table("users").update({
                    "last_login": datetime.now(IST).isoformat()
                }).eq("user_id", user["user_id"]).execute()
            except Exception:
                pass
            return user
        return None
    except Exception as e:
        st.error(f"Supabase Auth Query Error: {e}")
        return None

def update_user_password(user_id, old_password, new_password):
    try:
        res = (
            supabase.table("users")
            .select("user_id")
            .eq("user_id", int(user_id))
            .eq("password_hash", old_password.strip())
            .execute()
        )
        if not res.data:
            return False, "Current password does not match."

        supabase.table("users").update({
            "password_hash": new_password.strip()
        }).eq("user_id", int(user_id)).execute()

        log_audit(user_id, "PASSWORD_CHANGED", "User successfully changed password.")
        return True, "Password updated successfully!"
    except Exception as e:
        return False, str(e)


# --- USER & VENDOR MANAGEMENT ---

def get_all_users():
    try:
        res = supabase.table("users").select("*").order("user_id").execute()
        return res.data or []
    except Exception:
        return []

def create_user(username, password, full_name, account_type, permissions, emp_code="", phone="", email="", primary_station="", can_manage_vendors=False):
    try:
        payload = {
            "username": username.strip(),
            "password_hash": password.strip(),
            "full_name": full_name.strip(),
            "account_type": account_type,
            "permissions": permissions,
            "emp_code": emp_code.strip(),
            "phone": phone.strip(),
            "email": email.strip(),
            "primary_station": primary_station.strip(),
            "can_manage_vendors": can_manage_vendors,
            "is_active": True,
            "created_at": datetime.now(IST).isoformat()
        }
        res = supabase.table("users").insert(payload).execute()
        return True, res.data
    except Exception as e:
        return False, str(e)

def update_user_status(user_id, is_active):
    try:
        supabase.table("users").update({"is_active": is_active}).eq("user_id", int(user_id)).execute()
        return True, "Status updated."
    except Exception as e:
        return False, str(e)

def update_user_permissions(user_id, account_type, permissions, can_manage_vendors, primary_station=""):
    try:
        payload = {
            "account_type": account_type,
            "permissions": permissions,
            "can_manage_vendors": can_manage_vendors,
            "primary_station": primary_station.strip()
        }
        supabase.table("users").update(payload).eq("user_id", int(user_id)).execute()
        return True, "User permissions updated successfully."
    except Exception as e:
        return False, str(e)

def delete_user(user_id):
    try:
        supabase.table("users").delete().eq("user_id", int(user_id)).execute()
        return True, "User deleted."
    except Exception as e:
        return False, str(e)

def get_all_vendors():
    try:
        res = supabase.table("vendors").select("*").order("vendor_id").execute()
        return res.data or []
    except Exception:
        return []

def create_vendor(vendor_name, contact_person="", phone="", category="", city="Kolkata"):
    try:
        payload = {
            "vendor_name": vendor_name.strip(),
            "contact_person": contact_person.strip(),
            "phone": phone.strip(),
            "category": category.strip(),
            "city": city.strip(),
            "is_active": True,
            "created_at": datetime.now(IST).isoformat()
        }
        supabase.table("vendors").insert(payload).execute()
        return True, "Vendor added."
    except Exception as e:
        return False, str(e)

def update_vendor_status(vendor_id, is_active):
    try:
        supabase.table("vendors").update({"is_active": is_active}).eq("vendor_id", int(vendor_id)).execute()
        return True, "Vendor status updated."
    except Exception as e:
        return False, str(e)

def delete_vendor(vendor_id):
    try:
        supabase.table("vendors").delete().eq("vendor_id", int(vendor_id)).execute()
        return True, "Vendor deleted."
    except Exception as e:
        return False, str(e)


# --- JOB SHEET & ITEM HELPERS ---

def get_next_job_no():
    try:
        res = supabase.table("jobs").select("job_no, job_id").order("job_id", desc=True).limit(20).execute()
        data = res.data or []
        max_num = 1000
        for row in data:
            digits = "".join(filter(str.isdigit, str(row.get("job_no", ""))))
            if digits:
                num = int(digits)
                if num > max_num:
                    max_num = num
        return str(max_num + 1)
    except Exception:
        return "1001"

def create_job_sheet(job_payload: dict, items_data: list):
    """Inserts header and line items atomically. Cleans header if line-item insertion crashes."""
    job_id = None
    try:
        res = supabase.table("jobs").insert(job_payload).execute()
        if not res.data:
            return False, "Failed to insert jobsheet header."
        
        job_id = res.data[0]["job_id"]
        prepared_rows = []
        for idx, item in enumerate(items_data, 1):
            prepared_rows.append({
                "job_id": job_id,
                "item_no": idx,
                "item_name": item["item_name"].strip(),
                "specifications": item.get("specifications", ""),
                "description_spec": item.get("specifications", ""),
                "quantity": float(item["quantity"]),
                "unit": item.get("unit", "Pcs"),
                "rate": float(item["rate"]),
                "amount": float(item["amount"]),
                "delivery_address": item.get("delivery_address", "").strip(),
                "is_delivered": False
            })

        if prepared_rows:
            supabase.table("job_items").insert(prepared_rows).execute()

        return True, res.data
    except Exception as e:
        if job_id:
            # Rollback dangling header
            try:
                supabase.table("jobs").delete().eq("job_id", job_id).execute()
            except Exception:
                pass
        return False, str(e)

def get_job_items(job_id):
    try:
        res = supabase.table("job_items").select("*").eq("job_id", int(job_id)).order("item_no").execute()
        return res.data or []
    except Exception:
        return []

def get_user_created_jobs(user_name, is_management=False):
    try:
        query = supabase.table("jobs").select("*").order("job_id", desc=True)
        if not is_management:
            query = query.eq("order_taken_by", user_name.strip())
        res = query.execute()
        return res.data or []
    except Exception:
        return []

def extend_job_deadline(job_id, user_id, new_due_date, reason=""):
    try:
        supabase.table("jobs").update({"due_date": str(new_due_date)}).eq("job_id", int(job_id)).execute()
        log_audit(user_id, "DEADLINE_EXTENDED", f"Job ID #{job_id} deadline moved to {new_due_date}. Reason: {reason}")
        return True, "Deadline updated."
    except Exception as e:
        return False, str(e)

def delete_job_sheet(job_id):
    try:
        supabase.table("job_items").delete().eq("job_id", int(job_id)).execute()
        res = supabase.table("jobs").delete().eq("job_id", int(job_id)).execute()
        if res.data:
            return True, "Job sheet deleted."
        return False, "Record could not be removed."
    except Exception as e:
        return False, str(e)

def update_job_sheet_by_management(job_id, header_payload, line_items):
    """Updates jobsheet header and restores items safely with automatic rollback."""
    jid = int(job_id)
    old_items = get_job_items(jid)
    try:
        supabase.table("jobs").update(header_payload).eq("job_id", jid).execute()

        new_rows = []
        for idx, it in enumerate(line_items, 1):
            new_rows.append({
                "job_id": jid,
                "item_no": idx,
                "item_name": it["item_name"].strip(),
                "specifications": it.get("specifications", ""),
                "description_spec": it.get("specifications", ""),
                "quantity": float(it.get("quantity", 0)),
                "unit": it.get("unit", "Pcs"),
                "rate": float(it.get("rate", 0)),
                "amount": float(it.get("amount", 0)),
                "delivery_address": it.get("delivery_address", "").strip(),
                "is_delivered": it.get("is_delivered", False)
            })

        supabase.table("job_items").delete().eq("job_id", jid).execute()
        if new_rows:
            supabase.table("job_items").insert(new_rows).execute()

        return True, "Jobsheet updated successfully."
    except Exception as e:
        # Restore previous items if replace fails
        if old_items:
            try:
                for o in old_items:
                    o.pop("item_id", None)
                supabase.table("job_items").insert(old_items).execute()
            except Exception:
                pass
        return False, str(e)

def request_job_deletion(job_id, requested_by, reason):
    try:
        supabase.table("jobs").update({
            "is_returned": True,
            "return_reason": f"[DELETION_REQ] By {requested_by}: {reason.strip()}"
        }).eq("job_id", int(job_id)).execute()
        return True, "Deletion request submitted to CEO & Admin."
    except Exception as e:
        return False, str(e)

def reject_job_deletion_request(job_id):
    try:
        supabase.table("jobs").update({
            "is_returned": False,
            "return_reason": None
        }).eq("job_id", int(job_id)).execute()
        return True, "Deletion request rejected. Job restored."
    except Exception as e:
        return False, str(e)

def get_all_designers():
    try:
        res = supabase.table("users").select("user_id, full_name, username, account_type, permissions").eq("is_active", True).execute()
        users = res.data or []
        designers = []
        for u in users:
            perms = u.get("permissions") or []
            role = u.get("account_type", "")
            username = (u.get("username") or "").lower()
            if role in ["SUPER_ADMIN", "CEO"] or username in ["admin"]:
                continue
            if "MOD_B" in perms:
                designers.append(u)
        return designers
    except Exception:
        return []

def claim_design_job(job_id, designer_name, user_id=None):
    try:
        supabase.table("jobs").update({"assigned_designer": designer_name}).eq("job_id", int(job_id)).execute()
        log_audit(user_id, "DESIGN_CLAIMED", f"Job #{job_id} claimed by {designer_name}")
        return True, "Job successfully claimed!"
    except Exception as e:
        return False, str(e)

def reject_job_to_sales(job_id, designer_name, reason, user_id=None):
    try:
        supabase.table("jobs").update({
            "current_stage": "SALES",
            "is_returned": True,
            "returned_by": f"Designer ({designer_name})",
            "return_reason": f"[SPEC_ISSUE] {reason.strip()}"
        }).eq("job_id", int(job_id)).execute()
        log_audit(user_id, "SPEC_ISSUE_FLAGGED", f"Job #{job_id} routed back to Sales: {reason.strip()}")
        return True, "Flagged and routed back to Sales Desk."
    except Exception as e:
        return False, str(e)

def record_payment_and_release(job_id, user_name, advance_received, balance_remaining, payment_mode, ref_no, payment_date, notes, is_credit=False, user_id=None):
    try:
        payment_status = "CREDIT_APPROVED" if is_credit else ("CLEARED" if balance_remaining <= 0 else "PARTIAL_ADVANCE")
        payload = {
            "current_stage": "PRODUCTION",
            "advance_received": float(advance_received),
            "balance_amount": float(balance_remaining),
            "payment_mode": payment_mode,
            "payment_ref": ref_no.strip() if ref_no else None,
            "payment_date": str(payment_date),
            "payment_remarks": notes.strip() if notes else None,
            "payment_status": payment_status,
            "accounts_cleared_by": user_name,
            "is_returned": False,
            "return_reason": None
        }
        supabase.table("jobs").update(payload).eq("job_id", int(job_id)).execute()
        audit_note = f"Released to PRODUCTION (Credit) by {user_name}" if is_credit else f"Advance ₹{advance_received:,.2f} recorded via {payment_mode}. Balance: ₹{balance_remaining:,.2f}"
        log_audit(user_id, "PAYMENT_CLEARED", f"Job #{job_id}: {audit_note}")
        return True, "Payment recorded. Job released to Production Floor!"
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=15, show_spinner=False)
def get_station_pending_counts():
    counts = {
        "SALES": 0,
        "DESIGN": 0,
        "PAYMENT": 0,
        "PRODUCTION": 0,
        "QC": 0,
        "DISPATCH": 0,
        "BILLING": 0,
        "BILLING_QUEUE": 0,
        "DELETION_REQS": 0,
    }
    try:
        res = (
            supabase.table("jobs")
            .select("current_stage, return_reason")
            .neq("current_stage", "SETTLED")
            .execute()
        )
        for j in (res.data or []):
            stg = j.get("current_stage")
            if (j.get("return_reason") or "").startswith("[DELETION_REQ]"):
                counts["DELETION_REQS"] += 1
            if stg in ["BILLING_REVIEW", "BILLING"]:
                counts["BILLING"] += 1
            elif stg in counts:
                counts[stg] += 1
    except Exception:
        pass
    return counts

def get_custom_presets(preset_type: str) -> list:
    try:
        res = supabase.table("custom_presets").select("preset_name").eq("preset_type", preset_type).execute()
        return [r["preset_name"] for r in (res.data or []) if r.get("preset_name")]
    except Exception:
        return []

def add_custom_preset(preset_type: str, preset_name: str) -> bool:
    p_clean = preset_name.strip()
    if not p_clean or p_clean.upper() == "NEW":
        return False
    try:
        supabase.table("custom_presets").upsert({
            "preset_type": preset_type,
            "preset_name": p_clean
        }, on_conflict="preset_name").execute()
        return True
    except Exception:
        return False