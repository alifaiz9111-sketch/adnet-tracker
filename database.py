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
    # Simple direct verification against password_hash stored in DB
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

# --- DATA RETRIEVAL (WITH MASKING) ---
def get_jobs_for_stage(stage, is_financial_role=False):
    jobs = supabase.table("jobs").select("*").eq("current_stage", stage).order("job_id", desc=False).execute().data
    for j in jobs:
        if is_financial_role:
            items = supabase.table("job_items").select("*").eq("job_id", j["job_id"]).execute().data
        else:
            items = supabase.table("job_items").select("item_no, description_spec, material, qty, remarks").eq("job_id", j["job_id"]).execute().data
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
    job = supabase.table("jobs").select("due_date").eq("job_id", job_id).execute().data[0]
    old_date = job["due_date"]
    
    supabase.table("jobs").update({"next_due_date": new_date, "is_overdue": False}).eq("job_id", job_id).execute()
    supabase.table("audit_logs").insert({
        "job_id": job_id,
        "action_type": "DEADLINE_EXTENDED",
        "old_value": str(old_date),
        "new_value": str(new_date),
        "performed_by": user_id,
        "reason": reason
    }).execute()