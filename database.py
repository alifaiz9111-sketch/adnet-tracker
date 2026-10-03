import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

@st.cache_resource
def get_supabase_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase_client()

# --- AUTHENTICATION & USERS ---
def authenticate_user(username, password):
    res = supabase.table("users").select("*").eq("username", username).eq("is_active", True).execute()
    if not res.data:
        return None
    user = res.data[0]
    if user["password_hash"] == password:
        perm_res = supabase.table("user_permissions").select("module_id").eq("user_id", user["user_id"]).execute()
        user["permissions"] = [p["module_id"] for p in perm_res.data] if perm_res.data else []
        return user
    return None

def get_all_users():
    return supabase.table("users").select("user_id, username, full_name, account_type, email, is_active").execute().data

def create_user(username, password, full_name, account_type, email, modules):
    user_data = {
        "username": username,
        "password_hash": password,
        "full_name": full_name,
        "account_type": account_type,
        "email": email
    }
    user_res = supabase.table("users").insert(user_data).execute()
    new_user_id = user_res.data[0]["user_id"]
    
    if modules:
        perm_data = [{"user_id": new_user_id, "module_id": m} for m in modules]
        supabase.table("user_permissions").insert(perm_data).execute()
    return True

def update_user_status(user_id, is_active):
    supabase.table("users").update({"is_active": is_active}).eq("user_id", user_id).execute()

def get_user_permissions(user_id):
    res = supabase.table("user_permissions").select("module_id").eq("user_id", user_id).execute()
    return [r["module_id"] for r in res.data] if res.data else []

def update_user_profile(user_id, full_name, email, password=None):
    payload = {"full_name": full_name, "email": email}
    if password and password.strip():
        payload["password_hash"] = password.strip()
    supabase.table("users").update(payload).eq("user_id", user_id).execute()

def update_user_modules(user_id, new_module_list):
    supabase.table("user_permissions").delete().eq("user_id", user_id).execute()
    if new_module_list:
        records = [{"user_id": user_id, "module_id": m} for m in new_module_list]
        supabase.table("user_permissions").insert(records).execute()

def delete_user_account(user_id):
    supabase.table("user_permissions").delete().eq("user_id", user_id).execute()
    supabase.table("users").delete().eq("user_id", user_id).execute()

# --- JOB NUMBERS & COUNTERS ---
def get_next_job_no():
    try:
        res = supabase.table("jobs").select("job_no").order("job_id", desc=True).limit(50).execute()
        if not res.data:
            return "0001"
        max_num = 0
        for row in res.data:
            val = str(row.get("job_no", "")).strip()
            if val.isdigit():
                max_num = max(max_num, int(val))
        return f"{max_num + 1:04d}"
    except Exception:
        return "0001"

def get_stage_job_count(stage):
    try:
        res = supabase.table("jobs").select("job_id", count="exact").eq("current_stage", stage).execute()
        return res.count if res.count is not None else len(res.data)
    except Exception:
        return 0

# --- DATA RETRIEVAL (WITH MASKING) ---
def get_jobs_for_stage(stage, is_financial_role=False):
    jobs = supabase.table("jobs").select("*").eq("current_stage", stage).order("job_id", desc=False).execute().data
    for j in jobs:
        if is_financial_role:
            items = supabase.table("job_items").select("*").eq("job_id", j["job_id"]).execute().data
        else:
            items = supabase.table("job_items").select("item_id, item_no, description_spec, material, qty, remarks, delivery_address, is_delivered, delivered_qty").eq("job_id", j["job_id"]).execute().data
        j["items"] = items
    return jobs

def get_all_active_jobs():
    return supabase.table("jobs").select("*").neq("current_stage", "SETTLED").order("job_id", desc=True).execute().data

# --- STAGE TRANSITIONS & RETURNS ---
def update_job_stage(job_id, next_stage, holding_role):
    supabase.table("jobs").update({
        "current_stage": next_stage,
        "holding_employee_role": holding_role,
        "is_returned": False
    }).eq("job_id", job_id).execute()

def return_job_to_previous_stage(job_id, previous_stage, holding_role, reason, returned_by_name):
    """Returns a job sheet to a previous desk with a required note."""
    supabase.table("jobs").update({
        "current_stage": previous_stage,
        "holding_employee_role": holding_role,
        "is_returned": True,
        "return_reason": reason,
        "returned_by": returned_by_name
    }).eq("job_id", job_id).execute()

    try:
        supabase.table("audit_logs").insert({
            "job_id": int(job_id),
            "action_type": "STAGE_RETURNED",
            "old_value": holding_role,
            "new_value": previous_stage,
            "reason": str(reason or "")
        }).execute()
    except Exception:
        pass

