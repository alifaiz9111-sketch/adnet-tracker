import os
from datetime import datetime
import pytz
import streamlit as st
from supabase import create_client, Client

IST = pytz.timezone("Asia/Kolkata")

# Fetch credentials from Streamlit Secrets or Environment Variables
SUPABASE_URL = ""
SUPABASE_KEY = ""

if "supabase" in st.secrets:
    SUPABASE_URL = st.secrets["supabase"].get("url", "")
    SUPABASE_KEY = st.secrets["supabase"].get("key", "")
else:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase credentials missing! Please configure [supabase] url and key in Streamlit Secrets.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- AUDIT & AUTHENTICATION ---

def log_audit(user_id, action, details=""):
    """Logs system events and user actions to audit_logs."""
    try:
        payload = {
            "user_id": int(user_id) if user_id else None,
            "action": action,
            "details": details,
            "created_at": datetime.now(IST).isoformat()
        }
        supabase.table("audit_logs").insert(payload).execute()
        return True
    except Exception:
        return False


def authenticate_user(username, password):
    """Authenticates staff/admin user against password_hash and validates active status."""
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
            supabase.table("users").update({
                "last_login": datetime.now(IST).isoformat()
            }).eq("user_id", user["user_id"]).execute()
            return user
        return None
    except Exception:
        return None

def update_user_password(user_id, old_password, new_password):
    """Allows an active user to change their password after verifying their old password."""
    try:
        # Verify old password
        res = (
            supabase.table("users")
            .select("user_id")
            .eq("user_id", int(user_id))
            .eq("password_hash", old_password.strip())
            .execute()
        )
        if not res.data:
            return False, "Current password does not match."

        # Update to new password
        supabase.table("users").update({
            "password_hash": new_password.strip()
        }).eq("user_id", int(user_id)).execute()

        log_audit(user_id, "PASSWORD_CHANGED", "User successfully changed their password.")
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
        res = supabase.table("jobs").select("job_no").order("job_id", desc=True).limit(1).execute()
        data = res.data or []
        if data and data[0].get("job_no"):
            last_no = data[0]["job_no"]
            digits = "".join(filter(str.isdigit, str(last_no)))
            if digits:
                return str(int(digits) + 1)
        return "1001"
    except Exception:
        return "1001"


def create_job_sheet(job_payload, items_data):
    try:
        res = supabase.table("jobs").insert(job_payload).execute()
        if not res.data:
            return False, "Failed to insert job header."
        
        job_id = res.data[0]["job_id"]
        for idx, item in enumerate(items_data, 1):
            item_payload = {
                "job_id": job_id,
                "item_no": idx,
                "item_name": item["item_name"],
                "specifications": item.get("specifications", ""),
                "description_spec": item.get("specifications", ""),
                "quantity": item["quantity"],
                "unit": item["unit"],
                "rate": item["rate"],
                "amount": item["amount"],
                "delivery_address": item.get("delivery_address", ""),
                "is_delivered": False
            }
            supabase.table("job_items").insert(item_payload).execute()
        return True, res.data
    except Exception as e:
        return False, str(e)


def get_job_items(job_id):
    try:
        res = supabase.table("job_items").select("*").eq("job_id", int(job_id)).order("item_id").execute()
        return res.data or []
    except Exception:
        return []


def get_user_created_jobs(user_name, is_management=False):
    try:
        query = supabase.table("jobs").select("*").order("job_id", desc=True)
        if not is_management:
            query = query.ilike("order_taken_by", f"%{user_name.strip()}%")
        res = query.execute()
        return res.data or []
    except Exception:
        return []


def extend_job_deadline(job_id, user_id, new_due_date, reason=""):
    try:
        supabase.table("jobs").update({"due_date": str(new_due_date)}).eq("job_id", int(job_id)).execute()
        log_audit(user_id, "DEADLINE_EXTENDED", f"Job ID {job_id} deadline moved to {new_due_date}. Reason: {reason}")
        return True, "Deadline updated."
    except Exception as e:
        return False, str(e)


def delete_job_sheet(job_id):
    try:
        supabase.table("job_items").delete().eq("job_id", int(job_id)).execute()
        supabase.table("jobs").delete().eq("job_id", int(job_id)).execute()
        return True, "Job sheet deleted."
    except Exception as e:
        return False, str(e)

def update_user_password(user_id, old_password, new_password):
    """Allows an active user to change their password after verifying their old password."""
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

        log_audit(user_id, "PASSWORD_CHANGED", "User successfully changed their password.")
        return True, "Password updated successfully!"
    except Exception as e:
        return False, str(e)


def update_user_permissions(user_id, account_type, permissions, can_manage_vendors, primary_station=""):
    """Updates roles, permissions, vendor privileges, and station for an existing staff member."""
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

def update_job_sheet_by_management(job_id, header_payload, line_items):
    """Allows Manager, CEO, and Admin to edit jobsheet header and line items."""
    try:
        # 1. Update jobs header
        supabase.table("jobs").update(header_payload).eq("job_id", int(job_id)).execute()

        # 2. Replace line items (delete old, insert new)
        supabase.table("job_items").delete().eq("job_id", int(job_id)).execute()
        for it in line_items:
            it["job_id"] = int(job_id)
        if line_items:
            supabase.table("job_items").insert(line_items).execute()

        return True, "Jobsheet updated successfully."
    except Exception as e:
        return False, str(e)

def request_job_deletion(job_id, requested_by, reason):
    """Marks a jobsheet with a deletion request pending CEO/Admin review."""
    try:
        supabase.table("jobs").update({
            "is_returned": True,
            "return_reason": f"[DELETION_REQ] By {requested_by}: {reason.strip()}"
        }).eq("job_id", int(job_id)).execute()
        return True, "Deletion request submitted to CEO & Admin."
    except Exception as e:
        return False, str(e)


def reject_job_deletion_request(job_id):
    """Rejects the deletion request and restores normal job status."""
    try:
        supabase.table("jobs").update({
            "is_returned": False,
            "return_reason": None
        }).eq("job_id", int(job_id)).execute()
        return True, "Deletion request rejected. Job restored."
    except Exception as e:
        return False, str(e)