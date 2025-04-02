import os
import streamlit as st
import pandas as pd
from pyairtable import Api, Base, Table
from dotenv import load_dotenv
import requests
import math

# Load configuration from environment variables or streamlit secrets
# Streamlit secrets are defined in .streamlit/secrets.toml
AIRTABLE_API_KEY = st.secrets.get("airtable", {}).get("AIRTABLE_API_KEY", os.getenv("AIRTABLE_API_KEY", ""))
BASE_ID = st.secrets.get("airtable", {}).get("AIRTABLE_BASE_ID", "")
RISK_REGISTER_TABLE_ID = st.secrets.get("airtable", {}).get("AIRTABLE_TABLE_ID", "")
RISK_TYPES_TABLE_ID = st.secrets.get("airtable", {}).get("RISK_TYPES_TABLE_ID", "")
RISK_CHANGES_TABLE_ID = st.secrets.get("airtable", {}).get("RISK_CHANGES_TABLE_ID", "tblRw7CFjBSPvMNcs")  # Use hardcoded ID as fallback
RISK_CHANGES_TABLE_NAME = "Risk Changes History"  # Changed to "History" as requested

# Debug mode - disable by default for production
show_debug = False

# App title and description
st.title("Risk Management System")
st.write("This application interfaces with Airtable to manage risk register entries.")

# Function to connect to Airtable and get data
def connect_to_airtable():
    """Connect to Airtable and retrieve tables"""
    if not AIRTABLE_API_KEY or not BASE_ID or not RISK_REGISTER_TABLE_ID:
        st.error("Please ensure all Airtable credentials (API Key, Base ID, and Table ID) are set in the .streamlit/secrets.toml file.")
        return None, None, None
    
    try:
        api = Api(AIRTABLE_API_KEY)
        risk_register_table = Table(AIRTABLE_API_KEY, BASE_ID, RISK_REGISTER_TABLE_ID)
        
        # Try to access Risk Types table but don't fail if it's not accessible
        try:
            risk_types_table = Table(AIRTABLE_API_KEY, BASE_ID, RISK_TYPES_TABLE_ID) if RISK_TYPES_TABLE_ID else None
            # Test if we can access it by getting a record
            if risk_types_table:
                risk_types_table.first()
                st.sidebar.success("Connected to Risk Types table successfully")
        except Exception as e:
            st.warning(f"Could not access Risk Types table: {e}")
            st.info("Risk Type names will be shown as IDs. Check your API token permissions.")
            risk_types_table = None
        
        # Access risk changes table
        try:
            if RISK_CHANGES_TABLE_ID:
                risk_changes_table = Table(AIRTABLE_API_KEY, BASE_ID, RISK_CHANGES_TABLE_ID)
                try:
                    risk_changes_table.first()
                    st.sidebar.success(f"Connected to '{RISK_CHANGES_TABLE_NAME}' table successfully")
                except Exception as e:
                    st.warning(f"Error accessing '{RISK_CHANGES_TABLE_NAME}' table: {e}")
                    risk_changes_table = None
                
            return risk_register_table, risk_changes_table, risk_types_table
            
        except Exception as e:
            st.warning(f"Could not access risk changes table: {e}")
            risk_changes_table = None
            return risk_register_table, None, risk_types_table
        
    except Exception as e:
        st.error(f"Error connecting to Airtable: {e}")
        return None, None, None

def clean_display_value(value):
    """Helper function to clean string values (remove brackets and quotes)"""
    if isinstance(value, str):
        # Remove brackets, single quotes, and extra spaces
        cleaned = value.replace('[', '').replace(']', '').replace("'", "")
        return cleaned
    elif isinstance(value, list):
        # Convert list items to strings and join them
        return ", ".join(clean_display_value(item) for item in value if item is not None)
    else:
        return str(value) if value is not None else ""

def json_safe_value(value):
    """Helper function to ensure JSON-safe values (no NaN)"""
    if value is None:
        return ""
    
    # Check for NaN or infinity
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return ""
    
    # Handle lists recursively
    if isinstance(value, list):
        return [json_safe_value(item) for item in value]
    
    # Handle dictionaries recursively
    if isinstance(value, dict):
        return {k: json_safe_value(v) for k, v in value.items()}
    
    return value