def extend_job_deadline(job_id, new_date, reason, user_id):
    job_id = int(job_id)
    user_id = int(user_id) if user_id is not None else None
    new_date_str = str(new_date)

    job_res = supabase.table("jobs").select("due_date").eq("job_id", job_id).execute()
    old_date = job_res.data[0].get("due_date") if job_res.data else None
    old_date_str = str(old_date) if old_date is not None else ""

    supabase.table("jobs").update({
        "due_date": new_date_str,
        "next_due_date": new_date_str,
        "is_overdue": False
    }).eq("job_id", job_id).execute()

    try:
        supabase.table("audit_logs").insert({
            "job_id": job_id,
            "action_type": "DEADLINE_EXTENDED",
            "old_value": old_date_str,
            "new_value": new_date_str,
            "performed_by": user_id,
            "reason": str(reason or "")
        }).execute()
    except Exception:
        pass

# --- DISPATCH ITEM DELIVERY STATUS ---
def update_item_delivery_status(item_id, is_delivered, delivered_qty=None):
    payload = {
        "is_delivered": bool(is_delivered),
        "delivered_at": datetime.now(IST).isoformat() if is_delivered else None
    }
    if delivered_qty is not None:
        payload["delivered_qty"] = int(delivered_qty)
    supabase.table("job_items").update(payload).eq("item_id", item_id).execute()

# --- FREELANCER CA & INVOICING ---
def get_unbilled_jobs():
    return supabase.table("jobs").select("*").eq("is_billed", False).order("job_id", desc=False).execute().data

def get_billed_jobs():
    return supabase.table("jobs").select("*").eq("is_billed", True).order("invoice_uploaded_at", desc=True).execute().data

def get_today_uploaded_invoices_count():
    try:
        today_date = datetime.now(IST).strftime("%Y-%m-%d")
        res = supabase.table("jobs").select("job_id").eq("is_billed", True).gte("invoice_uploaded_at", f"{today_date}T00:00:00").execute()
        return len(res.data) if res.data else 0
    except Exception:
        return 0

def upload_invoice_file(job_id, file_bytes, file_name, uploader_name):
    try:
        job_res = supabase.table("jobs").select("invoice_upload_attempts, invoice_max_attempts").eq("job_id", job_id).execute()
        if not job_res.data:
            return False, "Job not found."
        
        job = job_res.data[0]
        attempts = job.get("invoice_upload_attempts", 0) or 0
        max_attempts = job.get("invoice_max_attempts", 3) or 3

        if attempts >= max_attempts:
            return False, f"Maximum re-upload attempts ({max_attempts}) reached. Contact Admin/CEO for permission."

        file_path = f"job_{job_id}/{int(datetime.now().timestamp())}_{file_name}"
        supabase.storage.from_("invoices").upload(file_path, file_bytes, {"content-type": "application/octet-stream", "x-upsert": "true"})
        public_url = supabase.storage.from_("invoices").get_public_url(file_path)

        now_iso = datetime.now(IST).isoformat()
        supabase.table("jobs").update({
            "invoice_file_url": public_url,
            "invoice_uploaded_at": now_iso,
            "invoice_uploaded_by": uploader_name,
            "invoice_upload_attempts": attempts + 1,
            "is_billed": True,
            "current_stage": "SETTLED"
        }).eq("job_id", job_id).execute()

        return True, "Invoice uploaded successfully and archived to Billed section!"
    except Exception as e:
        return False, str(e)

def reset_invoice_attempts(job_id):
    try:
        supabase.table("jobs").update({
            "invoice_upload_attempts": 0,
            "invoice_max_attempts": 6
        }).eq("job_id", job_id).execute()
        return True, "Upload attempts successfully reset."
    except Exception as e:
        return False, str(e)

# --- JOB SHEET DELETION ---
def delete_job_sheet(job_id):
    child_tables = [
        "job_items", "job_artwork", "job_payments_advance", 
        "job_production", "job_production_materials", 
        "job_qc", "job_quality_check", "job_dispatch", 
        "job_billing_review", "audit_logs"
    ]
    for table_name in child_tables:
        try:
            supabase.table(table_name).delete().eq("job_id", job_id).execute()
        except Exception:
            pass

    try:
        supabase.table("jobs").delete().eq("job_id", job_id).execute()
        return True, "Job sheet and all associated records deleted successfully."
    except Exception as e:
        return False, str(e)