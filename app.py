import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import hashlib
import sqlite3  # Added SQLite import

# Page config
st.set_page_config(page_title="Attendance Tracker", layout="wide", page_icon="📊")

# Custom CSS styling
st.markdown(""" 
<style>
/* Overall page styling with deep blue background */
.stApp {
    background-color: #0A192F;
    color: #E2E8F0;
}

/* Remove default Streamlit white backgrounds and borders */
div.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

div.element-container {
    margin-bottom: 1rem;
}

.stTabs [data-baseweb="tab-panel"] {
    background-color: transparent !important;
}

/* Main header styling */
.main-header {
    font-size: 36px;
    font-weight: bold;
    color: #64FFDA;
    margin-bottom: 20px;
    text-align: center;
}

/* Sub headers */
.sub-header {
    font-size: 24px;
    font-weight: bold;
    color: #64FFDA;
    margin-top: 20px;
    margin-bottom: 15px;
    padding-bottom: 5px;
    border-bottom: 2px solid #172A45;
}

/* Info boxes */
.info-box {
    background-color: #172A45;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 4px solid #64FFDA;
}

/* Section styling */
.section {
    background-color: #172A45;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
}

/* Button styling - Updated to ensure mustard yellow background with BLACK text */
.stButton>button {
    background-color: #E3B448 !important;
    color: black !important;
    border-radius: 6px;
    padding: 5px 15px;
    border: none;
    font-weight: bold;
}

.stButton>button:hover {
    background-color: #CBA135 !important;
    color: black !important;
}

/* Ensure the button's text and all spans inside are black */
.stButton>button * {
    color: black !important;
}

.logout-btn>button {
    background-color: #F87171;
    color: #0F172A !important;
}

.logout-btn>button:hover {
    background-color: #EF4444;
}

/* Success and warning boxes */
.success-box {
    background-color: #0D3331;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 4px solid #10B981;
}

.warning-box {
    background-color: #3A2518;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 4px solid #F59E0B;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
    background-color: #172A45;
    border-radius: 8px;
    padding: 5px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    font-weight: 500;
    color: #E2E8F0;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: #64FFDA;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #64FFDA;
}

/* Input fields styling */
.stTextInput>div>div>input, .stSelectbox>div>div, .stDateInput>div>div {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
}

/* Text areas */
.stTextArea>div>div>textarea {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
}

/* Dataframe styling */
.dataframe-container div[data-testid="stDataFrame"] {
    background-color: #172A45;
}

/* Override for default gray from Streamlit */
div.stMarkdown {
    color: #E2E8F0;
}

p, .stMarkdown p {
    color: #E2E8F0 !important;
}

/* Hide footer */
footer {visibility: hidden;}

/* File uploader style */
.stFileUploader div {
    background-color: #172A45;
    padding: 10px;
    border-radius: 8px;
}

/* Radio buttons */
.stRadio div[role="radiogroup"] label {
    color: #E2E8F0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #0F172A;
    border-right: 1px solid #1E293B;
}

/* Message styling */
div[data-testid="stAlert"] {
    background-color: #172A45;
    border: 1px solid #334155;
}
</style>
""", unsafe_allow_html=True)

# Session state setup
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'attendance_uploaded' not in st.session_state:
    st.session_state.attendance_uploaded = False
if 'attendance_data' not in st.session_state:
    st.session_state.attendance_data = None

# Database setup
def init_db():
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users
    (username TEXT PRIMARY KEY, password_hash TEXT)
    ''')
    
    # Create attendance_data table to store Excel uploads
    c.execute('''
    CREATE TABLE IF NOT EXISTS student_data
    (username TEXT PRIMARY KEY, data TEXT)
    ''')
    
    # Create tables for attendance records
    c.execute('''
    CREATE TABLE IF NOT EXISTS class_attendance
    (username TEXT PRIMARY KEY, data TEXT)
    ''')
    
    # Create tables for practical attendance
    c.execute('''
    CREATE TABLE IF NOT EXISTS practical_attendance
    (username TEXT PRIMARY KEY, data TEXT)
    ''')
    
    # Create batch-specific attendance tables
    c.execute('''
    CREATE TABLE IF NOT EXISTS batch_attendance
    (username TEXT, batch TEXT, data TEXT, 
    PRIMARY KEY (username, batch))
    ''')
    
    # Create defaulters table
    c.execute('''
    CREATE TABLE IF NOT EXISTS defaulters
    (username TEXT, type TEXT, batch TEXT, data TEXT, 
    PRIMARY KEY (username, type, batch))
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helpers
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return False
    
    c.execute("INSERT INTO users VALUES (?, ?)", (username, hash_password(password)))
    conn.commit()
    conn.close()
    return True

