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
st.title("FH Response")
st.subheader("Review ABBYY responses and provide feedback")

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
        selected_risk_reference = st.selectbox("Risk Reference", options=risk_references, key="risk_ref_fh")
    
    with col2:
        selected_fh_personnel = st.selectbox("FH Personnel", options=fh_personnel, key="fh_personnel_fh")
    
    with col3:
        selected_abbyy_personnel = st.selectbox("ABBYY Personnel", options=abbyy_personnel, key="abbyy_personnel_fh")
    
    # Load risk details once selected
    filtered_record = app.get_risk_details(records_df, selected_risk_reference)
    
    if filtered_record:
        # Extract record ID
        record_id = filtered_record.get('record_id')
        
        # Get risk type display
        risk_types_dict = st.session_state.get('risk_types_dict', {})
        risk_type_display, risk_type_ids = app.get_risk_type_display(filtered_record, risk_types_dict)
        
        # Get ABBYY response from risk changes table
        risk_changes_record = app.get_risk_changes_record(risk_changes_table, selected_risk_reference)
        
        if not risk_changes_record:
            st.warning("No ABBYY response found for this risk reference. Please have ABBYY submit their response first.")
            st.stop()
        
        # Extract fields from risk changes record
        abbyy_record_fields = risk_changes_record.get('fields', {})
        
        # Get ABBYY's response
        abbyy_response = ""
        if 'ABBYY\'s Response' in abbyy_record_fields:
            abbyy_response = abbyy_record_fields['ABBYY\'s Response']
        elif 'fldQ66bxR2keyBdHm' in abbyy_record_fields:
            abbyy_response = abbyy_record_fields['fldQ66bxR2keyBdHm']
        
        # Display risk details (uneditable)
        st.write("### Risk Details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Risk Type
            st.text_input("Risk Type", value=risk_type_display, disabled=True, key="risk_type_fh")
            
            # Risk Category
            risk_category = ""
            if 'Risk category (from Risk types)' in filtered_record:
                risk_category = app.clean_display_value(filtered_record['Risk category (from Risk types)'])
            elif 'fldARoA6U91O9wKiZ' in filtered_record:
                risk_category = app.clean_display_value(filtered_record['fldARoA6U91O9wKiZ'])
            
            st.text_input("Risk Category", value=risk_category, disabled=True, key="risk_category_fh")
            
            # Components
            components = ""
            if 'Component (Where will the risk occur)' in filtered_record:
                components = app.clean_display_value(filtered_record['Component (Where will the risk occur)'])
            elif 'fldlCW5th0RdZg1in' in filtered_record:
                components = app.clean_display_value(filtered_record['fldlCW5th0RdZg1in'])
            
            st.text_area("Components", value=components, disabled=True, key="components_fh")
        
        with col2:
            # Risk Description
            risk_description = ""
            if 'Risk description' in filtered_record:
                risk_description = app.clean_display_value(filtered_record['Risk description'])
            elif 'fldqKOmtleXVuuhKE' in filtered_record:
                risk_description = app.clean_display_value(filtered_record['fldqKOmtleXVuuhKE'])
            
            st.text_area("Risk Description", value=risk_description, disabled=True, key="risk_description_fh")
            
            # Root Causes
            root_causes = ""
            if 'Rootcause description (from rootcause)' in filtered_record:
                root_causes = app.clean_display_value(filtered_record['Rootcause description (from rootcause)'])
            elif 'fld00wYhLLvTGZkPM' in filtered_record:
                root_causes = app.clean_display_value(filtered_record['fld00wYhLLvTGZkPM'])
            
            st.text_area("Root Causes", value=root_causes, disabled=True, key="root_causes_fh")
            
            # Impact
            impact = ""
            if 'Impact' in filtered_record:
                impact = app.clean_display_value(filtered_record['Impact'])
            elif 'fldc2ec6pUigCtOSb' in filtered_record:
                impact = app.clean_display_value(filtered_record['fldc2ec6pUigCtOSb'])
            
            st.text_area("Impact", value=impact, disabled=True, key="impact_fh")
        
        # Display ABBYY Response section
        st.write("### ABBYY Response")
        
        # Show ABBYY's response
        st.info(f"ABBYY's Response: **{abbyy_response}**")
        
        # If ABBYY selected "Change", show the changes
        if abbyy_response == "Change":
            st.write("#### Changes Made By ABBYY")
            
            # Get original and new values
            original_severity = ""
            if 'Original Severity Level' in abbyy_record_fields:
                original_severity = abbyy_record_fields['Original Severity Level']
            elif 'fldTr9bdRevGV7zyi' in abbyy_record_fields:
                original_severity = abbyy_record_fields['fldTr9bdRevGV7zyi']
            
            new_severity = ""
            if 'New Severity Level' in abbyy_record_fields:
                new_severity = abbyy_record_fields['New Severity Level']
            elif 'fldEYZSgQTr00GHf5' in abbyy_record_fields:
                new_severity = abbyy_record_fields['fldEYZSgQTr00GHf5']
            
            original_likelihood = ""
            if 'Original Likelihood Level' in abbyy_record_fields:
                original_likelihood = abbyy_record_fields['Original Likelihood Level']
            elif 'fldUZEGlpdaMMGTC9' in abbyy_record_fields:
                original_likelihood = abbyy_record_fields['fldUZEGlpdaMMGTC9']
            
            new_likelihood = ""
            if 'New Likelihood Level' in abbyy_record_fields:
                new_likelihood = abbyy_record_fields['New Likelihood Level']
            elif 'fld860nkAw1DUJaro' in abbyy_record_fields:
                new_likelihood = abbyy_record_fields['fld860nkAw1DUJaro']
            
            original_detectability = ""
            if 'Original Detectability Level' in abbyy_record_fields:
                original_detectability = abbyy_record_fields['Original Detectability Level']
            elif 'fldXO1FfoUa89lnsA' in abbyy_record_fields:
                original_detectability = abbyy_record_fields['fldXO1FfoUa89lnsA']
            
            new_detectability = ""
            if 'New Detectability Level' in abbyy_record_fields:
                new_detectability = abbyy_record_fields['New Detectability Level']
            elif 'fld60ppjc9HEM8RPo' in abbyy_record_fields:
                new_detectability = abbyy_record_fields['fld60ppjc9HEM8RPo']
            
            original_risk_level = ""
            if 'Original Overall Risk Level' in abbyy_record_fields:
                original_risk_level = abbyy_record_fields['Original Overall Risk Level']
            elif 'fldXsSjjUWPjRftIm' in abbyy_record_fields:
                original_risk_level = abbyy_record_fields['fldXsSjjUWPjRftIm']
            
            new_risk_level = ""
            if 'New Overall Risk Level' in abbyy_record_fields:
                new_risk_level = abbyy_record_fields['New Overall Risk Level']
            elif 'fldDJXURZKKyfz8pg' in abbyy_record_fields:
                new_risk_level = abbyy_record_fields['fldDJXURZKKyfz8pg']
            
            # Get risk score if available
            risk_score = ""
            if 'Risk Score' in abbyy_record_fields:
                risk_score = abbyy_record_fields['Risk Score']
            elif 'fldP1TiJw5FWkrQn0' in abbyy_record_fields:
                risk_score = abbyy_record_fields['fldP1TiJw5FWkrQn0']
            
            # Display the changes in a table
            changes_data = {
                "Parameter": ["Severity", "Likelihood", "Detectability", "Overall Risk Level"],
                "Original Value": [original_severity, original_likelihood, original_detectability, original_risk_level],
                "New Value": [new_severity, new_likelihood, new_detectability, new_risk_level]
            }
            
            changes_df = pd.DataFrame(changes_data)
            st.table(changes_df)
            
            # Show risk score if available
            if risk_score:
                st.write(f"Risk Score: **{risk_score}**")
        
        # FH Response section
        st.write("### FH Response")
        
        # FH Response options
        fh_response_options = ["Accept", "Unsure"]
        
        # Default to "Accept" if ABBYY selected "Accept"
        default_fh_response = "Accept" if abbyy_response == "Accept" else "Unsure"
        
        # Allow FH to choose response
        fh_response = st.radio(
            "FH Response", 
            options=fh_response_options, 
            index=fh_response_options.index(default_fh_response),
            key="fh_resp",
            horizontal=True
        )
        
        # Notes field
        change_notes = st.text_area("Notes", key="change_notes", 
                                   help="Add any additional notes about this risk assessment")
        
        # Save button
        if st.button("Save FH Response"):
            try:
                # Check if risk_changes_table is available
                if not risk_changes_table:
                    st.error(f"Cannot access '{app.RISK_CHANGES_TABLE_NAME}' table. Please check permissions.")
                    st.stop()
                
                # Get the record ID from the risk changes record
                record_id_to_update = risk_changes_record['id']
                
                # Create update data
                update_data = {
                    "fldj5ERls7Jsaq21H": fh_response,  # FH Response
                    "fldmpEa117ZHBlJAN": change_notes,  # Change Notes
                    "fldfTsmdEsXG2dcAo": "Todo"  # Status
                }
                
                try:
                    # Update the existing record in the Risk Changes table
                    result = risk_changes_table.update(record_id_to_update, update_data)
                    st.success("FH response saved successfully!")
                except Exception as field_id_error:
                    st.error(f"Error updating with field IDs: {field_id_error}")
                    st.info("Trying alternative method with field names...")
                    
                    # Try with field names instead
                    try:
                        update_data_by_name = {
                            "FH Response": fh_response,
                            "Change Notes": change_notes,
                            "Status": "Todo"
                        }
                        
                        result = risk_changes_table.update(record_id_to_update, update_data_by_name)
                        st.success("FH response saved successfully with field names!")
                    except Exception as name_error:
                        st.error(f"Error updating with field names: {name_error}")
                        
                        # Try direct API call as last resort
                        try:
                            api_response = requests.patch(
                                f"https://api.airtable.com/v0/{app.BASE_ID}/{app.RISK_CHANGES_TABLE_ID}/{record_id_to_update}",
                                headers={
                                    "Authorization": f"Bearer {app.AIRTABLE_API_KEY}",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "fields": update_data
                                }
                            )
                            
                            if api_response.status_code in [200, 201]:
                                st.success("Successfully saved using direct API call!")
                            else:
                                st.error(f"API error: {api_response.status_code}")
                                if app.show_debug:
                                    st.write(api_response.json())
                        except Exception as api_error:
                            st.error(f"Direct API call failed: {api_error}")
            except Exception as e:
                st.error(f"Error saving FH response: {e}")
                st.info("Please check your Airtable configuration.")
    else:
        st.info("Please select a valid Risk Reference to load the risk details.")
else:
    st.warning("No records found in Risk Register table.") 