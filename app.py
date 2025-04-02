import os
import streamlit as st
import pandas as pd
from pyairtable import Api, Base, Table
from dotenv import load_dotenv
import requests

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
def get_airtable_data():
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
        
        # Create risk changes table if it doesn't exist yet
        try:
            # Try to get the risk changes table directly by ID
            if RISK_CHANGES_TABLE_ID:
                risk_changes_table = Table(AIRTABLE_API_KEY, BASE_ID, RISK_CHANGES_TABLE_ID)
                try:
                    # Just test connection, don't actually fetch data
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

# Auto-connect to Airtable on app start
if 'connected' not in st.session_state:
    risk_register_table, risk_changes_table, risk_types_table = get_airtable_data()
    if risk_register_table:
        st.session_state['risk_register_table'] = risk_register_table
        st.session_state['risk_changes_table'] = risk_changes_table
        st.session_state['risk_types_table'] = risk_types_table
        st.session_state['connected'] = True
        st.success("Successfully connected to Airtable!")
        
        # Cache the risk types for faster lookup
        risk_types_dict = {}
        if risk_types_table:
            try:
                risk_types_records = risk_types_table.all()
                for record in risk_types_records:
                    record_id = record['id']
                    type_name = record['fields'].get('Risk type', f"Unknown Type: {record_id}")
                    risk_types_dict[record_id] = type_name
                    
                if show_debug:
                    st.sidebar.write(f"Loaded {len(risk_types_dict)} risk types")
            except Exception as e:
                st.warning(f"Could not load risk types: {e}")
        
        st.session_state['risk_types_dict'] = risk_types_dict
    else:
        st.session_state['connected'] = False

# Button to reconnect if needed
if st.sidebar.button("Connect to Airtable"):
    risk_register_table, risk_changes_table, risk_types_table = get_airtable_data()
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
                    
                if show_debug:
                    st.sidebar.write(f"Loaded {len(risk_types_dict)} risk types")
            except Exception as e:
                st.warning(f"Could not load risk types: {e}")
        
        st.session_state['risk_types_dict'] = risk_types_dict
        st.success("Successfully connected to Airtable!")
    else:
        st.session_state['connected'] = False

