import streamlit as st
import pandas as pd
import requests
import sys
import os
from pathlib import Path

# Add the app directory to the Python path to import common functions
sys.path.append(str(Path(__file__).parent.parent))
import app

# Page title
st.title("ABBYY Response")
st.subheader("Review and respond to risks")

# Check if connected
if not st.session_state.get('connected', False):
    st.info("Please connect to Airtable using the sidebar button to begin.")
    st.stop()

# Get tables from session state
risk_register_table = st.session_state.get('risk_register_table')
risk_changes_table = st.session_state.get('risk_changes_table')
records_df = st.session_state.get('records_df')

# Create lists for dropdowns
if records_df is not None and not records_df.empty:
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
    
    # Display form for selecting risk
    st.write("### Risk Selection")
    
    # Three dropdowns for selection
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_risk_reference = st.selectbox("Risk Reference", options=risk_references, key="risk_ref_abbyy")
    
    with col2:
        selected_fh_personnel = st.selectbox("FH Personnel", options=fh_personnel, key="fh_personnel_abbyy")
    
    with col3:
        selected_abbyy_personnel = st.selectbox("ABBYY Personnel", options=abbyy_personnel, key="abbyy_personnel_abbyy")
    
    # Load risk details once selected
    filtered_record = app.get_risk_details(records_df, selected_risk_reference)
    
    if filtered_record:
        # Extract record ID
        record_id = filtered_record.get('record_id')
        
        # Get risk type display
        risk_types_dict = st.session_state.get('risk_types_dict', {})
        risk_type_display, risk_type_ids = app.get_risk_type_display(filtered_record, risk_types_dict)
        
        # Display risk details (uneditable)
        st.write("### Risk Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Risk Type
            st.text_input("Risk Type", value=risk_type_display, disabled=True, key="risk_type_abbyy")
            
            # Risk Category
            risk_category = ""
            if 'Risk category (from Risk types)' in filtered_record:
                risk_category = app.clean_display_value(filtered_record['Risk category (from Risk types)'])
            elif 'fldARoA6U91O9wKiZ' in filtered_record:
                risk_category = app.clean_display_value(filtered_record['fldARoA6U91O9wKiZ'])
            
            st.text_input("Risk Category", value=risk_category, disabled=True, key="risk_category_abbyy")
            
            # Components
            components = ""
            if 'Component (Where will the risk occur)' in filtered_record:
                components = app.clean_display_value(filtered_record['Component (Where will the risk occur)'])
            elif 'fldlCW5th0RdZg1in' in filtered_record:
                components = app.clean_display_value(filtered_record['fldlCW5th0RdZg1in'])
            
            st.text_area("Components", value=components, disabled=True, key="components_abbyy")
        
        with col2:
            # Risk Description
            risk_description = ""
            if 'Risk description' in filtered_record:
                risk_description = app.clean_display_value(filtered_record['Risk description'])
            elif 'fldqKOmtleXVuuhKE' in filtered_record:
                risk_description = app.clean_display_value(filtered_record['fldqKOmtleXVuuhKE'])
            
            st.text_area("Risk Description", value=risk_description, disabled=True, key="risk_description_abbyy")
            
            # Root Causes
            root_causes = ""
            if 'Rootcause description (from rootcause)' in filtered_record:
                root_causes = app.clean_display_value(filtered_record['Rootcause description (from rootcause)'])
            elif 'fld00wYhLLvTGZkPM' in filtered_record:
                root_causes = app.clean_display_value(filtered_record['fld00wYhLLvTGZkPM'])
            
            st.text_area("Root Causes", value=root_causes, disabled=True, key="root_causes_abbyy")
            
            # Impact
            impact = ""
            if 'Impact' in filtered_record:
                impact = app.clean_display_value(filtered_record['Impact'])
            elif 'fldc2ec6pUigCtOSb' in filtered_record:
                impact = app.clean_display_value(filtered_record['fldc2ec6pUigCtOSb'])
            
            st.text_area("Impact", value=impact, disabled=True, key="impact_abbyy")
        
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
        
        # Store original values in session state for this risk
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
        
        # Initialize ABBYY response
        if 'abbyy_response' not in st.session_state:
            st.session_state['abbyy_response'] = "Accept"
        
        # ABBYY's Response selection
        abbyy_response_options = ["Accept", "Change"]
        abbyy_response = st.radio(
            "ABBYY's Response", 
            options=abbyy_response_options,
            key="abbyy_resp",
            horizontal=True
        )
        
        # Store selection in session state
        st.session_state['abbyy_response'] = abbyy_response
        
        # Show editable fields only if "Change" is selected
        is_editable = (abbyy_response == "Change")
        
        # Function to update risk level based on current selections
        def update_risk_level():
            severity = st.session_state.get('severity_abbyy', st.session_state['original_severity'])
            likelihood = st.session_state.get('likelihood_abbyy', st.session_state['original_likelihood'])
            detectability = st.session_state.get('detectability_abbyy', st.session_state['original_detectability'])
            
            new_level, overall_score = app.calculate_risk_level(severity, likelihood, detectability)
            
            st.session_state['new_risk_level'] = new_level
            st.session_state['risk_score'] = overall_score
        
        with col1:
            # Severity
            severity_index = severity_options.index(default_severity) if default_severity in severity_options else 0
            severity_level = st.selectbox(
                "Severity Level", 
                options=severity_options, 
                index=severity_index,
                key="severity_abbyy",
                disabled=not is_editable,
                on_change=update_risk_level if is_editable else None
            )
        
        with col2:
            # Likelihood
            likelihood_index = likelihood_options.index(default_likelihood) if default_likelihood in likelihood_options else 0
            likelihood_level = st.selectbox(
                "Likelihood Level", 
                options=likelihood_options, 
                index=likelihood_index,
                key="likelihood_abbyy",
                disabled=not is_editable,
                on_change=update_risk_level if is_editable else None
            )
        
        with col3:
            # Detectability
            detectability_index = detectability_options.index(default_detectability) if default_detectability in detectability_options else 0
            detectability_level = st.selectbox(
                "Detectability Level", 
                options=detectability_options, 
                index=detectability_index,
                key="detectability_abbyy",
                disabled=not is_editable,
                on_change=update_risk_level if is_editable else None
            )
        
        with col4:
            # Calculate and display risk level
            if is_editable:
                # Get current values
                severity = st.session_state.get('severity_abbyy', severity_level)
                likelihood = st.session_state.get('likelihood_abbyy', likelihood_level)
                detectability = st.session_state.get('detectability_abbyy', detectability_level)
                
                # Calculate new risk level
                new_level, overall_score = app.calculate_risk_level(severity, likelihood, detectability)
                
                # Update session state
                st.session_state['new_risk_level'] = new_level
                st.session_state['risk_score'] = overall_score
                
                # Display the result
                st.text_input("Overall Risk Level", 
                            value=f"{new_level} (Score: {overall_score})", 
                            disabled=True,
                            key="risk_level_abbyy")
            else:
                # Show original risk level when not in edit mode
                st.text_input("Overall Risk Level", 
                            value=str(st.session_state.get('original_risk_level', "")), 
                            disabled=True,
                            key="original_risk_level_abbyy")
        
        # Save button
        if st.button("Save ABBYY Response"):
            try:
                # Check if risk_changes_table is available
                if not risk_changes_table:
                    st.error(f"Cannot access '{app.RISK_CHANGES_TABLE_NAME}' table. Please check permissions.")
                    st.info("Make sure your API key has access to the table with ID: " + app.RISK_CHANGES_TABLE_ID)
                    st.stop()
                
                # Only save if there's a change or user explicitly wants to save
                has_changes = (
                    abbyy_response == "Change" and (
                        severity_level != st.session_state['original_severity'] or
                        likelihood_level != st.session_state['original_likelihood'] or
                        detectability_level != st.session_state['original_detectability']
                    )
                )
                
                if abbyy_response == "Accept" or has_changes:
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
                        "fldEYZSgQTr00GHf5": str(severity_level) if abbyy_response == "Change" else "",  # New Severity Level
                        "fldUZEGlpdaMMGTC9": str(st.session_state.get('original_likelihood', default_likelihood)),  # Original Likelihood Level
                        "fld860nkAw1DUJaro": str(likelihood_level) if abbyy_response == "Change" else "",  # New Likelihood Level
                        "fldXO1FfoUa89lnsA": str(st.session_state.get('original_detectability', default_detectability)),  # Original Detectability Level
                        "fld60ppjc9HEM8RPo": str(detectability_level) if abbyy_response == "Change" else "",  # New Detectability Level
                        "fldXsSjjUWPjRftIm": str(st.session_state.get('original_risk_level', "")),  # Original Overall Risk Level
                        "fldDJXURZKKyfz8pg": str(st.session_state.get('new_risk_level', "")) if abbyy_response == "Change" else "",  # New Overall Risk Level
                        "fldQ66bxR2keyBdHm": str(abbyy_response),  # ABBYY's Response
                    }
                    
                    # Ensure all values are JSON-safe (no NaN values)
                    sanitized_data = {k: app.json_safe_value(v) for k, v in data.items()}
                    
                    try:
                        # Create a record in the Risk Changes table
                        result = risk_changes_table.create(sanitized_data)
                        st.success("ABBYY response saved successfully!")
                        
                        # Store the created record ID in session state for FH page to reference
                        st.session_state[f"risk_changes_id_{record_id}"] = result['id']
                        
                    except Exception as field_id_error:
                        st.error(f"Error saving with field IDs: {field_id_error}")
                        st.info("Trying alternative method with field names...")
                        
                        # Try with field names instead
                        try:
                            # Create data dictionary using field names
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
                                "Original Severity Level": str(st.session_state.get('original_severity', default_severity)),
                                "New Severity Level": str(severity_level) if abbyy_response == "Change" else "",
                                "Original Likelihood Level": str(st.session_state.get('original_likelihood', default_likelihood)),
                                "New Likelihood Level": str(likelihood_level) if abbyy_response == "Change" else "",
                                "Original Detectability Level": str(st.session_state.get('original_detectability', default_detectability)),
                                "New Detectability Level": str(detectability_level) if abbyy_response == "Change" else "",
                                "Original Overall Risk Level": str(st.session_state.get('original_risk_level', "")),
                                "New Overall Risk Level": str(st.session_state.get('new_risk_level', "")) if abbyy_response == "Change" else "",
                                "ABBYY's Response": str(abbyy_response),
                            }
                            
                            # Ensure all values are JSON-safe
                            sanitized_name_data = {k: app.json_safe_value(v) for k, v in data_by_name.items()}
                            
                            result = risk_changes_table.create(sanitized_name_data)
                            st.success("ABBYY response saved successfully with field names!")
                            
                            # Store the created record ID
                            st.session_state[f"risk_changes_id_{record_id}"] = result['id']
                            
                        except Exception as name_error:
                            st.error(f"Error saving with field names: {name_error}")
                            
                            # Try direct API call as last resort
                            try:
                                api_response = requests.post(
                                    f"https://api.airtable.com/v0/{app.BASE_ID}/{app.RISK_CHANGES_TABLE_ID}",
                                    headers={
                                        "Authorization": f"Bearer {app.AIRTABLE_API_KEY}",
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
                                
                                if api_response.status_code in [200, 201]:
                                    st.success("Successfully saved using direct API call!")
                                    
                                    # Try to get the record ID from the response
                                    try:
                                        response_data = api_response.json()
                                        if 'records' in response_data and len(response_data['records']) > 0:
                                            st.session_state[f"risk_changes_id_{record_id}"] = response_data['records'][0]['id']
                                    except:
                                        pass
                                else:
                                    st.error(f"API error: {api_response.status_code}")
                                    if app.show_debug:
                                        st.write(api_response.json())
                            except Exception as api_error:
                                st.error(f"Direct API call failed: {api_error}")
                else:
                    st.info("No changes detected. Nothing was saved.")
            except Exception as e:
                st.error(f"Error saving changes: {e}")
                st.info("Please check your Airtable configuration.")
    else:
        st.info("Please select a valid Risk Reference to load the risk details.")
else:
    st.warning("No records found in Risk Register table.") 