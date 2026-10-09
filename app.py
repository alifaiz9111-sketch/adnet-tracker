import os
import streamlit as st
import time
from database import (
    authenticate_user, 
    supabase, 
    log_audit, 
    update_user_password,
    get_station_pending_counts
)
from modules import (
    mod_a_sales,
    mod_b_design,
    mod_c_payment,
    mod_d_production,
    mod_e_qc,
    mod_f_dispatch,
    mod_g_billing,
    manager_view,
    ceo_admin,
    vendor_dashboard,
    customer_dashboard
)

st.set_page_config(
    page_title="AdNet Operations ERP",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_customer" not in st.session_state:
    st.session_state.selected_customer = None
if "selected_vendor" not in st.session_state:
    st.session_state.selected_vendor = None


def inject_preadmin_dark_css():
    """Applies Preadmin deep-navy sidebar styling with brand red accents."""
    st.markdown("""
        <style>
        /* Overall Sidebar Background */
        section[data-testid="stSidebar"] {
            background-color: #0B0F19 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
            padding-top: 1rem !important;
        }

        /* Top Brand Logo & Title */
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 4px 10px 18px 10px;
        }
        .sidebar-brand-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, #E11D48 0%, #BE123C 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(225, 29, 72, 0.4);
        }
        .sidebar-brand-text {
            font-size: 20px;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -0.5px;
        }

        /* Category / Section Headers */
        .nav-category {
            font-size: 11px;
            font-weight: 700;
            color: #4B5563;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin: 18px 0 6px 12px;
        }

        /* Sidebar Navigation Radio Buttons */
        div[data-testid="stRadio"] {
            background: transparent !important;
        }
        div[data-testid="stRadio"] > div {
            gap: 3px !important;
        }

        /* Hide Native Radio Circle */
        div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        /* Default Inactive Nav Item */
        div[data-testid="stRadio"] label {
            background-color: transparent !important;
            padding: 10px 14px !important;
            border-radius: 8px !important;
            margin: 0 !important;
            cursor: pointer !important;
            transition: all 0.18s ease-in-out !important;
            border: none !important;
        }
        div[data-testid="stRadio"] label p {
            color: #9CA3AF !important;
            font-size: 13.5px !important;
            font-weight: 500 !important;
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            width: 100% !important;
        }

        /* Hover State */
        div[data-testid="stRadio"] label:hover {
            background-color: rgba(255, 255, 255, 0.05) !important;
        }
        div[data-testid="stRadio"] label:hover p {
            color: #FFFFFF !important;
        }

        /* BRAND RED ACTIVE SELECTED PILL */
        div[data-testid="stRadio"] label:has(input:checked),
        div[data-testid="stRadio"] label[data-checked="true"] {
            background-color: #E11D48 !important;
            box-shadow: 0 4px 14px rgba(225, 29, 72, 0.35) !important;
        }
        div[data-testid="stRadio"] label:has(input:checked) p,
        div[data-testid="stRadio"] label[data-checked="true"] p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }

        /* Action Buttons */
        .sidebar-action-btn button {
            background-color: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            color: #D1D5DB !important;
            font-size: 12px !important;
            border-radius: 8px !important;
            margin-top: 4px;
        }
        .sidebar-action-btn button:hover {
            background-color: rgba(225, 29, 72, 0.15) !important;
            border-color: #E11D48 !important;
            color: #FFFFFF !important;
        }
        </style>
    """, unsafe_allow_html=True)


def render_signin_window():
    """Centered floating card login screen matching JIDOX design reference."""
    st.markdown("""
        <style>
        /* Hide sidebar on login screen */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        /* Style the card container */
        div[data-testid="stForm"] {
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 12px !important;
            background-color: #161B22 !important;
            padding: 34px 26px !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6) !important;
        }
        /* Custom Diamond Icon */
        .login-brand-box {
            text-align: center;
            margin-bottom: 20px;
        }
        .login-diamond {
            width: 18px;
            height: 18px;
            background: #E11D48;
            transform: rotate(45deg);
            border-radius: 3px;
            display: inline-block;
            margin-right: 8px;
            vertical-align: middle;
        }
        .login-brand-title {
            font-size: 22px;
            font-weight