# Main application logic
if st.session_state.get('connected', False):
    try:
        risk_register_table = st.session_state['risk_register_table']
        risk_changes_table = st.session_state['risk_changes_table']
        
        # Fetch all records from Risk Register
        records = risk_register_table.all()
        st.sidebar.write(f"Found {len(records)} records")
        
        # Convert to DataFrame for easier manipulation
        records_df = pd.DataFrame([{**record['fields'], 'record_id': record['id']} for record in records])
        
        # Store in session state
        st.session_state['records_df'] = records_df
        
        # Create lists for dropdowns
        if not records_df.empty:
            # Risk references - use whatever field has data
            risk_references = []
            
            # Try common fields for risk references
            for field in ['fldvQEaSVFnK3tmAo', 'Risk reference', 'Risk Reference']:
                if field in records_df.columns:
                    risk_refs = records_df[field].dropna().tolist()
                    if risk_refs:
                        risk_references = [str(ref) for ref in risk_refs if ref is not None]
                        break
            
            if not risk_references:
                # Fallback to record IDs if no references found
                risk_references = records_df['record_id'].tolist()
            
            # Create mock data for FH and ABBYY Personnel (replace this with actual data retrieval)
            fh_personnel = ["FH Person 1", "FH Person 2", "FH Person 3"]
            abbyy_personnel = ["ABBYY Person 1", "ABBYY Person 2", "ABBYY Person 3"]
            
            # Display form
            st.write("### Risk Selection")
            
            # Three dropdowns for selection
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_risk_reference = st.selectbox("Risk Reference", options=risk_references, key="risk_ref")
            
            with col2:
                selected_fh_personnel = st.selectbox("FH Personnel", options=fh_personnel, key="fh_personnel")
            
            with col3:
                selected_abbyy_personnel = st.selectbox("ABBYY Personnel", options=abbyy_personnel, key="abbyy_personnel")
            
            # Initialize form state in session if not present
            if 'form_stage' not in st.session_state:
                st.session_state['form_stage'] = 'initial'  # Possible values: initial, abbyy_submitted
            
            if 'abbyy_response' not in st.session_state:
                st.session_state['abbyy_response'] = None
            
            # Helper function to clean string values (remove brackets and quotes)
            def clean_display_value(value):
                if isinstance(value, str):
                    # Remove brackets, single quotes, and extra spaces
                    cleaned = value.replace('[', '').replace(']', '').replace("'", "")
                    return cleaned
                elif isinstance(value, list):
                    # Convert list items to strings and join them
                    return ", ".join(clean_display_value(item) for item in value if item is not None)
                else:
                    return str(value) if value is not None else ""
            
            # Helper function to ensure JSON-safe values (no NaN)
            def json_safe_value(value):
                import math
                
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
            
            # Filter record based on selection
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
            
            if filtered_record:
                record_id = filtered_record.get('record_id')
                
                # Display risk details (uneditable)
                st.write("### Risk Details")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Display Risk Type (from linked record)
                    risk_type_val = ""
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
                    
                    if show_debug:
                        st.sidebar.write("Risk Type IDs:")
                        st.sidebar.write(risk_type_ids)
                    
                    # Check if we have a dictionary for lookup
                    risk_types_dict = st.session_state.get('risk_types_dict', {})
                    
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
                    
                    # Save the IDs for later use
                    risk_type_val = risk_type_ids
                    
                    st.text_input("Risk Type", value=risk_type_display, disabled=True, key="risk_type")
                    
                    # Risk Category
                    risk_category = ""
                    if 'Risk category (from Risk types)' in filtered_record:
                        risk_category = clean_display_value(filtered_record['Risk category (from Risk types)'])
                    elif 'fldARoA6U91O9wKiZ' in filtered_record:
                        risk_category = clean_display_value(filtered_record['fldARoA6U91O9wKiZ'])
                    
                    st.text_input("Risk Category", value=risk_category, disabled=True)
                    
                    # Components
                    components = ""
                    if 'Component (Where will the risk occur)' in filtered_record:
                        components = clean_display_value(filtered_record['Component (Where will the risk occur)'])
                    elif 'fldlCW5th0RdZg1in' in filtered_record:
                        components = clean_display_value(filtered_record['fldlCW5th0RdZg1in'])
                    
                    st.text_area("Components", value=components, disabled=True)
                
                with col2:
                    # Risk Description
                    risk_description = ""
                    if 'Risk description' in filtered_record:
                        risk_description = clean_display_value(filtered_record['Risk description'])
                    elif 'fldqKOmtleXVuuhKE' in filtered_record:
                        risk_description = clean_display_value(filtered_record['fldqKOmtleXVuuhKE'])
                    
                    st.text_area("Risk Description", value=risk_description, disabled=True)
                    
                    # Root Causes
                    root_causes = ""
                    if 'Rootcause description (from rootcause)' in filtered_record:
                        root_causes = clean_display_value(filtered_record['Rootcause description (from rootcause)'])
                    elif 'fld00wYhLLvTGZkPM' in filtered_record:
                        root_causes = clean_display_value(filtered_record['fld00wYhLLvTGZkPM'])
                    
                    st.text_area("Root Causes", value=root_causes, disabled=True)
                    
                    # Impact
                    impact = ""
                    if 'Impact' in filtered_record:
                        impact = clean_display_value(filtered_record['Impact'])
                    elif 'fldc2ec6pUigCtOSb' in filtered_record:
                        impact = clean_display_value(filtered_record['fldc2ec6pUigCtOSb'])
                    
                    st.text_area("Impact", value=impact, disabled=True)
                
                # Risk Assessment section
                st.write("### Risk Assessment")
                
                col1, col2, col3, col4 = st.columns(4)
                
                severity_options = ["High", "Medium", "Low"]
                likelihood_options = ["High", "Medium", "Low"]
                detectability_options = ["High", "Medium", "Low"]
                
                # Get default values for risk levels
                default_severity = "Low"
                if 'Severity' in filtered_record:
                    default_severity = filtered_record['Severity']
                elif 'fld195IZccUi69V5D' in filtered_record:
                    default_severity = filtered_record['fld195IZccUi69V5D']
                
                default_likelihood = "Low"
                if 'Likelihood' in filtered_record:
                    default_likelihood = filtered_record['Likelihood']
                elif 'fldhdlk8KsdWNqgff' in filtered_record:
                    default_likelihood = filtered_record['fldhdlk8KsdWNqgff']
                
                default_detectability = "Low"
                if 'Detectability' in filtered_record:
                    default_detectability = filtered_record['Detectability']
                elif 'fldfVsQ4b7qc8TAPP' in filtered_record:
                    default_detectability = filtered_record['fldfVsQ4b7qc8TAPP']
                
                # Store original values in session state - only when first loading this risk
                risk_id_key = f"risk_id_{record_id}"
                if risk_id_key not in st.session_state or st.session_state[risk_id_key] != record_id:
                    # First time loading this specific risk, store original values
                    st.session_state[risk_id_key] = record_id
                    st.session_state['original_severity'] = default_severity if isinstance(default_severity, str) else "Low"
                    st.session_state['original_likelihood'] = default_likelihood if isinstance(default_likelihood, str) else "Low"  
                    st.session_state['original_detectability'] = default_detectability if isinstance(default_detectability, str) else "Low"
                    
                    # Get original overall risk level
                    original_risk_level = ""
                    if 'Overall Risk Level' in filtered_record:
                        original_risk_level = filtered_record['Overall Risk Level']
                    elif 'Overall Risk Score' in filtered_record:
                        original_risk_level = filtered_record['Overall Risk Score']
                    elif 'fldJtc0r2NsqF5UPV' in filtered_record:
                        original_risk_level = filtered_record['fldJtc0r2NsqF5UPV']
                    elif 'fldqLmmgCcAioHTi4' in filtered_record:
                        original_risk_level = filtered_record['fldqLmmgCcAioHTi4']
                    
                    st.session_state['original_risk_level'] = original_risk_level if isinstance(original_risk_level, str) else ""
                    
                    # Print the actual values we're storing (for debugging)
                    if show_debug:
                        st.sidebar.write(f"Loaded original values for risk {record_id}:")
                        st.sidebar.write(f"Severity: {st.session_state['original_severity']}")
                        st.sidebar.write(f"Likelihood: {st.session_state['original_likelihood']}")
                        st.sidebar.write(f"Detectability: {st.session_state['original_detectability']}")
                        st.sidebar.write(f"Risk Level: {st.session_state['original_risk_level']}")
                
                # Only allow editing in Form 2 (after ABBYY Response)
                is_editable = st.session_state.get('form_stage') == 'abbyy_submitted'
                
                # Define the update_risk_level function before it's used in the callbacks
                def update_risk_level():
                    # Get current values from session state
                    severity = st.session_state.get('severity', "Low")
                    likelihood = st.session_state.get('likelihood', "Low")
                    detectability = st.session_state.get('detectability', "Low")
                    
                    # Calculate new risk level
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
                    
                    # Store the new risk level in session state
                    st.session_state['new_risk_level'] = new_level
                    st.session_state['risk_score'] = overall_score
                
                with col1:
                    # Severity - Allow editing only after ABBYY Response
                    severity_index = severity_options.index(default_severity) if default_severity in severity_options else 0
                    severity_level = st.selectbox(
                        "Severity Level", 
                        options=severity_options, 
                        index=severity_index,
                        key="severity",
                        disabled=not is_editable,
                        on_change=update_risk_level if is_editable else None
                    )
                
                with col2:
                    # Likelihood - Allow editing only after ABBYY Response
                    likelihood_index = likelihood_options.index(default_likelihood) if default_likelihood in likelihood_options else 0
                    likelihood_level = st.selectbox(
                        "Likelihood Level", 
                        options=likelihood_options, 
                        index=likelihood_index,
                        key="likelihood",
                        disabled=not is_editable,
                        on_change=update_risk_level if is_editable else None
                    )
                
                with col3:
                    # Detectability - Allow editing only after ABBYY Response
                    detectability_index = detectability_options.index(default_detectability) if default_detectability in detectability_options else 0
                    detectability_level = st.selectbox(
                        "Detectability Level", 
                        options=detectability_options, 
                        index=detectability_index,
                        key="detectability",
                        disabled=not is_editable,
                        on_change=update_risk_level if is_editable else None
                    )
                
                with col4:
                    # Display the calculated risk level from session state
                    if is_editable:
                        # Get current values
                        severity = st.session_state.get('severity', severity_level)
                        likelihood = st.session_state.get('likelihood', likelihood_level)
                        detectability = st.session_state.get('detectability', detectability_level)
                        
                        # Calculate score for display (even if session state already has it)
                        severity_score = 3 if severity == "High" else (2 if severity == "Medium" else 1)
                        likelihood_score = 3 if likelihood == "High" else (2 if likelihood == "Medium" else 1)
                        detectability_score = 3 if detectability == "Low" else (2 if detectability == "Medium" else 1)
                        overall_score = severity_score * likelihood_score * detectability_score
                        
                        # Determine level from score (or get from session state)
                        new_risk_level = st.session_state.get('new_risk_level', 
                            "High" if overall_score >= 15 else ("Medium" if overall_score >= 6 else "Low"))
                        
                        # Make sure session state is updated with the latest value
                        st.session_state['new_risk_level'] = new_risk_level
                        st.session_state['risk_score'] = overall_score
                        
                        # Display the result
                        st.text_input("Overall Risk Level", 
                                     value=f"{new_risk_level} (Score: {overall_score})", 
                                     disabled=True)
                    else:
                        # Show original risk level when not in edit mode
                        st.text_input("Overall Risk Level", 
                                     value=str(st.session_state.get('original_risk_level', "")), 
                                     disabled=True)
                        
                        # Ensure the new risk level matches the original when not in edit mode
                        st.session_state['new_risk_level'] = st.session_state.get('original_risk_level', "")
                
                # Add session state for active tab
                if 'active_tab' not in st.session_state:
                    st.session_state['active_tab'] = 0
                
                # Set the active tab based on form stage
                if st.session_state['form_stage'] == 'abbyy_submitted' and st.session_state['active_tab'] == 0:
                    st.session_state['active_tab'] = 1
                
                # Create tabs for ABBYY and FH Response
                abbyy_tab, fh_tab = st.tabs(["ABBYY Response", "FH Response"])
                
                # Set ABBYY Response via callback 
                def set_abbyy_response():
                    st.session_state['abbyy_response'] = st.session_state['abbyy_resp']
                    st.session_state['form_stage'] = 'abbyy_submitted'
                    st.session_state['active_tab'] = 1  # Switch to FH Response tab
                
                # ABBYY Response Tab
                with abbyy_tab:
                    if st.session_state['form_stage'] == 'initial':
                        # ABBYY's Response
                        abbyy_response_options = ["Accept", "Change"]
                        default_abbyy_response = "Accept"
                        
                        if 'ABBYY Response' in filtered_record:
                            default_abbyy_response = filtered_record['ABBYY Response']
                        elif 'fldPQRI4yOhY8bXRn' in filtered_record:
                            default_abbyy_response = filtered_record['fldPQRI4yOhY8bXRn']
                        
                        if default_abbyy_response not in abbyy_response_options:
                            default_abbyy_response = abbyy_response_options[0]
                        
                        abbyy_index = abbyy_response_options.index(default_abbyy_response)
                        abbyy_response = st.selectbox(
                            "ABBYY's Response", 
                            options=abbyy_response_options, 
                            index=abbyy_index,
                            key="abbyy_resp",
                            on_change=lambda: set_abbyy_response()
                        )
                    else:
                        st.info("ABBYY response has been submitted. Please go to the FH Response tab.")
                
                # FH Response Tab
                with fh_tab:
                    if st.session_state['form_stage'] == 'initial':
                        st.info("Please submit ABBYY response first in the ABBYY Response tab.")
                    else:
                        # Display the changes made by ABBYY
                        st.write("### Changes Made By ABBYY")
                        st.write(f"ABBYY Response: **{st.session_state['abbyy_response']}**")
                        
                        # Show changes to risk levels if any
                        if st.session_state['abbyy_response'] == "Change":
                            changes = []
                            if severity_level != st.session_state['original_severity']:
                                changes.append(f"Severity: {st.session_state['original_severity']} → {severity_level}")
                            if likelihood_level != st.session_state['original_likelihood']:
                                changes.append(f"Likelihood: {st.session_state['original_likelihood']} → {likelihood_level}")
                            if detectability_level != st.session_state['original_detectability']:
                                changes.append(f"Detectability: {st.session_state['original_detectability']} → {detectability_level}")
                            
                            if changes:
                                st.write("Risk level changes:")
                                for change in changes:
                                    st.write(f"- {change}")
                            else:
                                st.write("No specific risk level changes were made.")
                        
                        st.write("### FH Response")
                        
                        # FH Response options
                        fh_response_options = ["Accept", "Unsure"]
                        
                        # Default to "Accept" if ABBYY selected "Accept"
                        default_fh_response = "Accept" if st.session_state['abbyy_response'] == "Accept" else "Unsure"
                        
                        # Allow FH to choose response
                        fh_index = fh_response_options.index(default_fh_response)
                        fh_response = st.selectbox(
                            "FH Response", 
                            options=fh_response_options, 
                            index=fh_index,
                            key="fh_resp"
                        )
                        
                        # Notes field
                        change_notes = st.text_area("Notes", key="change_notes", 
                                                   help="Add any additional notes about this risk assessment")
                        
                        # Submit button
                        if st.button("Save Changes"):
                            try:
                                # Check if risk_changes_table is available
                                if not risk_changes_table:
                                    st.error(f"Cannot access '{RISK_CHANGES_TABLE_NAME}' table. Please check permissions.")
                                    st.info("Make sure your API key has access to the table with ID: " + RISK_CHANGES_TABLE_ID)
                                    st.stop()
                                    
                                # Only save if there's a change or user explicitly wants to save
                                has_changes = (
                                    severity_level != st.session_state['original_severity'] or
                                    likelihood_level != st.session_state['original_likelihood'] or
                                    detectability_level != st.session_state['original_detectability'] or
                                    st.session_state['abbyy_response'] == "Change" or
                                    fh_response == "Unsure" or
                                    len(change_notes.strip()) > 0
                                )
                                
                                if has_changes:
                                    # Create data dictionary using field IDs directly
                                    data = {
                                        "fldJwiM65ftTV4wA3": str(selected_risk_reference) if selected_risk_reference else "",  # Original Risk Reference
                                        "fldMvXyJc8zCAHJJg": str(selected_fh_personnel) if selected_fh_personnel else "",  # FH Personnel
                                        "fld6RKhK7kWfsJost": str(selected_abbyy_personnel) if selected_abbyy_personnel else "",  # ABBYY Personnel
                                        "fldfTsmdEsXG2dcAo": "Todo",  # Status
                                        "flde0fUGwJlykaRnM": str(risk_category) if risk_category else "",  # Risk Category
                                        "fldYdVmw8pCKyRagq": str(risk_type_display) if risk_type_display else "",  # Risk Type
                                        "fldrpv5xlWDVnIE5d": str(risk_description) if risk_description else "",  # Risk Description
                                        "fldDmecXGLkpnK8lM": str(impact) if impact else "",  # Impact
                                        "fldcXaPheiACBgbEv": str(root_causes) if root_causes else "",  # Root Causes
                                        "fldqf7xmu3Z2EgTm0": str(components) if components else "",  # Components
                                        "fldTr9bdRevGV7zyi": str(st.session_state.get('original_severity', default_severity)),  # Original Severity Level
                                        "fldEYZSgQTr00GHf5": str(severity_level) if severity_level else "",  # New Severity Level
                                        "fldUZEGlpdaMMGTC9": str(st.session_state.get('original_likelihood', default_likelihood)),  # Original Likelihood Level
                                        "fld860nkAw1DUJaro": str(likelihood_level) if likelihood_level else "",  # New Likelihood Level
                                        "fldXO1FfoUa89lnsA": str(st.session_state.get('original_detectability', default_detectability)),  # Original Detectability Level
                                        "fld60ppjc9HEM8RPo": str(detectability_level) if detectability_level else "",  # New Detectability Level
                                        "fldXsSjjUWPjRftIm": str(st.session_state.get('original_risk_level', "")),  # Original Overall Risk Level
                                        "fldDJXURZKKyfz8pg": str(st.session_state.get('new_risk_level', "")),  # New Overall Risk Level
                                        "fldQ66bxR2keyBdHm": str(st.session_state.get('abbyy_response', "")),  # ABBYY's Response
                                        "fldj5ERls7Jsaq21H": str(fh_response) if fh_response else "",  # FH Response
                                        "fldmpEa117ZHBlJAN": str(change_notes) if change_notes else ""  # Change Notes
                                    }
                                    
                                    # Include risk score in change notes if calculated
                                    if 'risk_score' in st.session_state and st.session_state['risk_score']:
                                        risk_score = st.session_state['risk_score']
                                        score_note = f"Risk Score: {risk_score}"
                                        
                                        # Append to existing notes or create new
                                        if data["fldmpEa117ZHBlJAN"]:
                                            data["fldmpEa117ZHBlJAN"] = data["fldmpEa117ZHBlJAN"] + "\n\n" + score_note
                                        else:
                                            data["fldmpEa117ZHBlJAN"] = score_note
                                    
                                    # Ensure all values are JSON-safe (no NaN values)
                                    sanitized_data = {k: json_safe_value(v) for k, v in data.items()}
                                    
                                    # Debug information (only shown when debugging is enabled)
                                    if show_debug:
                                        st.write("Debug Information:")
                                        st.write("Fields being sent to Airtable using field IDs:")
                                        st.write(sanitized_data)
                                    
                                    try:
                                        # Create a record in the Risk Changes table using field IDs
                                        result = risk_changes_table.create(sanitized_data)
                                        st.success("Changes saved successfully!")
                                    except Exception as field_id_error:
                                        st.error(f"Error saving with field IDs: {field_id_error}")
                                        st.info("Trying alternative method with field names...")
                                        
                                        # Try with field names instead
                                        try:
                                            data_by_name = {
                                                "Original Risk Reference": str(selected_risk_reference) if selected_risk_reference else "",
                                                "FH Personnel": str(selected_fh_personnel) if selected_fh_personnel else "",
                                                "ABBYY Personnel": str(selected_abbyy_personnel) if selected_abbyy_personnel else "",
                                                "Status": "Todo",
                                                "Risk Category": str(risk_category) if risk_category else "",
                                                "Risk Type": str(risk_type_display) if risk_type_display else "",
                                                "Risk Description": str(risk_description) if risk_description else "",
                                                "Impact": str(impact) if impact else "",
                                                "Root Causes": str(root_causes) if root_causes else "",
                                                "Components": str(components) if components else "",
                                                "Original Severity Level": str(st.session_state.get('original_severity', default_severity)),
                                                "New Severity Level": str(severity_level) if severity_level else "",
                                                "Original Likelihood Level": str(st.session_state.get('original_likelihood', default_likelihood)),
                                                "New Likelihood Level": str(likelihood_level) if likelihood_level else "",
                                                "Original Detectability Level": str(st.session_state.get('original_detectability', default_detectability)),
                                                "New Detectability Level": str(detectability_level) if detectability_level else "",
                                                "Original Overall Risk Level": str(st.session_state.get('original_risk_level', "")),
                                                "New Overall Risk Level": str(st.session_state.get('new_risk_level', "")),
                                                "ABBYY's Response": str(st.session_state.get('abbyy_response', "")),
                                                "FH Response": str(fh_response) if fh_response else "",
                                                "Change Notes": str(change_notes) if change_notes else ""
                                            }
                                            
                                            # Ensure all values are JSON-safe (no NaN values)
                                            sanitized_name_data = {k: json_safe_value(v) for k, v in data_by_name.items()}
                                            
                                            # Only show debug information if explicitly enabled
                                            if show_debug:
                                                st.write("Trying with field names:")
                                                st.write(sanitized_name_data)
                                                
                                            result = risk_changes_table.create(sanitized_name_data)
                                            st.success("Changes saved successfully with field names!")
                                        except Exception as name_error:
                                            st.error(f"Error saving with field names: {name_error}")
                                            
                                            # Try one more method: direct API call
                                            try:
                                                # Attempt direct API call to create record
                                                api_response = requests.post(
                                                    f"https://api.airtable.com/v0/{BASE_ID}/{RISK_CHANGES_TABLE_ID}",
                                                    headers={
                                                        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
                                                        "Content-Type": "application/json"
                                                    },
                                                    json={
                                                        "records": [
                                                            {
                                                                "fields": sanitized_data
                                                            }
                                                        ]
                                                    }
                                                )
                                                
                                                # Only log API response details in debug mode
                                                if show_debug:
                                                    st.write(f"API Response: {api_response.status_code}")
                                                    st.write(api_response.json())
                                                    
                                                if api_response.status_code in [200, 201]:
                                                    st.success("Successfully saved using direct API call!")
                                            except Exception as api_error:
                                                st.error(f"Direct API call also failed: {api_error}")
                                else:
                                    st.info("No changes detected. Nothing was saved.")
                                    
                            except Exception as e:
                                st.error(f"Error saving changes: {e}")
                                st.info("Please check your Airtable configuration and ensure API permissions are correct.")
            else:
                st.info("Please select a valid Risk Reference to load the risk details.")
        else:
            st.warning("No records found in Risk Register table.")
    except Exception as e:
        st.error(f"Error retrieving data from Airtable: {e}")
        st.info("Please check your Airtable configuration and ensure the API key, Base ID, and Table ID are correct.")
else:
    st.info("Please connect to Airtable using the sidebar button to begin.")

# Instructions section in expandable area
with st.expander("Instructions"):
    st.write("""
    ## How to use this application:
    
    1. The application automatically connects to Airtable when started.
    
    2. Select a Risk Reference, FH Personnel, and ABBYY Personnel from the dropdowns.
    
    3. Review the risk details.
    
    4. Form 1: Choose ABBYY's Response (Accept or Change) and submit.
    
    5. Form 2: 
       - If ABBYY selected "Accept", the FH Response defaults to "Accept"
       - You can modify Severity, Likelihood, and Detectability values
       - Overall Risk Level will be recalculated based on changes
       - Choose FH Response (Accept or Unsure)
       - Add notes about the changes
    
    6. Click "Save Changes" to save to the Risk Changes History table.
    
    7. Changes are only saved to the Risk Changes History table if there are actual changes.
    """)
