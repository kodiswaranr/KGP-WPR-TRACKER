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
    """Normalize a column name into a compact uppercase key."""
    if not isinstance(name, str):
        name = str(name)
    s = name.strip().upper()
    s = re.sub(r"[^0-9A-Z]+", "", s)
    return s

def load_logo_as_base64(path: str, width: int = 80) -> str:
    """Return HTML <img> tag with base64-embedded image or empty string."""
    if os.path.exists(path):
        with open(path, "rb") as f:
            logo_bytes = f.read()
        logo_b64 = base64.b64encode(logo_bytes).decode()
        return f"<img src='data:image/png;base64,{logo_b64}' width='{width}'/>"
    return ""

# --------------------------
# Page setup
# --------------------------
st.set_page_config(page_title="KGP - WPR TRACKING PORTAL", layout="wide")

# --------------------------
# Header bar (logos + title)
# --------------------------
# Use equal sizes for symmetry (both 60 px)
left_logo_html = load_logo_as_base64(left_logo, 80)
right_logo_html = load_logo_as_base64(right_logo, 70)

st.markdown(
    """
    <div style='background-color:#f2f6fa; padding:14px; border-radius:8px; margin-bottom:14px;'>
      <div style='display:flex; justify-content:space-between; align-items:flex-end;'>
        <div style='flex:1; text-align:left;'>{left}</div>
        <div style='flex:2; text-align:center;'>
          <h1 style='font-size:40px; font-weight:700; color:#111; margin:0;'>
            KGP WPR PORTAL
          </h1>
        </div>
        <div style='flex:1; text-align:right;'>{right}</div>
      </div>
    </div>
    """.format(left=left_logo_html, right=right_logo_html),
    unsafe_allow_html=True,
)

# --------------------------
# Load Excel data (if present)
# --------------------------
if os.path.exists(excel_file):
    try:
        orig_df = pd.read_excel(excel_file)
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
        orig_df = pd.DataFrame()
else:
    orig_df = pd.DataFrame()

# Build normalized mapping: normalized_key -> original column name
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
# Permit Entry Form
# --------------------------
st.subheader("📝 Permit Entry Form")

REQ_NAME = "NAME"
REQ_ANUM = "ANUMBER"

required_ok = not working_df.empty and (REQ_NAME in working_df.columns) and (REQ_ANUM in working_df.columns)

def get_orig_values(norm_key: str, fallback: list):
    """Return unique values from original dataframe column mapped by normalized key."""
    orig_col = norm_to_orig.get(norm_key)
    if orig_col and orig_col in orig_df.columns:
        vals = orig_df[orig_col].dropna().astype(str).unique().tolist()
        if vals:
            return vals
    return fallback

if not required_ok:
    st.error("❌ Excel file not found or missing required columns (NAME, A NUMBER). Please ensure the sheet contains those columns.")
