from datetime import datetime
import pytz
import streamlit as st
from supabase import create_client, Client

IST = pytz.timezone("Asia/Kolkata")

@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase_client()

# --- AUTHENTICATION & USERS ---
def authenticate_user(username, password):
    try:
        res = supabase.table("users").select("*").eq("username", username).eq("password_hash", password).eq("is_active", True).execute()
        return res.data[0] if res.data else None
    except Exception:
        return None

def update_user_last_login(user_id):
    now_iso = datetime.now(IST).isoformat()
    try:
        supabase.table("users").update({"last_login": now_iso}).eq("user_id", int(user_id)).execute()
    except Exception:
        pass

def get_user_login_summary(user):
    user_id = user.get("user_id")
    account_type = user.get("account_type", "STAFF")
    user_perms = user.get("permissions", [])
    last_login = user.get("last_login")

    summary = {
        "new_jobs_count": 0,
        "new_jobs_total_val": 0.0,
        "pending_stage_name": None,
        "pending_stage_count": 0
    }

    try:
        if account_type in ["CEO", "SUPER_ADMIN"]:
            query = supabase.table("jobs").select("job_id")
            if last_login:
                query = query.gt("created_at", last_login)
            jobs_res = query.execute()
            new_job_ids = [j["job_id"] for j in (jobs_res.data or [])]
            summary["new_jobs_count"] = len(new_job_ids)

            if new_job_ids:
                items_res = supabase.table("job_items").select("amount").in_("job_id", new_job_ids).execute()
                summary["new_jobs_total_val"] = sum(float(it.get("amount", 0) or 0) for it in (items_res.data or []))
        else:
            stage_map = {
                "MOD_A": ("Order Intake", "DESIGN"),
                "MOD_B": ("Design & Proofs", "DESIGN"),
                "MOD_C": ("Advance & Accounts", "PAYMENT"),
                "MOD_D": ("Production Floor", "PRODUCTION"),
                "MOD_E": ("Quality Control", "QC"),
                "MOD_F": ("Dispatch & Delivery", "DISPATCH"),
                "MOD_G": ("Billing Review", "BILLING_REVIEW"),
                "MOD_BILL": ("GST Invoicing Queue", "BILLING_QUEUE")
            }
            for mod_code, (stage_label, stage_key) in stage_map.items():
                if mod_code in user_perms:
                    summary["pending_stage_name"] = stage_label
                    summary["pending_stage_count"] = get_stage_job_count(stage_key)
                    break
    except Exception:
        pass

    return summary

def get_all_users():
    try:
        res = supabase.table("users").select("*").order("user_id").execute()
        return res.data or []
    except Exception:
        return []

def create_user(username, password, full_name, account_type, permissions, emp_code="", phone="", email="", primary_station="", can_manage_vendors=False):
    try:
        data = {
            "username": username,
            "password_hash": password,
            "full_name": full_name,
            "account_type": account_type,
            "permissions": permissions,
            "emp_code": emp_code,
            "phone": phone,
            "email": email,
            "primary_station": primary_station,
            "can_manage_vendors": can_manage_vendors,
            "is_active": True
        }
        res = supabase.table("users").insert(data).execute()
        return True, res.data
    except Exception as e:
        return False, str(e)

def update_user_status(user_id, is_active):
    try:
        supabase.table("users").update({"is_active": is_active}).eq("user_id", int(user_id)).execute()
        return True
    except Exception:
        return False

# --- STAGE QUERIES & COUNTERS ---
def get_stage_job_count(stage_name):
    try:
        res = supabase.table("jobs").select("job_id", count="exact").eq("current_stage", stage_name).execute()
        return res.count or 0
    except Exception:
        return 0

def get_jobs_by_stage(stage_name):
    try:
        res = supabase.table("jobs").select("*").eq("current_stage", stage_name).order("job_id", desc=True).execute()
        return res.data or []
    except Exception:
        return []

def get_job_items(job_id):
    try:
        res = supabase.table("job_items").select("*").eq("job_id", int(job_id)).order("item_id").execute()
        return res.data or []
    except Exception:
        return []

def get_next_job_no():
    try:
        res = supabase.table("jobs").select("job_no").order("job_id", desc=True).limit(1).execute()
        if res.data and res.data[0].get("job_no"):
            last_no = res.data[0]["job_no"]
            if str(last_no).isdigit():
                return f"{int(last_no) + 1:04d}"
        return "0001"
    except Exception:
        return "0001"

# --- WORKFLOW UPDATES ---
def create_job_sheet(job_data, items_list):
    try:
        res = supabase.table("jobs").insert(job_data).execute()
        if not res.data:
            return False, "Failed to create jobsheet header"
        job_id = res.data[0]["job_id"]
        for it in items_list:
            it["job_id"] = int(job_id)
        supabase.table("job_items").insert(items_list).execute()
        return True, job_id
    except Exception as e:
        return False, str(e)

