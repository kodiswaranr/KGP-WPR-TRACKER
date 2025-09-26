import streamlit as st
import pandas as pd
import os
import re
import base64

# --------------------------
# Config / File paths
# --------------------------
excel_file = "WPR TRACKING FILE.xlsx"
left_logo = "left_logo.png"
right_logo = "right_logo.png"

# --------------------------
# Admin password
# --------------------------
DEFAULT_ADMIN_PASSWORD = "Admin@1234"
ADMIN_PASSWORD = os.environ.get("WPR_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

# --------------------------
# Helpers
# --------------------------
def normalize_col(name: str) -> str:
    if not isinstance(name, str):
        name = str(name)
    s = name.strip().upper()
    s = re.sub(r'[^0-9A-Z]+', '', s)
    return s

def load_logo_as_base64(path, width=100):
    if os.path.exists(path):
        with open(path, "rb") as f:
            logo_bytes = f.read()
        logo_b64 = base64.b64encode(logo_bytes).decode()
        return f"<img src='data:image/png;base64,{logo_b64}' width='{width}'>"
    return ""

# --------------------------
# Page setup
# --------------------------
st.set_page_config(page_title="KGP - WPR TRACKING PORTAL", layout="wide")

# --------------------------
# Header Bar with Logos
# --------------------------
left_logo_html = load_logo_as_base64(left_logo, 80)    # left logo
right_logo_html = load_logo_as_base64(right_logo, 10)  # right logo

st.markdown(
    f"""
    <div style='background-color:#f2f6fa; padding:15px; border-radius:8px; margin-bottom:15px;'>
        <div style='display:flex; justify-content:space-between; align-items:flex-end;'>
            <div style='flex:1; text-align:left;'>{left_logo_html}</div>
            <div style='flex:2; text-align:center;'>
                <h1 style='font-size:40px; font-weight:bold; color:black; margin:0;'>
                    KGP WPR PORTAL
                </h1>
            </div>
            <div style='flex:1; text-align:right;'>{right_logo_html}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------
# Load Excel
# --------------------------
if os.path.exists(excel_file):
    try:
        orig_df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
        orig_df = pd.DataFrame()
else:
    orig_df = pd.DataFrame()

# Build normalized mapping
norm_to_orig = {}
orig_cols = list(orig_df.columns)
seen = {}
normalized_cols = []
for col in orig_cols:
    norm = normalize_col(col)
    if norm in seen:
        seen[norm] += 1
        norm_unique = f"{norm}_{seen[norm]}"
    else:
        seen[norm] = 0
        norm_unique = norm
    norm_to_orig[norm_unique] = col
    normalized_cols.append(norm_unique)

# Create working dataframe with normalized column names
if not orig_df.empty:
    working_df = orig_df.copy()
    working_df.columns = normalized_cols
else:
    working_df = pd.DataFrame()

# --------------------------
# PERMIT ENTRY FORM
# --------------------------
st.subheader("📝 Permit Entry Form")

REQ_NAME = "NAME"
REQ_ANUM = "ANUMBER"

required_ok = not working_df.empty and (REQ_NAME in working_df.columns) and (REQ_ANUM in working_df.columns)

def get_orig_values(norm_key, fallback):
    orig_col = norm_to_orig.get(norm_key)
    if orig_col and orig_col in orig_df.columns:
        vals = orig_df[orig_col].dropna().astype(str).unique().tolist()
        if vals:
            return vals
    return fallback

if not required_ok:
    st.error("❌ Excel file not found or missing required columns (NAME, A NUMBER).")
else