else:
    # fixed boss name (read-only)
    kgp_incharge = "CAPO MR UGGERI GIANPIERO"
    st.text_input("KGP OVER-ALL UNDER", value=kgp_incharge, disabled=True)

    # Filter employees under this boss
    under_col_norm = normalize_col("KGP OVER-ALL UNDER")
    if under_col_norm in working_df.columns:
        employees_filtered = working_df.loc[
            working_df[under_col_norm] == kgp_incharge, REQ_NAME
        ].dropna().unique()
    else:
        employees_filtered = working_df[REQ_NAME].dropna().unique()

    employees_filtered = list(employees_filtered)
    if not employees_filtered:
        st.warning("No employees found for the selected boss. Please check the Excel file.")
    employee = st.selectbox("Select Employee Name", employees_filtered)

    if employee:
        emp_row = working_df[working_df[REQ_NAME] == employee].iloc[0]

        # Auto-display read-only fields
        a_number = emp_row.get(REQ_ANUM, "")
        job_title = emp_row.get(normalize_col("JOB TITLE"), "")
        iqama = emp_row.get(normalize_col("IQAMA"), "")

        st.text_input("A.Number", value=a_number, disabled=True)
        st.text_input("Job Title", value=job_title, disabled=True)
        st.text_input("IQAMA", value=iqama, disabled=True)

        # Dropdown options
        work_area_options = get_orig_values(normalize_col("WORK AREA AT SITE"), ["Area A", "Area B", "Area C"])
        dept_options = get_orig_values(normalize_col("DISCIPLINE DEPARTMENT"), ["Mechanical", "Electrical", "Civil", "Safety"])
        permit_options = get_orig_values(normalize_col("PERMIT TYPE"), ["Hot Work", "Cold Work", "Confined Space", "Electrical"])
        supervisor_options = get_orig_values(normalize_col("IN CHARGE SUPERVISOR SUPERINTENDENT"), ["Supervisor 1", "Supervisor 2"])
        shift_options = get_orig_values(normalize_col("ACTUAL SHIFT"), ["Day", "Night", "General"])

        with st.form("permit_form", clear_on_submit=True):
            work_area = st.selectbox("Work Area at Site", work_area_options)
            department = st.selectbox("Discipline Department", dept_options)
            permit_type = st.selectbox("Permit Type", permit_options)
            supervisor = st.selectbox("In Charge Supervisor / Superintendent", supervisor_options)
            shift = st.selectbox("Actual Shift", shift_options)
            permit_no = st.text_input("Permit No")
            date = st.date_input("Date")
            start_time = st.time_input("Start Time")
            end_time = st.time_input("End Time")

            submitted = st.form_submit_button("Submit")
            if submitted:
                def orig(col_norm: str, fallback: str):
                    return norm_to_orig.get(col_norm, fallback)

                new_row = {}
                new_row[orig(normalize_col("KGP OVER-ALL UNDER"), "KGP OVER-ALL UNDER")] = kgp_incharge
                new_row[orig(REQ_NAME, "NAME")] = employee
                new_row[orig(REQ_ANUM, "A.NUMBER")] = a_number
                new_row[orig(normalize_col("JOB TITLE"), "JOB TITLE")] = job_title
                new_row[orig(normalize_col("IQAMA"), "IQAMA")] = iqama
                new_row[orig(normalize_col("WORK AREA AT SITE"), "WORK AREA AT SITE")] = work_area
                new_row[orig(normalize_col("DISCIPLINE DEPARTMENT"), "DISCIPLINE DEPARTMENT")] = department
                new_row[orig(normalize_col("PERMIT TYPE"), "PERMIT TYPE")] = permit_type
                new_row[orig(normalize_col("IN CHARGE SUPERVISOR SUPERINTENDENT"), "IN CHARGE SUPERVISOR SUPERINTENDENT")] = supervisor
                new_row[orig(normalize_col("ACTUAL SHIFT"), "ACTUAL SHIFT")] = shift
                new_row[orig(normalize_col("PERMIT NO"), "PERMIT NO")] = permit_no
                new_row[orig(normalize_col("DATE"), "DATE")] = pd.to_datetime(date).date() if date else ""
                new_row[orig(normalize_col("START TIME"), "START TIME")] = start_time.strftime("%H:%M:%S") if start_time else ""
                new_row[orig(normalize_col("END TIME"), "END TIME")] = end_time.strftime("%H:%M:%S") if end_time else ""

                if os.path.exists(excel_file):
                    try:
                        current = pd.read_excel(excel_file)
                    except Exception as e:
                        st.error(f"Failed to read existing Excel file: {e}")
                        current = pd.DataFrame()
                else:
                    current = pd.DataFrame()

                new_df = pd.DataFrame([new_row])
                final_df = pd.concat([current, new_df], ignore_index=True, sort=False)

                try:
                    final_df.to_excel(excel_file, index=False)
                    st.success("✅ Permit details saved successfully!")
                except Exception as e:
                    st.error(f"Failed to save to Excel: {e}")

# --------------------------
# Admin-protected Excel download
# --------------------------
st.markdown("---")
st.markdown("### 🔐 Admin: Download Excel")