def update_job_stage(job_id, next_stage, user_name, audit_note=""):
    try:
        now_iso = datetime.now(IST).isoformat()
        supabase.table("jobs").update({
            "current_stage": next_stage,
            "updated_at": now_iso
        }).eq("job_id", int(job_id)).execute()

        supabase.table("audit_logs").insert({
            "job_id": int(job_id),
            "stage_moved_to": next_stage,
            "action_by": user_name,
            "notes": audit_note,
            "created_at": now_iso
        }).execute()
        return True
    except Exception:
        return False

def return_job_to_stage(job_id, target_stage, reason, returned_by):
    try:
        now_iso = datetime.now(IST).isoformat()
        supabase.table("jobs").update({
            "current_stage": target_stage,
            "is_returned": True,
            "return_reason": reason,
            "returned_by": returned_by,
            "updated_at": now_iso
        }).eq("job_id", int(job_id)).execute()

        supabase.table("audit_logs").insert({
            "job_id": int(job_id),
            "stage_moved_to": target_stage,
            "action_by": returned_by,
            "notes": f"RETURNED: {reason}",
            "created_at": now_iso
        }).execute()
        return True
    except Exception:
        return False

def extend_job_deadline(job_id, user_id, new_date, reason):
    try:
        now_iso = datetime.now(IST).isoformat()
        supabase.table("jobs").update({
            "due_date": str(new_date),
            "updated_at": now_iso
        }).eq("job_id", int(job_id)).execute()

        supabase.table("audit_logs").insert({
            "job_id": int(job_id),
            "stage_moved_to": "DEADLINE_EXTENDED",
            "action_by": str(user_id),
            "notes": f"Extended to {new_date}: {reason}",
            "created_at": now_iso
        }).execute()
        return True
    except Exception:
        return False

def delete_job_sheet(job_id):
    tables = [
        "job_items", "job_artwork", "job_payments_advance",
        "job_production", "job_production_materials", "job_qc",
        "job_quality_check", "job_dispatch", "job_billing_review",
        "audit_logs", "jobs"
    ]
    for tbl in tables:
        try:
            supabase.table(tbl).delete().eq("job_id", int(job_id)).execute()
        except Exception:
            pass
    return True

def delete_user(user_id):
    """Permanently deletes a user from the directory."""
    try:
        supabase.table("users").delete().eq("user_id", int(user_id)).execute()
        return True
    except Exception:
        return False


# --- VENDOR MANAGEMENT HELPERS ---
def get_all_vendors():
    try:
        res = supabase.table("vendors").select("*").order("vendor_id").execute()
        return res.data or []
    except Exception:
        return []

def create_vendor(vendor_name, contact_person="", phone="", category="", city="Kolkata"):
    try:
        data = {
            "vendor_name": vendor_name,
            "contact_person": contact_person,
            "phone": phone,
            "category": category,
            "city": city,
            "is_active": True
        }
        res = supabase.table("vendors").insert(data).execute()
        return True, res.data
    except Exception as e:
        return False, str(e)

def update_vendor_status(vendor_id, is_active):
    try:
        supabase.table("vendors").update({"is_active": is_active}).eq("vendor_id", int(vendor_id)).execute()
        return True
    except Exception:
        return False

def delete_vendor(vendor_id):
    try:
        supabase.table("vendors").delete().eq("vendor_id", int(vendor_id)).execute()
        return True
    except Exception:
        return False

def update_user_permissions(user_id, full_name, phone, email, primary_station, can_manage_vendors, permissions, account_type):
    """Updates existing staff profile, roles, and module access permissions."""
    try:
        data = {
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "primary_station": primary_station,
            "can_manage_vendors": can_manage_vendors,
            "permissions": permissions,
            "account_type": account_type
        }
        supabase.table("users").update(data).eq("user_id", int(user_id)).execute()
        return True, "Profile updated successfully."
    except Exception as e:
        return False, str(e)

def get_user_created_jobs(user_name, is_management=False):
    """Fetches jobs created by a specific user, or all jobs if management."""
    try:
        query = supabase.table("jobs").select("*").order("job_id", desc=True)
        if not is_management:
            # Case-insensitive match on creator name
            query = query.ilike("order_taken_by", f"%{user_name.strip()}%")
        res = query.execute()
        return res.data or []
    except Exception:
        return []

def authorize_gst_billing(job_id, authorized_by):
    """Pushes a GST job to CA Desk (BILLING_QUEUE)."""
    try:
        data = {
            "current_stage": "BILLING_QUEUE",
            "billing_type": "GST",
            "is_billed": False
        }
        supabase.table("jobs").update(data).eq("job_id", int(job_id)).execute()
        return True, "Job successfully authorized and pushed to CA Invoicing Queue."
    except Exception as e:
        return False, str(e)

def complete_nongst_billing(job_id, settled_by):
    """Marks a Non-GST job directly completed/settled without CA invoicing."""
    try:
        data = {
            "current_stage": "SETTLED",
            "billing_type": "NON_GST",
            "is_billed": True
        }
        supabase.table("jobs").update(data).eq("job_id", int(job_id)).execute()
        return True, "Job marked completed as Non-GST and settled successfully."
    except Exception as e:
        return False, str(e)