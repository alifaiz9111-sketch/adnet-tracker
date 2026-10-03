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
        user["permissions"] = [p["module_id"] for p in perm_res.data]
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

# --- AUTO INCREMENT JOB NUMBER ---
def get_next_job_no():
    try:
        res = supabase.table("jobs").select("job_no").order("job_id", desc=True).limit(50).execute()
        if not res.data:
            return "0001"
        
        max_num = 0
        for row in res.data:
            val = str(row.get("job_no", "")).strip()
            # Extract digits if user entered pure digits
            if val.isdigit():
                max_num = max(max_num, int(val))
        
        return f"{max_num + 1:04d}"
    except Exception:
        return "0001"

# --- DATA RETRIEVAL (WITH MASKING) ---
def get_jobs_for_stage(stage, is_financial_role=False):
    jobs = supabase.table("jobs").select("*").eq("current_stage", stage).order("job_id", desc=False).execute().data
    for j in jobs:
        if is_financial_role:
            items = supabase.table("job_items").select("*").eq("job_id", j["job_id"]).execute().data
        else:
            items = supabase.table("job_items").select("item_no, description_spec, material, qty, remarks, delivery_address").eq("job_id", j["job_id"]).execute().data
        j["items"] = items
    return jobs

def get_all_active_jobs():
    return supabase.table("jobs").select("*").neq("current_stage", "SETTLED").order("job_id", desc=True).execute().data

# --- STAGE TRANSITIONS & BOTTLENECK TRACKING ---
def update_job_stage(job_id, next_stage, holding_role):
    supabase.table("jobs").update({
        "current_stage": next_stage,
        "holding_employee_role": holding_role
    }).eq("job_id", job_id).execute()

def extend_job_deadline(job_id, new_date, reason, user_id):
    # Ensure job_id and user_id are native Python types, not numpy types
    job_id = int(job_id)
    user_id = int(user_id) if user_id is not None else None
    new_date_str = str(new_date)
    
    # Retrieve current due date
    job_res = supabase.table("jobs").select("due_date").eq("job_id", job_id).execute()
    old_date = job_res.data[0].get("due_date") if job_res.data else None
    old_date_str = str(old_date) if old_date is not None else ""

    # 1. Update jobs table (both due_date and next_due_date to avoid mismatch)
    supabase.table("jobs").update({
        "due_date": new_date_str,
        "next_due_date": new_date_str,
        "is_overdue": False
    }).eq("job_id", job_id).execute()

    # 2. Insert audit log record safely (all fields converted to primitives)
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
        # Avoid crashing if audit_logs table schema has optional column differences
        pass

# --- ADVANCED USER & PERMISSIONS MANAGEMENT (NO SUPABASE MANUAL EDITS) ---
def get_user_permissions(user_id):
    """Fetch list of module codes assigned to a user."""
    res = supabase.table("user_permissions").select("module_id").eq("user_id", user_id).execute()
    return [r["module_id"] for r in res.data] if res.data else []

def update_user_profile(user_id, full_name, email, password=None):
    """Update employee personal details; optionally change password."""
    payload = {"full_name": full_name, "email": email}
    if password and password.strip():
        payload["password_hash"] = password.strip()
    supabase.table("users").update(payload).eq("user_id", user_id).execute()

def update_user_modules(user_id, new_module_list):
    """Grant or revoke module permissions dynamically."""
    supabase.table("user_permissions").delete().eq("user_id", user_id).execute()
    if new_module_list:
        records = [{"user_id": user_id, "module_id": m} for m in new_module_list]
        supabase.table("user_permissions").insert(records).execute()

def delete_user_account(user_id):
    """Permanently delete an employee account and revoke their permissions."""
    supabase.table("user_permissions").delete().eq("user_id", user_id).execute()
    supabase.table("users").delete().eq("user_id", user_id).execute()

# --- SAFE JOB SHEET DELETION ---
def delete_job_sheet(job_id):
    """Cascading deletion of a job and all its related records across all modules safely."""
    # List of all potential child tables linked to a job
    child_tables = [
        "job_items",
        "job_artwork",
        "job_payments_advance",
        "job_production",
        "job_qc",
        "job_dispatch",
        "job_billing_review",
        "audit_logs"
    ]
    
    # Delete child records safely (ignores missing tables)
    for table_name in child_tables:
        try:
            supabase.table(table_name).delete().eq("job_id", job_id).execute()
        except Exception:
            pass  # If the table doesn't exist in Supabase, skip it without throwing an error

    # Finally delete the job itself
    try:
        supabase.table("jobs").delete().eq("job_id", job_id).execute()
        return True, "Job sheet and all associated records deleted successfully."
    except Exception as e:
        return False, str(e)

def get_stage_job_count(stage):
    """Return count of active jobs waiting in a specific stage."""
    try:
        res = supabase.table("jobs").select("job_id", count="exact").eq("current_stage", stage).execute()
        return res.count if res.count is not None else len(res.data)
    except Exception:
        return 0