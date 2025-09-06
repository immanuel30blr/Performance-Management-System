import streamlit as st
import pandas as pd
from backend_perf import DatabaseManager

# Database connection details (must match backend_perf.py)
DB_NAME = 'PMS System'
DB_USER = 'postgres'
DB_PASSWORD = 'bijujohn'
DB_HOST = 'localhost'
DB_PORT = '5432'

# --- Session State Initialization ---
# This ensures the DatabaseManager is only initialized once
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager(
        DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
    )
    # Automatically create tables when the app first runs
    st.session_state.db_manager.create_tables()

db = st.session_state.db_manager

def refresh_data():
    """Reloads data from the database into session state."""
    st.session_state.employees = db.get_all_employees()
    st.session_state.clients = db.get_all_clients()
    st.session_state.skills = db.get_all_skills()
    st.session_state.certifications = db.get_all_certifications()

# Refresh data on initial load
if 'employees' not in st.session_state:
    refresh_data()

# --- Page Title and Layout ---
st.set_page_config(layout="wide", page_title="Agent Performance Dashboard")

st.title("🎯 Agent Performance & Client Matching")

# --- Sidebar for Adding Data ---
st.sidebar.header("Add New Data")

with st.sidebar.expander("➕ Add Employee"):
    with st.form("employee_form", clear_on_submit=True):
        name = st.text_input("Name")
        role = st.text_input("Role")
        experience = st.number_input("Experience (Years)", min_value=0, step=1)
        score = st.number_input("Performance Score (0-100)", min_value=0, max_value=100, step=1)
        submit_employee = st.form_submit_button("Add Employee")
        if submit_employee and name:
            db.add_employee(name, role, experience, score)
            st.success(f"Employee '{name}' added!")
            refresh_data()

with st.sidebar.expander("➕ Add Skill"):
    with st.form("skill_form", clear_on_submit=True):
        skill_name = st.text_input("Skill Name")
        submit_skill = st.form_submit_button("Add Skill")
        if submit_skill and skill_name:
            db.add_skill(skill_name)
            st.success(f"Skill '{skill_name}' added!")
            refresh_data()

with st.sidebar.expander("➕ Add Certification"):
    with st.form("cert_form", clear_on_submit=True):
        cert_name = st.text_input("Certification Name")
        submit_cert = st.form_submit_button("Add Certification")
        if submit_cert and cert_name:
            db.add_certification(cert_name)
            st.success(f"Certification '{cert_name}' added!")
            refresh_data()

with st.sidebar.expander("➕ Add Client"):
    with st.form("client_form", clear_on_submit=True):
        client_name = st.text_input("Client Name")
        submit_client = st.form_submit_button("Add Client")
        if submit_client and client_name:
            db.add_client(client_name)
            st.success(f"Client '{client_name}' added!")
            refresh_data()

st.sidebar.markdown("---")
st.sidebar.button("Refresh All Data", on_click=refresh_data)

# --- Main Content Area ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🔗 Link Data", "🔎 Find Best Agent"])

with tab1:
    st.header("Current Data Overview")
    if st.session_state.employees:
        st.subheader("Employees")
        st.dataframe(pd.DataFrame(st.session_state.employees))
    if st.session_state.skills:
        st.subheader("Skills")
        st.dataframe(pd.DataFrame(st.session_state.skills))
    if st.session_state.certifications:
        st.subheader("Certifications")
        st.dataframe(pd.DataFrame(st.session_state.certifications))
    if st.session_state.clients:
        st.subheader("Clients")
        st.dataframe(pd.DataFrame(st.session_state.clients))

with tab2:
    st.header("Link Employees to Skills & Certifications")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Link Skills")
        if st.session_state.employees and st.session_state.skills:
            selected_employee = st.selectbox(
                "Select Employee", st.session_state.employees, format_func=lambda x: x['name'], key="skill_employee_select"
            )
            selected_skills = st.multiselect(
                "Select Skills", st.session_state.skills, format_func=lambda x: x['skill_name']
            )
            if st.button("Assign Skills"):
                employee_id = selected_employee['id']
                for skill in selected_skills:
                    db.assign_skill_to_employee(employee_id, skill['id'])
                st.success(f"Skills assigned to {selected_employee['name']}!")
        else:
            st.warning("Please add employees and skills first.")
    
    with col2:
        st.subheader("Link Certifications")
        if st.session_state.employees and st.session_state.certifications:
            selected_employee_cert = st.selectbox(
                "Select Employee", st.session_state.employees, format_func=lambda x: x['name'], key="cert_employee_select"
            )
            selected_certs = st.multiselect(
                "Select Certifications", st.session_state.certifications, format_func=lambda x: x['certification_name']
            )
            if st.button("Assign Certs"):
                employee_id = selected_employee_cert['id']
                for cert in selected_certs:
                    db.assign_cert_to_employee(employee_id, cert['id'])
                st.success(f"Certifications assigned to {selected_employee_cert['name']}!")
        else:
            st.warning("Please add employees and certifications first.")

with tab3:
    st.header("Find the Best Agent")
    
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Set Client Requirements")
        if st.session_state.clients:
            selected_client = st.selectbox(
                "Select Client", st.session_state.clients, format_func=lambda x: x['client_name']
            )
            required_skills = st.multiselect(
                "Required Skills", st.session_state.skills, format_func=lambda x: x['skill_name']
            )
            required_certs = st.multiselect(
                "Required Certifications", st.session_state.certifications, format_func=lambda x: x['certification_name']
            )
            if st.button("Save Requirements"):
                client_id = selected_client['id']
                skill_ids = [s['id'] for s in required_skills]
                cert_ids = [c['id'] for c in required_certs]
                db.assign_requirements_to_client(client_id, skill_ids, cert_ids)
                st.success(f"Requirements saved for {selected_client['client_name']}!")
        else:
            st.warning("Please add clients first.")

    with col4:
        st.subheader("Best Agent Match")
        if 'find_agent_button' not in st.session_state:
            st.session_state.find_agent_button = False
            
        if st.session_state.clients and st.button("Find Best Agent for Selected Client"):
            st.session_state.find_agent_button = True
        
        if st.session_state.find_agent_button and 'selected_client' in locals():
            results = db.find_best_agent(selected_client['id'])
            if results:
                results_df = pd.DataFrame(results)
                results_df.rename(columns={
                    'employee_name': 'Agent Name',
                    'role': 'Role',
                    'experience_years': 'Experience (Years)',
                    'performance_score': 'Performance Score',
                    'matched_skills': 'Matching Skills',
                    'matched_certifications': 'Matching Certs',
                    'match_score': 'Match Score'
                }, inplace=True)
                st.dataframe(results_df.drop(columns=['id']))
            else:
                st.info("No agents found matching the client's requirements.")
