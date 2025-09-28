import streamlit as st
import pandas as pd
import os
import re
import base64
from datetime import datetime, timedelta

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

def style_dataframe(df):
    """Apply custom styling to the dataframe for better presentation."""
    return df.style.set_table_styles([
        {'selector': 'thead th', 'props': [
            ('background-color', '#4CAF50'),
            ('color', 'white'),
            ('font-weight', 'bold'),
            ('text-align', 'center'),
            ('font-size', '14px'),
            ('padding', '12px')
        ]},
        {'selector': 'tbody td', 'props': [
            ('text-align', 'center'),
            ('padding', '10px'),
            ('font-size', '12px'),
            ('border-bottom', '1px solid #ddd')
        ]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [
            ('background-color', '#f9f9f9')
        ]},
        {'selector': 'tbody tr:hover', 'props': [
            ('background-color', '#e8f5e8')
        ]},
        {'selector': 'table', 'props': [
            ('border-collapse', 'collapse'),
            ('margin', '25px 0'),
            ('font-size', '0.9em'),
            ('min-width', '400px'),
            ('border-radius', '5px 5px 0 0'),
            ('overflow', 'hidden'),
            ('box-shadow', '0 0 20px rgba(0, 0, 0, 0.15)')
        ]}
    ]).format(precision=2)

def get_date_column(df):
    """Find the date column in the dataframe."""
    date_columns = []
    for col in df.columns:
        if any(keyword in col.upper() for keyword in ['DATE', 'TIME']):
            if 'DATE' in col.upper() and 'TIME' not in col.upper():
                date_columns.append(col)
    return date_columns[0] if date_columns else None

def convert_to_datetime(df, date_col):
    """Convert date column to datetime with error handling."""
    try:
        # Try different date formats
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        return df, True
    except Exception as e:
        return df, False

# --------------------------
# Page setup
# --------------------------
st.set_page_config(page_title="KGP - WPR TRACKING PORTAL", layout="wide")

# --------------------------
# Header bar (logos + title)
# --------------------------
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
                    # Refresh the page data
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save to Excel: {e}")

# --------------------------
# Admin-protected Excel download and data view
# --------------------------
st.markdown("---")
st.markdown("### 🔐 Admin Panel: Data Management")