def get_risk_details(records_df, selected_risk_reference):
    """Get risk details based on selected reference"""
    filtered_record = None
    if selected_risk_reference:
        # Try all columns to find the matching record
        for col in records_df.columns:
            # Convert both to string for comparison
            records_df['string_val'] = records_df[col].astype(str)
            filtered = records_df[records_df['string_val'] == str(selected_risk_reference)]
            if not filtered.empty:
                filtered_record = filtered.iloc[0].to_dict()
                break
    
    return filtered_record

def get_risk_type_display(filtered_record, risk_types_dict):
    """Extract and format risk type information"""
    risk_type_display = ""
    risk_type_ids = []
    
    # Get linked record IDs first
    if 'Risk types' in filtered_record:
        risk_types = filtered_record['Risk types']
        if isinstance(risk_types, list) and risk_types:
            if isinstance(risk_types[0], dict) and 'id' in risk_types[0]:
                # Extract IDs from linked records
                risk_type_ids = [item['id'] for item in risk_types]
            elif isinstance(risk_types[0], str):
                # If it's already a list of ID strings
                risk_type_ids = risk_types
    
    # Also try the field ID for risk types
    if not risk_type_ids and 'fldNqIWQ5VqVT7itc' in filtered_record:
        risk_types_raw = filtered_record['fldNqIWQ5VqVT7itc']
        if isinstance(risk_types_raw, list) and risk_types_raw:
            if isinstance(risk_types_raw[0], dict) and 'id' in risk_types_raw[0]:
                # Extract IDs from linked records
                risk_type_ids = [item['id'] for item in risk_types_raw]
            elif isinstance(risk_types_raw[0], str):
                # If it's already a list of ID strings
                risk_type_ids = risk_types_raw
        # Handle case where it might be a single string ID
        elif isinstance(risk_types_raw, str):
            risk_type_ids = [risk_types_raw]
    
    # Look up the names from our dictionary
    if risk_type_ids and risk_types_dict:
        risk_type_names = []
        for type_id in risk_type_ids:
            # Get the name from our cached dictionary
            if type_id in risk_types_dict:
                risk_type_names.append(risk_types_dict[type_id])
            else:
                # If we couldn't load the risk types table, just show the ID
                risk_type_names.append(f"Type ID: {type_id}")
        
        if risk_type_names:
            risk_type_display = ", ".join(risk_type_names)
    
    # If we still don't have names, use the risk categories as fallback
    if not risk_type_display and 'Risk category (from Risk types)' in filtered_record:
        risk_categories = filtered_record['Risk category (from Risk types)']
        if isinstance(risk_categories, list):
            risk_type_display = ", ".join(str(cat) for cat in risk_categories if cat is not None)
        else:
            risk_type_display = str(risk_categories) if risk_categories else ""
    
    # Try to get specific risk type name from lookup field if available
    if not risk_type_display and 'Risk type' in filtered_record:
        risk_type_display = filtered_record['Risk type']
    
    # Try alternative fields as a last resort
    if not risk_type_display and 'AI, algorithmic or autonomous system reference /name' in filtered_record:
        risk_type_display = filtered_record['AI, algorithmic or autonomous system reference /name']
    
    # Set a fallback if nothing found
    if not risk_type_display:
        if risk_type_ids:
            # If we have IDs but couldn't look them up, show them as is
            risk_type_display = f"Type IDs: {', '.join(risk_type_ids)}"
        else:
            risk_type_display = "Unknown Risk Type"
    
    return risk_type_display, risk_type_ids