def verify_user(username, password):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result and result[0] == hash_password(password):
        return True
    return False

def save_attendance_data(username, df):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    # Convert DataFrame to JSON string
    data_json = df.to_json()
    
    # Use INSERT OR REPLACE to update if exists or insert if not
    c.execute("INSERT OR REPLACE INTO student_data (username, data) VALUES (?, ?)", 
              (username, data_json))
    
    conn.commit()
    conn.close()

def load_attendance_data(username):
    try:
        conn = sqlite3.connect('attendance_tracker.db')
        c = conn.cursor()
        c.execute("SELECT data FROM student_data WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        
        if result:
            # Convert JSON string back to DataFrame
            return pd.read_json(result[0])
        return None
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def save_class_attendance(username, df):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    data_json = df.to_json()
    
    c.execute("INSERT OR REPLACE INTO class_attendance (username, data) VALUES (?, ?)", 
              (username, data_json))
    
    conn.commit()
    conn.close()

def load_class_attendance(username):
    try:
        conn = sqlite3.connect('attendance_tracker.db')
        c = conn.cursor()
        c.execute("SELECT data FROM class_attendance WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return pd.read_json(result[0])
        return None
    except Exception as e:
        st.error(f"Error loading class attendance: {e}")
        return None

def save_practical_attendance(username, df):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    data_json = df.to_json()
    
    c.execute("INSERT OR REPLACE INTO practical_attendance (username, data) VALUES (?, ?)", 
              (username, data_json))
    
    conn.commit()
    conn.close()

def load_practical_attendance(username):
    try:
        conn = sqlite3.connect('attendance_tracker.db')
        c = conn.cursor()
        c.execute("SELECT data FROM practical_attendance WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return pd.read_json(result[0])
        return None
    except Exception as e:
        st.error(f"Error loading practical attendance: {e}")
        return None

def save_batch_attendance(username, batch, df):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    data_json = df.to_json()
    
    c.execute("INSERT OR REPLACE INTO batch_attendance (username, batch, data) VALUES (?, ?, ?)", 
              (username, batch, data_json))
    
    conn.commit()
    conn.close()

def load_batch_attendance(username, batch):
    try:
        conn = sqlite3.connect('attendance_tracker.db')
        c = conn.cursor()
        c.execute("SELECT data FROM batch_attendance WHERE username=? AND batch=?", (username, batch))
        result = c.fetchone()
        conn.close()
        
        if result:
            return pd.read_json(result[0])
        return None
    except Exception as e:
        st.error(f"Error loading batch attendance: {e}")
        return None

def save_defaulters(username, type_name, batch, df):
    conn = sqlite3.connect('attendance_tracker.db')
    c = conn.cursor()
    data_json = df.to_json()
    
    c.execute("INSERT OR REPLACE INTO defaulters (username, type, batch, data) VALUES (?, ?, ?, ?)", 
              (username, type_name, batch, data_json))
    
    conn.commit()
    conn.close()

def get_batch(roll):
    try:
        roll = int(roll)
        if 1 <= roll <= 20:
            return "A"
        elif 21 <= roll <= 40:
            return "B"
        elif 41 <= roll <= 60:
            return "C"
        elif 61 <= roll <= 80:
            return "D"
    except:
        return "Unknown"

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.attendance_data = None
    st.session_state.attendance_uploaded = False
    st.rerun()

# Login/Register
def login():
    st.markdown("<h1 class='main-header'>📊 Attendance Tracker</h1>", unsafe_allow_html=True)
    
    st.markdown("<div class='info-box'>Welcome to the Attendance Tracker System. Please login to continue or register for a new account.</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Login", "✏ Register"])
    
    with tab1:
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        username = st.text_input("👤 Username", key="login_username")
        password = st.text_input("🔒 Password", type="password", key="login_password")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            login_button = st.button("Login", key="login_btn", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if login_button:
            if verify_user(username, password):
                st.success("Login successful!... Redirecting...")
                st.session_state.logged_in = True
                st.session_state.username = username
                attendance_data = load_attendance_data(username)
                if attendance_data is not None:
                    st.session_state.attendance_data = attendance_data
                    st.session_state.attendance_uploaded = True
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    with tab2:
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        new_username = st.text_input("👤 New Username", key="reg_username")
        new_password = st.text_input("🔒 New Password", type="password", key="reg_password")
        confirm_password = st.text_input("🔒 Confirm Password", type="password", key="confirm_password")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            register_button = st.button("Register", key="register_btn", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if register_button:
            if new_password != confirm_password:
                st.error("Passwords do not match")
            elif not new_username or not new_password:
                st.error("Username and password cannot be empty")
            else:
                if register_user(new_username, new_password):
                    st.success("Registration successful! You can now login.")
                else:
                    st.error("Username already exists")

# Upload Excel Page (Only First Time)
def upload_excel_page():
    st.markdown("<h1 class='main-header'>📊 Attendance Tracker</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 18px; margin-bottom: 30px; color: #64FFDA;'>Welcome, <b>{st.session_state.username}</b>!</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='section'>", unsafe_allow_html=True)
    st.markdown("<h2 class='sub-header'>Upload Class Excel</h2>", unsafe_allow_html=True)
    st.markdown("<p>Please upload your class excel file with student details. The file must contain <b>'roll'</b> and <b>'name'</b> columns.</p>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload Class Excel File", type=["xlsx", "xls"], key="excel_upload")
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            if 'roll' not in df.columns or 'name' not in df.columns:
                st.error("Excel must include 'roll' and 'name' columns.")
                return
            
            # Show preview of the data
            st.markdown("<p style='margin-top: 20px; font-weight: 500; color: #64FFDA;'>Data Preview:</p>", unsafe_allow_html=True)
            st.dataframe(df.head(5), hide_index=True, use_container_width=True)
            
            df['batch'] = df['roll'].apply(get_batch)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Confirm Upload", key="confirm_upload", use_container_width=True):
                    st.session_state.attendance_data = df
                    st.session_state.attendance_uploaded = True
                    save_attendance_data(st.session_state.username, df)
                    st.success("Excel uploaded successfully! Redirecting...")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")
    st.markdown("</div>", unsafe_allow_html=True)

# Main App
def main_app():
    # Sidebar
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; margin-bottom: 20px; color: #64FFDA;'>👋 Hello, <b>{}</b></h2>".format(st.session_state.username), unsafe_allow_html=True)
        
        st.markdown("<div style='text-align: center; margin-bottom: 30px;'>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<h3 style='font-size: 18px; margin-bottom: 15px; color: #64FFDA;'>Options</h3>", unsafe_allow_html=True)
        
        if st.button("📤 Upload New Excel", key="upload_new", use_container_width=True):
            st.session_state.attendance_uploaded = False
            st.rerun()
        
        st.markdown("<div class='logout-btn'>", unsafe_allow_html=True)
        if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
            logout()
        st.markdown("</div>", unsafe_allow_html=True)

    # Main content
    st.markdown("<h1 class='main-header'>📊 Attendance Tracker</h1>", unsafe_allow_html=True)
    
    df = st.session_state.attendance_data
    
    tabs = st.tabs(["📝 Take Attendance", "📊 View Reports", "⚠ Defaulter List"])
    
    with tabs[0]:
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h2 class='sub-header'>Take Attendance</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            date_str = st.date_input("📅 Select Date", datetime.now()).strftime("%Y-%m-%d")
        with col2:
            attendance_type = st.radio("📋 Attendance Type", ["Class", "Practical"])
        
        if attendance_type == "Practical":
            selected_batch = st.selectbox("👥 Select Batch", ["A", "B", "C", "D"])
        else:
            selected_batch = None
        
        absent_rolls = st.text_input("❌ Enter absent roll numbers (comma separated)")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_btn = st.button("Submit Attendance", key="submit_attendance", use_container_width=True)
        
        if submit_btn:
            roll_list = [r.strip() for r in absent_rolls.split(",") if r.strip()]
            absent_list = []
            for r in roll_list:
                try:
                    absent_list.append(int(r))
                except ValueError:
                    absent_list.append(str(r))
            
            column_name = f"{date_str}_{attendance_type}"
            updated_df = df.copy()
            
            if attendance_type == "Class":
                class_df = load_class_attendance(st.session_state.username)
                if class_df is None:
                    class_df = updated_df[['roll', 'name']].copy()
                
                class_df[column_name] = "Present"
                class_df.loc[class_df['roll'].isin(absent_list), column_name] = "Absent"
                save_class_attendance(st.session_state.username, class_df)
                st.success("Class attendance recorded successfully!")
            
            elif attendance_type == "Practical" and selected_batch:
                practical_df = load_practical_attendance(st.session_state.username)
                if practical_df is None:
                    practical_df = updated_df[['roll', 'name']].copy()
                
                practical_df[column_name] = ""
                practical_df.loc[updated_df['batch'] == selected_batch, column_name] = "Present"
                practical_df.loc[(updated_df['batch'] == selected_batch) & (practical_df['roll'].isin(absent_list)), column_name] = "Absent"
                save_practical_attendance(st.session_state.username, practical_df)
                
                for batch in ['A', 'B', 'C', 'D']:
                    batch_df = practical_df[practical_df['roll'].isin(updated_df[updated_df['batch'] == batch]['roll'])]
                    save_batch_attendance(st.session_state.username, batch, batch_df)
                
                st.success(f"Practical attendance for Batch {selected_batch} recorded successfully!")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h2 class='sub-header'>Absent Students in Last 5 Sessions</h2>", unsafe_allow_html=True)
        
        if attendance_type == "Class":
            class_df = load_class_attendance(st.session_state.username)
            if class_df is not None:
                attendance_cols = [col for col in class_df.columns if col not in ['roll', 'name']]
                last_cols = attendance_cols[-5:] if len(attendance_cols) >= 5 else attendance_cols
                
                if not last_cols:
                    st.info("No attendance records found yet.")
                else:
                    for col in last_cols:
                        st.markdown(f"<p style='font-weight: 500; margin-top: 10px; color: #64FFDA;'>🗓 {col}</p>", unsafe_allow_html=True)
                        absent_students = class_df[class_df[col] == "Absent"]["roll"].tolist()
                        if absent_students:
                            st.markdown(f"<p style='background-color: #3A2518; padding: 8px; border-radius: 5px; color: #F87171;'>Absent: {', '.join(map(str, absent_students))}</p>", unsafe_allow_html=True)
                        else:
                            st.markdown("<p style='background-color: #0D3331; padding: 8px; border-radius: 5px; color: #34D399;'>No students marked absent.</p>", unsafe_allow_html=True)
            else:
                st.info("Class attendance data not found.")
        
        elif attendance_type == "Practical" and selected_batch:
            batch_df = load_batch_attendance(st.session_state.username, selected_batch)
            if batch_df is not None:
                attendance_cols = [col for col in batch_df.columns if col not in ['roll', 'name']]
                last_cols = attendance_cols[-5:] if len(attendance_cols) >= 5 else attendance_cols
                
                if not last_cols:
                    st.info("No attendance records found yet.")
                else:
                    for col in last_cols:
                        st.markdown(f"<p style='font-weight: 500; margin-top: 10px; color: #64FFDA;'>🗓 {col}</p>", unsafe_allow_html=True)
                        absent_students = batch_df[batch_df[col] == "Absent"]["roll"].tolist()
                        if absent_students:
                            st.markdown(f"<p style='background-color: #3A2518; padding: 8px; border-radius: 5px; color: #F87171;'>Absent: {', '.join(map(str, absent_students))}</p>", unsafe_allow_html=True)
                        else:
                            st.markdown("<p style='background-color: #0D3331; padding: 8px; border-radius: 5px; color: #34D399;'>No students marked absent.</p>", unsafe_allow_html=True)
            else:
                st.info(f"Batch {selected_batch} attendance data not found.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tabs[1]:
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h2 class='sub-header'>Download Attendance Files</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<p style='font-weight: 500; color: #64FFDA;'>Class Attendance</p>", unsafe_allow_html=True)
            class_df = load_class_attendance(st.session_state.username)
            if class_df is not None:
                # Generate Excel file on-the-fly
                buffer = pd.ExcelWriter("class_attendance.xlsx", engine="xlsxwriter")
                class_df.to_excel(buffer, index=False)
                buffer.close()
                
                with open("class_attendance.xlsx", "rb") as f:
                    st.download_button(
                        label="📥 Download Class Attendance Excel",
                        data=f.read(),
                        file_name="class_attendance.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("No class attendance data available.")
        
        with col2:
            st.markdown("<p style='font-weight: 500; color: #64FFDA;'>Practical Attendance</p>", unsafe_allow_html=True)
            batch_options = ["A", "B", "C", "D"]
            selected_batch = st.selectbox("Select Batch", batch_options, key="dl_batch")
            
            batch_df = load_batch_attendance(st.session_state.username, selected_batch)
            if batch_df is not None:
                # Generate Excel file on-the-fly
                buffer = pd.ExcelWriter(f"batch_{selected_batch}_attendance.xlsx", engine="xlsxwriter")
                batch_df.to_excel(buffer, index=False)
                buffer.close()
                
                with open(f"batch_{selected_batch}_attendance.xlsx", "rb") as f:
                    st.download_button(
                        label=f"📥 Download Batch {selected_batch} Attendance",
                        data=f.read(),
                        file_name=f"batch_{selected_batch}_attendance.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info(f"No Batch {selected_batch} attendance data available.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tabs[2]:
        st.markdown("<div class='section'>", unsafe_allow_html=True)
        st.markdown("<h2 class='sub-header'>Defaulter List Generator</h2>", unsafe_allow_html=True)
        
        defaulter_type = st.selectbox("Select Attendance Type", ["Class", "Practical"], key="defaulter_type")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            calc_btn = st.button("Calculate Defaulters", key="calc_defaulters", use_container_width=True)
        
        if calc_btn:
            def calculate_defaulters(df, type_name, batch=None):
                if df is None:
                    st.warning(f"No {type_name} attendance data found.")
                    return
                
                if df.shape[1] <= 2:
                    st.warning(f"No attendance records found in {type_name}.")
                    return
                
                total_classes = df.shape[1] - 2  # excluding roll and name columns
                attendance_counts = df.iloc[:, 2:].applymap(lambda x: 1 if x == "Present" else 0)
                df["Attendance %"] = attendance_counts.sum(axis=1) / total_classes * 100
                
                defaulters_df = df[df["Attendance %"] < 80].copy()
                if defaulters_df.empty:
                    st.markdown("<div class='success-box'>", unsafe_allow_html=True)
                    st.markdown(f"✅ No defaulters in {type_name} attendance!", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='font-weight: 500; margin-top: 20px; color: #F87171;'>⚠ Defaulters in {type_name} Attendance (Below 80%)</p>", unsafe_allow_html=True)
                    
                    # Dataframe
                    st.dataframe(defaulters_df[["roll", "name", "Attendance %"]], use_container_width=True)
                    
                    # Save defaulters to database
                    save_defaulters(st.session_state.username, type_name, batch, defaulters_df)
                    
                    # Create Excel for download
                    buffer = pd.ExcelWriter(f"{type_name.lower()}_defaulters.xlsx", engine="xlsxwriter")
                    defaulters_df.to_excel(buffer, index=False)
                    buffer.close()
                    
                    with open(f"{type_name.lower()}_defaulters.xlsx", "rb") as f:
                        st.download_button(
                            label=f"📥 Download {type_name} Defaulters Excel",
                            data=f.read(),
                            file_name=f"{type_name.lower()}_defaulters.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
            
            if defaulter_type == "Class":
                class_df = load_class_attendance(st.session_state.username)
                calculate_defaulters(class_df, "Class")
            else:
                selected_batch = st.selectbox("Select Batch", ["A", "B", "C", "D"], key="defaulter_batch_select")
                batch_df = load_batch_attendance(st.session_state.username, selected_batch)
                
                if batch_df is not None:
                    calculate_defaulters(batch_df, "Practical", selected_batch)
                else:
                    st.warning("No practical attendance data found.")
        st.markdown("</div>", unsafe_allow_html=True)

# Run the app
if not st.session_state.logged_in:
    login()
elif not st.session_state.attendance_uploaded:
    upload_excel_page()
else:
    main_app()