admin_pass = st.text_input("Enter admin password to access admin panel", type="password")
if admin_pass:
    if admin_pass == ADMIN_PASSWORD:
        st.success("✅ Correct password. Welcome to Admin Panel!")
        
        # Create tabs for different admin functions
        tab1, tab2, tab3 = st.tabs(["📊 View Data", "📥 Download Excel", "📈 Statistics"])
        
        with tab1:
            st.subheader("📊 WPR Tracking Data")
            
            if os.path.exists(excel_file):
                try:
                    # Load the latest data
                    admin_df = pd.read_excel(excel_file)
                    
                    if not admin_df.empty:
                        # Enhanced Filters Section
                        st.markdown("### 🔍 **Data Filters**")
                        
                        # Create filter columns
                        filter_col1, filter_col2 = st.columns([1, 1])
                        
                        with filter_col1:
                            st.markdown("#### 👤 **Employee & Permit Filters**")
                            
                            # Filter by employee name
                            if 'NAME' in admin_df.columns:
                                names = ['All'] + sorted(admin_df['NAME'].dropna().unique().tolist())
                                selected_name = st.selectbox("🔸 Filter by Employee", names)
                            else:
                                selected_name = 'All'
                            
                            # Filter by permit type
                            permit_col = None
                            for col in admin_df.columns:
                                if 'PERMIT' in col.upper() and 'TYPE' in col.upper():
                                    permit_col = col
                                    break
                            
                            if permit_col:
                                permits = ['All'] + sorted(admin_df[permit_col].dropna().unique().tolist())
                                selected_permit = st.selectbox("🔸 Filter by Permit Type", permits)
                            else:
                                selected_permit = 'All'
                        
                        with filter_col2:
                            st.markdown("#### 📅 **Date Filters**")
                            
                            # Find date column
                            date_col = get_date_column(admin_df)
                            
                            if date_col:
                                # Convert to datetime
                                admin_df, date_conversion_success = convert_to_datetime(admin_df, date_col)
                                
                                if date_conversion_success:
                                    # Quick date filter options
                                    date_filter_type = st.selectbox(
                                        "🔸 Date Filter Type",
                                        ["No Filter", "Quick Filters", "Custom Range"],
                                        help="Choose how you want to filter by date"
                                    )
                                    
                                    if date_filter_type == "Quick Filters":
                                        quick_filter = st.selectbox(
                                            "🔸 Quick Filter",
                                            [
                                                "All Time",
                                                "Today", 
                                                "Yesterday",
                                                "Last 3 Days",
                                                "Last 7 Days", 
                                                "Last 14 Days",
                                                "Last 30 Days",
                                                "This Week",
                                                "This Month",
                                                "Last Month"
                                            ]
                                        )
                                        
                                        # Calculate date ranges based on selection
                                        today = datetime.now().date()
                                        
                                        if quick_filter == "Today":
                                            start_date = end_date = today
                                        elif quick_filter == "Yesterday":
                                            start_date = end_date = today - timedelta(days=1)
                                        elif quick_filter == "Last 3 Days":
                                            start_date = today - timedelta(days=2)
                                            end_date = today
                                        elif quick_filter == "Last 7 Days":
                                            start_date = today - timedelta(days=6)
                                            end_date = today
                                        elif quick_filter == "Last 14 Days":
                                            start_date = today - timedelta(days=13)
                                            end_date = today
                                        elif quick_filter == "Last 30 Days":
                                            start_date = today - timedelta(days=29)
                                            end_date = today
                                        elif quick_filter == "This Week":
                                            start_date = today - timedelta(days=today.weekday())
                                            end_date = today
                                        elif quick_filter == "This Month":
                                            start_date = today.replace(day=1)
                                            end_date = today
                                        elif quick_filter == "Last Month":
                                            last_month = today.replace(day=1) - timedelta(days=1)
                                            start_date = last_month.replace(day=1)
                                            end_date = last_month
                                        else:  # All Time
                                            start_date = end_date = None
                                    
                                    elif date_filter_type == "Custom Range":
                                        st.markdown("**Select Custom Date Range:**")
                                        date_col1, date_col2 = st.columns(2)
                                        
                                        with date_col1:
                                            start_date = st.date_input(
                                                "📅 Start Date",
                                                value=admin_df[date_col].dt.date.min() if not admin_df[date_col].isna().all() else today,
                                                help="Select the start date for filtering"
                                            )
                                        
                                        with date_col2:
                                            end_date = st.date_input(
                                                "📅 End Date",
                                                value=admin_df[date_col].dt.date.max() if not admin_df[date_col].isna().all() else today,
                                                help="Select the end date for filtering"
                                            )
                                        
                                        # Validate date range
                                        if start_date > end_date:
                                            st.error("❌ Start date cannot be after end date!")
                                            start_date = end_date = None
                                    
                                    else:  # No Filter
                                        start_date = end_date = None
                                        
                                else:
                                    st.warning("⚠️ Could not parse date column. Date filtering unavailable.")
                                    start_date = end_date = None
                                    date_filter_type = "No Filter"
                            else:
                                st.info("ℹ️ No date column found in data.")
                                start_date = end_date = None
                                date_filter_type = "No Filter"
                        
                        # Apply filters
                        filtered_df = admin_df.copy()
                        filter_info = []
                        
                        # Apply employee filter
                        if selected_name != 'All':
                            filtered_df = filtered_df[filtered_df['NAME'] == selected_name]
                            filter_info.append(f"Employee: {selected_name}")
                        
                        # Apply permit filter
                        if selected_permit != 'All' and permit_col:
                            filtered_df = filtered_df[filtered_df[permit_col] == selected_permit]
                            filter_info.append(f"Permit: {selected_permit}")
                        
                        # Apply date filter
                        if date_filter_type != "No Filter" and date_col and start_date and end_date:
                            try:
                                filtered_df = filtered_df[
                                    (filtered_df[date_col].dt.date >= start_date) & 
                                    (filtered_df[date_col].dt.date <= end_date)
                                ]
                                filter_info.append(f"Date: {start_date} to {end_date}")
                            except Exception as e:
                                st.error(f"❌ Error applying date filter: {e}")
                        
                        # Show active filters
                        if filter_info:
                            st.markdown("---")
                            st.markdown("### 🔎 **Active Filters:**")
                            for info in filter_info:
                                st.markdown(f"- {info}")
                            
                            # Clear filters button
                            if st.button("🗑️ Clear All Filters"):
                                st.rerun()
                        
                        # Display summary metrics
                        st.markdown("---")
                        st.markdown("### 📊 **Data Summary**")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "📋 Total Records", 
                                len(filtered_df),
                                delta=f"{len(filtered_df) - len(admin_df)}" if len(filtered_df) != len(admin_df) else None
                            )
                        
                        with col2:
                            if 'NAME' in filtered_df.columns:
                                unique_employees = filtered_df['NAME'].nunique()
                                st.metric("👥 Unique Employees", unique_employees)
                        
                        with col3:
                            if permit_col:
                                unique_permits = filtered_df[permit_col].nunique()
                                st.metric("📄 Permit Types", unique_permits)
                        
                        with col4:
                            if date_col and not filtered_df.empty:
                                try:
                                    date_range = filtered_df[date_col].dt.date.nunique()
                                    st.metric("📅 Date Range (days)", date_range)
                                except:
                                    st.metric("📅 Date Range", "N/A")
                        
                        # Display the data table
                        st.markdown("---")
                        st.markdown("### 📋 **Data Table**")
                        
                        if not filtered_df.empty:
                            # Pagination controls
                            col1, col2, col3 = st.columns([1, 1, 2])
                            
                            with col1:
                                rows_per_page = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
                            
                            with col2:
                                if len(filtered_df) > rows_per_page:
                                    total_pages = (len(filtered_df) - 1) // rows_per_page + 1
                                    page = st.selectbox("Page", range(1, total_pages + 1))
                                    start_idx = (page - 1) * rows_per_page
                                    end_idx = start_idx + rows_per_page
                                    display_df = filtered_df.iloc[start_idx:end_idx]
                                    
                                    st.caption(f"Showing {start_idx + 1}-{min(end_idx, len(filtered_df))} of {len(filtered_df)} records")
                                else:
                                    display_df = filtered_df
                                    page = 1
                            
                            with col3:
                                # Export filtered data
                                if st.button("📤 Export Filtered Data"):
                                    try:
                                        # Create Excel file for filtered data
                                        filtered_filename = f"filtered_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                        filtered_df.to_excel(filtered_filename, index=False)
                                        
                                        with open(filtered_filename, "rb") as f:
                                            filtered_data = f.read()
                                        
                                        st.download_button(
                                            label="📥 Download Filtered Excel",
                                            data=filtered_data,
                                            file_name=filtered_filename,
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                        )
                                        
                                        # Clean up temporary file
                                        os.remove(filtered_filename)
                                        
                                    except Exception as e:
                                        st.error(f"Error creating filtered export: {e}")
                            
                            # Display the dataframe
                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                height=400
                            )
                            
                            # Alternative styled table view
                            if st.checkbox("🎨 Show Styled Table View"):
                                styled_df = style_dataframe(display_df)
                                st.write(styled_df.to_html(), unsafe_allow_html=True)
                        
                        else:
                            st.warning("⚠️ No records match the selected filters.")
                            st.info("💡 Try adjusting your filter criteria to see results.")
                        
                    else:
                        st.info("📝 No data found in the Excel file yet.")
                        
                except Exception as e:
                    st.error(f"Error loading Excel file: {e}")
            else:
                st.warning("📄 Excel file not found. Please submit some permit data first.")
        
        with tab2:
            st.subheader("📥 Download Excel File")
            
            if os.path.exists(excel_file):
                try:
                    with open(excel_file, "rb") as f:
                        data_bytes = f.read()
                    
                    # Show file info
                    file_size = len(data_bytes)
                    file_modified = datetime.fromtimestamp(os.path.getmtime(excel_file))
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"📁 File Size: {file_size:,} bytes")
                    with col2:
                        st.info(f"🕒 Last Modified: {file_modified.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    st.download_button(
                        label="📥 Download Full Excel File",
                        data=data_bytes,
                        file_name=f"WPR_TRACKING_FILE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Download the complete WPR tracking file with all permit records"
                    )
                    
                except Exception as e:
                    st.error(f"Could not prepare download: {e}")
            else:
                st.error("📄 Excel file not found for download.")
        
        with tab3:
            st.subheader("📈 Data Statistics")
            
            if os.path.exists(excel_file):
                try:
                    stats_df = pd.read_excel(excel_file)
                    
                    if not stats_df.empty:
                        # Basic statistics
                        st.write("### 📊 Overview Statistics")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Permit type distribution
                            permit_col = None
                            for col in stats_df.columns:
                                if 'PERMIT' in col.upper() and 'TYPE' in col.upper():
                                    permit_col = col
                                    break
                            
                            if permit_col:
                                st.write("**Permit Type Distribution:**")
                                permit_counts = stats_df[permit_col].value_counts()
                                st.bar_chart(permit_counts)
                        
                        with col2:
                            # Department distribution
                            dept_col = None
                            for col in stats_df.columns:
                                if 'DEPARTMENT' in col.upper() or 'DISCIPLINE' in col.upper():
                                    dept_col = col
                                    break
                            
                            if dept_col:
                                st.write("**Department Distribution:**")
                                dept_counts = stats_df[dept_col].value_counts()
                                st.bar_chart(dept_counts)
                        
                        # Recent activity
                        st.write("### 🕒 Recent Activity")
                        recent_records = stats_df.tail(5)
                        if 'NAME' in recent_records.columns:
                            st.write("**Last 5 Permit Entries:**")
                            display_cols = ['NAME']
                            for col in recent_records.columns:
                                if any(keyword in col.upper() for keyword in ['PERMIT', 'DATE', 'TIME']):
                                    display_cols.append(col)
                            
                            if len(display_cols) > 1:
                                st.dataframe(recent_records[display_cols[:5]], use_container_width=True)
                        
                    else:
                        st.info("📝 No data available for statistics.")
                        
                except Exception as e:
                    st.error(f"Error generating statistics: {e}")
            else:
                st.warning("📄 No Excel file found for statistics.")
                
    else:
        st.error("❌ Incorrect admin password.")

st.markdown("---")
st.caption("💡 Tip: Set WPR_ADMIN_PASSWORD environment variable to change admin password and avoid hardcoding.")

# Custom CSS for better styling
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: bold;
    }
    
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    
    .stDataFrame {
        border: 1px solid #e1e5e9;
        border-radius: 0.5rem;
    }
    
    .date-filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4CAF50;
    }
</style>
""", unsafe_allow_html=True)