def calculate_risk_level(severity, likelihood, detectability):
    """Calculate risk level based on severity, likelihood, and detectability"""
    # Convert severity to numeric values: High=3, Medium=2, Low=1
    severity_score = 3 if severity == "High" else (2 if severity == "Medium" else 1)
    
    # Convert likelihood to numeric values: High=3, Medium=2, Low=1
    likelihood_score = 3 if likelihood == "High" else (2 if likelihood == "Medium" else 1)
    
    # Convert detectability to numeric values: Low=3, Medium=2, High=1 (note the inverse scale)
    detectability_score = 3 if detectability == "Low" else (2 if detectability == "Medium" else 1)
    
    # Calculate overall score using the formula
    overall_score = severity_score * likelihood_score * detectability_score
    
    # Convert score to risk level
    if overall_score >= 15:  # High risk (15-27)
        new_level = "High"
    elif overall_score >= 6:  # Medium risk (6-14)
        new_level = "Medium"
    else:  # Low risk (1-5)
        new_level = "Low"
    
    return new_level, overall_score

def get_risk_changes_record(risk_changes_table, selected_risk_reference):
    """Get risk changes record for a specific risk reference"""
    try:
        if risk_changes_table:
            # Query by the Original Risk Reference field
            formula = f"{{Original Risk Reference}} = '{selected_risk_reference}'"
            risk_changes_records = risk_changes_table.all(formula=formula)
            
            # Return the most recent record if available
            if risk_changes_records:
                return risk_changes_records[-1]  # Most recent record
    except Exception as e:
        st.error(f"Error retrieving risk changes record: {e}")
    
    return None

def load_risk_data():
    """Load risk data from Airtable and set up session state"""
    # Auto-connect to Airtable on app start
    if 'connected' not in st.session_state:
        risk_register_table, risk_changes_table, risk_types_table = connect_to_airtable()
        if risk_register_table:
            st.session_state['risk_register_table'] = risk_register_table
            st.session_state['risk_changes_table'] = risk_changes_table
            st.session_state['risk_types_table'] = risk_types_table
            st.session_state['connected'] = True
            
            # Cache the risk types for faster lookup
            risk_types_dict = {}
            if risk_types_table:
                try:
                    risk_types_records = risk_types_table.all()
                    for record in risk_types_records:
                        record_id = record['id']
                        type_name = record['fields'].get('Risk type', f"Unknown Type: {record_id}")
                        risk_types_dict[record_id] = type_name
                except Exception as e:
                    st.warning(f"Could not load risk types: {e}")
            
            st.session_state['risk_types_dict'] = risk_types_dict
            
            # Fetch risk register data
            try:
                records = risk_register_table.all()
                st.sidebar.write(f"Found {len(records)} records")
                
                # Convert to DataFrame for easier manipulation
                records_df = pd.DataFrame([{**record['fields'], 'record_id': record['id']} for record in records])
                
                # Store in session state
                st.session_state['records_df'] = records_df
                
                st.success("Successfully connected to Airtable!")
            except Exception as e:
                st.error(f"Error retrieving data: {e}")
                st.session_state['connected'] = False
                st.session_state['records_df'] = None
        else:
            st.session_state['connected'] = False
            st.session_state['records_df'] = None
    # Make sure records_df is initialized
    if 'records_df' not in st.session_state:
        st.session_state['records_df'] = None

# Button to reconnect if needed
if st.sidebar.button("Connect to Airtable"):
    load_risk_data()

# Load data on initial run
load_risk_data()

# Instructions section in expandable area
with st.expander("Instructions"):
    st.write("""
    ## How to use this application:
    
    1. The application automatically connects to Airtable when started.
    
    2. Use the sidebar to navigate between pages:
       - ABBYY Response: For ABBYY personnel to review and respond
       - FH Response: For FH personnel to review ABBYY responses and provide their input
    
    3. On each page, select a Risk Reference, FH Personnel, and ABBYY Personnel from the dropdowns.
    
    **ABBYY Response Page:**
    
    4. Review the risk details.
    
    5. Choose ABBYY's Response (Accept or Change).
    
    6. If "Change" is selected, you can modify Severity, Likelihood, and Detectability values.
    
    7. Click "Save ABBYY Response" to save changes to the Risk Changes History table.
    
    **FH Response Page:**
    
    8. View the risk details and ABBYY's response/changes.
    
    9. Choose FH Response (Accept or Unsure).
    
    10. Add notes about the changes.
    
    11. Click "Save FH Response" to update the record in the Risk Changes History table.
    """)
