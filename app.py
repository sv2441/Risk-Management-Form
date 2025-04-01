import os
import streamlit as st
import pandas as pd
from pyairtable import Api, Base, Table
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Get Airtable API key and IDs from environment variables
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appNqoykW6Kqas0nh")  # Default value if not set
RISK_REGISTER_TABLE_ID = os.getenv("AIRTABLE_TABLE_ID", "tblMYODwpfZDIpjTL") 
RISK_TYPES_TABLE_ID = os.getenv("RISK_TYPES_TABLE_ID", "tblWpajjZP9siICLD")  # Make configurable via env var
RISK_CHANGES_TABLE_NAME = "Risk Changes History"  # Changed to "History" as requested

# Debug mode - disable by default
show_debug = False

# App title and description
st.title("Risk Management System")
st.write("This application interfaces with Airtable to manage risk register entries.")

# Function to connect to Airtable and get data
def get_airtable_data():
    if not AIRTABLE_API_KEY or not BASE_ID or not RISK_REGISTER_TABLE_ID:
        st.error("Please ensure all Airtable credentials (API Key, Base ID, and Table ID) are set in the .env file.")
        return None, None, None
    
    try:
        api = Api(AIRTABLE_API_KEY)
        risk_register_table = Table(AIRTABLE_API_KEY, BASE_ID, RISK_REGISTER_TABLE_ID)
        
        # Try to access Risk Types table but don't fail if it's not accessible
        try:
            risk_types_table = Table(AIRTABLE_API_KEY, BASE_ID, RISK_TYPES_TABLE_ID)
            # Test if we can access it by getting a record
            risk_types_table.first()
            st.sidebar.success("Connected to Risk Types table successfully")
        except Exception as e:
            st.warning(f"Could not access Risk Types table: {e}")
            st.info("Risk Type names will be shown as IDs. Check your API token permissions.")
            risk_types_table = None
        
        # Create risk changes table if it doesn't exist yet
        try:
            base = Base(AIRTABLE_API_KEY, BASE_ID)
            # Try to get the risk changes table
            try:
                risk_changes_table = base.table(RISK_CHANGES_TABLE_NAME)
                # Test if we can access it
                try:
                    risk_changes_table.first()
                    st.sidebar.success(f"Connected to '{RISK_CHANGES_TABLE_NAME}' table successfully")
                except Exception as e:
                    st.sidebar.error(f"Error accessing '{RISK_CHANGES_TABLE_NAME}' table: {e}")
                    risk_changes_table = None
            except Exception as table_e:
                st.warning(f"'{RISK_CHANGES_TABLE_NAME}' table not found: {table_e}")
                st.info(f"You need to create the '{RISK_CHANGES_TABLE_NAME}' table in your Airtable base.")
                risk_changes_table = None
        except Exception as e:
            st.warning(f"Could not access base: {e}")
            risk_changes_table = None
            
        return risk_register_table, risk_changes_table, risk_types_table
        
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
                
                # Store original values in session state
                if 'original_severity' not in st.session_state:
                    st.session_state['original_severity'] = default_severity
                if 'original_likelihood' not in st.session_state:
                    st.session_state['original_likelihood'] = default_likelihood  
                if 'original_detectability' not in st.session_state:
                    st.session_state['original_detectability'] = default_detectability
                
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
                
                if 'original_risk_level' not in st.session_state:
                    st.session_state['original_risk_level'] = original_risk_level
                
                # Only allow editing in Form 2 (after ABBYY Response)
                is_editable = st.session_state.get('form_stage') == 'abbyy_submitted'
                
                with col1:
                    # Severity - Allow editing only after ABBYY Response
                    severity_index = severity_options.index(default_severity) if default_severity in severity_options else 0
                    severity_level = st.selectbox(
                        "Severity Level", 
                        options=severity_options, 
                        index=severity_index,
                        key="severity",
                        disabled=not is_editable
                    )
                
                with col2:
                    # Likelihood - Allow editing only after ABBYY Response
                    likelihood_index = likelihood_options.index(default_likelihood) if default_likelihood in likelihood_options else 0
                    likelihood_level = st.selectbox(
                        "Likelihood Level", 
                        options=likelihood_options, 
                        index=likelihood_index,
                        key="likelihood",
                        disabled=not is_editable
                    )
                
                with col3:
                    # Detectability - Allow editing only after ABBYY Response
                    detectability_index = detectability_options.index(default_detectability) if default_detectability in detectability_options else 0
                    detectability_level = st.selectbox(
                        "Detectability Level", 
                        options=detectability_options, 
                        index=detectability_index,
                        key="detectability",
                        disabled=not is_editable
                    )
                
                with col4:
                    # Calculate new overall risk level if values have changed
                    # This is a placeholder calculation - replace with actual formula
                    def calculate_risk_level(severity, likelihood, detectability):
                        # Simple formula: if two or more are High, risk is High
                        # If two or more are Low, risk is Low
                        # Otherwise, risk is Medium
                        high_count = sum(1 for level in [severity, likelihood, detectability] if level == "High")
                        low_count = sum(1 for level in [severity, likelihood, detectability] if level == "Low")
                        
                        if high_count >= 2:
                            return "High"
                        elif low_count >= 2:
                            return "Low"
                        else:
                            return "Medium"
                    
                    new_risk_level = calculate_risk_level(severity_level, likelihood_level, detectability_level)
                    
                    # Display the calculated risk level
                    if is_editable and (severity_level != st.session_state['original_severity'] or 
                                        likelihood_level != st.session_state['original_likelihood'] or 
                                        detectability_level != st.session_state['original_detectability']):
                        st.text_input("Overall Risk Level", value=new_risk_level, disabled=True)
                        st.session_state['new_risk_level'] = new_risk_level
                    else:
                        st.text_input("Overall Risk Level", value=str(original_risk_level), disabled=True)
                        st.session_state['new_risk_level'] = original_risk_level
                
                # Form 1: ABBYY Response (initial stage)
                if st.session_state['form_stage'] == 'initial':
                    st.write("### Form 1: ABBYY Response")
                    
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
                    
                    # Set ABBYY Response via callback 
                    def set_abbyy_response():
                        st.session_state['abbyy_response'] = st.session_state['abbyy_resp']
                        st.session_state['form_stage'] = 'abbyy_submitted'
                    
                    # FH Response options are shown immediately but disabled until ABBYY response is set
                    st.write("### FH Response")
                    fh_response_options = ["Accept", "Unsure"]
                    default_fh_response = "Accept" if abbyy_response == "Accept" else "Unsure"
                    fh_index = fh_response_options.index(default_fh_response)
                    
                    fh_response = st.selectbox(
                        "FH Response", 
                        options=fh_response_options, 
                        index=fh_index,
                        key="fh_resp",
                        disabled=True
                    )
                    
                    # Notes field
                    change_notes = st.text_area("Notes", key="change_notes", 
                                               help="Add any additional notes about this risk assessment",
                                               disabled=True)
                    
                    # Save button (disabled)
                    st.button("Save Changes", disabled=True)
                
                # Form 2: FH Response (after ABBYY Response)
                elif st.session_state['form_stage'] == 'abbyy_submitted':
                    st.write("### Form 2: FH Response")
                    
                    # Display the saved ABBYY Response
                    st.write(f"ABBYY Response: **{st.session_state['abbyy_response']}**")
                    
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
                                
                                # Try to provide more specific information about the issue
                                try:
                                    base = Base(AIRTABLE_API_KEY, BASE_ID)
                                    try:
                                        tables = base.tables
                                        table_names = [table.name for table in tables]
                                        st.info(f"Available tables in this base: {', '.join(table_names)}")
                                    except:
                                        st.warning("Could not retrieve table names")
                                    
                                    # Try to create the table as a fallback
                                    if st.button("Create Risk Changes History Table"):
                                        try:
                                            # This might not work with all API tokens
                                            schema = {
                                                "name": RISK_CHANGES_TABLE_NAME,
                                                "description": "Table to store history of risk changes"
                                            }
                                            result = requests.post(
                                                f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables",
                                                headers={
                                                    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
                                                    "Content-Type": "application/json"
                                                },
                                                json=schema
                                            )
                                            if result.status_code == 200:
                                                st.success("Table created successfully! Please refresh the app.")
                                            else:
                                                st.error(f"Failed to create table: {result.text}")
                                        except Exception as create_e:
                                            st.error(f"Error creating table: {create_e}")
                                except Exception as table_e:
                                    st.error(f"Error checking available tables: {table_e}")
                                
                                # Skip the rest of this function
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
                                # Create data with all the fields that should be included in the Risk Changes History
                                data = {
                                    "Original Risk Reference": selected_risk_reference,
                                    "FH Personnel": selected_fh_personnel,
                                    "ABBYY Personnel": selected_abbyy_personnel,
                                    "Risk Category": risk_category,
                                    "Risk Type": risk_type_display,
                                    "Risk Description": risk_description,
                                    "Impact": impact,
                                    "Root Causes": root_causes,
                                    "Components": components,
                                    "Original Severity Level": st.session_state['original_severity'],
                                    "New Severity Level": severity_level,
                                    "Original Likelihood Level": st.session_state['original_likelihood'],
                                    "New Likelihood Level": likelihood_level,
                                    "Original Detectability Level": st.session_state['original_detectability'],
                                    "New Detectability Level": detectability_level,
                                    "Original Overall Risk Level": st.session_state['original_risk_level'],
                                    "New Overall Risk Level": st.session_state['new_risk_level'],
                                    "ABBYY's Response": st.session_state['abbyy_response'],
                                    "FH Response": fh_response,
                                    "Change Notes": change_notes
                                }
                                
                                # Create a record in the Risk Changes table
                                result = risk_changes_table.create(data)
                                st.success("Changes saved successfully!")
                                
                                # Reset form after submission
                                st.session_state['form_stage'] = 'initial'
                                st.session_state['abbyy_response'] = None
                                del st.session_state['original_severity']
                                del st.session_state['original_likelihood']
                                del st.session_state['original_detectability']
                                del st.session_state['original_risk_level']
                                if 'new_risk_level' in st.session_state:
                                    del st.session_state['new_risk_level']
                                
                                # Use rerun instead of experimental_rerun
                                st.rerun()
                            else:
                                st.info("No changes detected. Nothing was saved.")
                                
                        except Exception as e:
                            st.error(f"Error saving changes: {e}")
                            
                            # Display the field names from the target table to help troubleshoot
                            try:
                                sample_record = risk_changes_table.first()
                                if sample_record:
                                    field_names = list(sample_record['fields'].keys())
                                    st.info(f"Available fields in the target table: {', '.join(field_names)}")
                            except:
                                pass
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
