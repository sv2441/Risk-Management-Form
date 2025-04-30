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

# Debug information
st.write(f"Records found: {len(records_df) if records_df is not None else 'None'}")

# Create lists for dropdowns
if records_df is not None and not records_df.empty:
    # Add filter section before risk selection
    st.write("### Filter Risks")
    filter_col1, filter_col2, filter_col3 = st.columns(3)  # Changed to 3 columns for the new filter
    
    with filter_col1:
        # Get unique "Who is responsible?" values
        responsible_options = []
        if 'fld6jqOm7dmjdXKRy' in records_df.columns:
            # Extract values from the array field
            all_responsible = []
            for resp in records_df['fld6jqOm7dmjdXKRy'].dropna():
                if isinstance(resp, list):
                    all_responsible.extend(resp)
                elif isinstance(resp, str):
                    # Handle string format like "[\"Product\"]"
                    cleaned = resp.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
                    items = [item.strip() for item in cleaned.split(',')]
                    all_responsible.extend(items)
            
            # Get unique values
            responsible_options = sorted(list(set([r for r in all_responsible if r])))
        
        if not responsible_options:
            # Try alternative field names
            for field in ['Who is responsible?', 'Who is responsible']:
                if field in records_df.columns:
                    all_responsible = []
                    for resp in records_df[field].dropna():
                        if isinstance(resp, list):
                            all_responsible.extend(resp)
                        elif isinstance(resp, str):
                            cleaned = resp.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
                            items = [item.strip() for item in cleaned.split(',')]
                            all_responsible.extend(items)
                    
                    responsible_options = sorted(list(set([r for r in all_responsible if r])))
                    break
        
        # Add "All" option at the beginning
        responsible_options = ["All"] + responsible_options
        
        # Create single-select dropdown for responsible party
        selected_responsible = st.selectbox(
            "Who is responsible?",
            options=responsible_options,
            index=0,
            key="filter_responsible"
        )
    
    with filter_col2:
        # Create multiselect for Overall Risk Level with predefined options
        risk_level_options = ["3. Moderate", "4. High", "5. Severe"]
        selected_risk_levels = st.multiselect(
            "Overall Risk Level",
            options=risk_level_options,
            key="filter_risk_level"
        )
    
    with filter_col3:
        # Add new filter for AI system reference
        ai_system_options = ["All", "IDP", "Process AI", "Enterprise"]
        selected_ai_system = st.selectbox(
            "AI System Reference",
            options=ai_system_options,
            index=0,
            key="filter_ai_system"
        )
    
    # Risk references - use whatever field has data
    risk_references = []
    filtered_records = records_df.copy()
    
    # Apply filter for Who is responsible (if not "All")
    if selected_responsible != "All":
        # Find the appropriate column for Who is responsible
        responsible_column = None
        for column in ['fld6jqOm7dmjdXKRy', 'Who is responsible?', 'Who is responsible']:
            if column in filtered_records.columns:
                responsible_column = column
                break
        
        if responsible_column:
            try:
                # Filter records where the selected responsible party is present
                filtered_records_list = []
                
                for _, row in filtered_records.iterrows():
                    if responsible_column in row:
                        value = row[responsible_column]
                        # Handle different data formats
                        if isinstance(value, list) and selected_responsible in value:
                            filtered_records_list.append(row)
                        elif isinstance(value, str):
                            if selected_responsible in value.replace('[', '').replace(']', '').replace('"', '').replace("'", ""):
                                filtered_records_list.append(row)
                
                if filtered_records_list:
                    filtered_records = pd.DataFrame(filtered_records_list)
                else:
                    # If no records found with this approach, try a broader match
                    mask = filtered_records[responsible_column].astype(str).str.contains(selected_responsible, na=False)
                    filtered_records = filtered_records[mask]
            except Exception as e:
                st.warning(f"Error filtering by responsible party: {e}")
    
    # Apply filter for risk levels (if any selected)
    if selected_risk_levels:
        # Find the appropriate column for risk level
        risk_level_column = None
        for column in ['fldJtc0r2NsqF5UPV', 'Overall Risk Level', 'Overall Risk Score']:
            if column in filtered_records.columns:
                risk_level_column = column
                break
        
        if risk_level_column:
            try:
                # Try direct matching first
                risk_level_mask = filtered_records[risk_level_column].isin(selected_risk_levels)
                if risk_level_mask.any():
                    filtered_records = filtered_records[risk_level_mask]
                else:
                    # If no direct matches, try string contains
                    level_mask = pd.Series(False, index=filtered_records.index)
                    for level in selected_risk_levels:
                        level_mask = level_mask | filtered_records[risk_level_column].astype(str).str.contains(level, na=False)
                    filtered_records = filtered_records[level_mask]
            except Exception as e:
                st.warning(f"Error filtering by risk level: {e}")
    
    # Apply filter for AI system reference (if not "All")
    if selected_ai_system != "All":
        # Find the appropriate column for AI system reference
        ai_system_column = None
        
        # Look for the column with more flexible matching (handle trailing spaces)
        for column in filtered_records.columns:
            if column.strip() == 'AI, algorithmic or autonomous system reference /name' or column == 'fldB5EPuCN5A5pD4V':
                ai_system_column = column
                break
        
        if ai_system_column:
            try:
                # Filter by exact match for AI system
                ai_system_mask = filtered_records[ai_system_column] == selected_ai_system
                
                # If no matches, try case-insensitive contains
                if not ai_system_mask.any():
                    ai_system_mask = filtered_records[ai_system_column].astype(str).str.contains(
                        selected_ai_system, case=False, na=False
                    )
                
                # Apply the filter
                filtered_records = filtered_records[ai_system_mask]
            except Exception as e:
                st.warning(f"Error filtering by AI system: {e}")
        else:
            st.warning("AI system column not found. Please check column names in your Airtable.")
    
    # Try common fields for risk references from filtered records
    for field in ['fldvQEaSVFnK3tmAo', 'Risk reference', 'Risk Reference']:
        if field in filtered_records.columns:
            risk_refs = filtered_records[field].dropna().tolist()
            if risk_refs:
                risk_references = [str(ref) for ref in risk_refs if ref is not None]
                break
    
    if not risk_references:
        # Fallback to record IDs if no references found
        risk_references = filtered_records['record_id'].tolist()
    
    # Display count of filtered risks
    st.info(f"Found {len(risk_references)} risk(s) matching your filter criteria.")
    
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
    if selected_risk_reference:
        # Get details directly from the original records_df, not from filtered records
        filtered_record = app.get_risk_details(records_df, selected_risk_reference)
        
        if not filtered_record:
            st.error(f"Could not find record for: {selected_risk_reference}")
        else:
            # Extract record ID
            record_id = filtered_record.get('record_id')
            
            # Get risk type display
            risk_types_dict = st.session_state.get('risk_types_dict', {})
            risk_type_display, risk_type_ids = app.get_risk_type_display(filtered_record, risk_types_dict)
            
            # Display risk details (uneditable)
            st.write("### Risk Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Process
                process = ""
                if 'Process' in filtered_record:
                    process = app.clean_display_value(filtered_record['Process'])
                elif 'fldogjZZsxB3oPcdv' in filtered_record:
                    process = app.clean_display_value(filtered_record['fldogjZZsxB3oPcdv'])
                
                st.text_input("Process", value=process, disabled=True, key="process_abbyy")
                
                # Sub Process
                sub_process = ""
                if 'Sub Process' in filtered_record:
                    sub_process = app.clean_display_value(filtered_record['Sub Process'])
                elif 'fldtE2ABpfY7asfn5' in filtered_record:
                    sub_process = app.clean_display_value(filtered_record['fldtE2ABpfY7asfn5'])
                
                st.text_input("Sub Process", value=sub_process, disabled=True, key="sub_process_abbyy")
                
                # Activity
                activity = ""
                if 'Activity' in filtered_record:
                    activity = app.clean_display_value(filtered_record['Activity'])
                elif 'fldkyb02e604tooNz' in filtered_record:
                    activity = app.clean_display_value(filtered_record['fldkyb02e604tooNz'])
                
                st.text_input("Activity", value=activity, disabled=True, key="activity_abbyy")
                
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

            # Comment out debug expander
            # with st.expander("Debug - Raw Field Values"):
            #     st.write("**Field IDs in record:**")
            #     field_list = list(filtered_record.keys())
            #     st.write(field_list)
            #     
            #     st.write("**Risk Assessment Field Contents:**")
            #     # Check for Severity
            #     for field in ['Severity', 'fld195IZccUi69V5D']:
            #         if field in filtered_record:
            #             st.write(f"{field}: {filtered_record[field]} (Type: {type(filtered_record[field])})")
            #     
            #     # Check for Likelihood
            #     for field in ['Likelihood', 'fldhdlk8KsdWNqgff']:
            #         if field in filtered_record:
            #             st.write(f"{field}: {filtered_record[field]} (Type: {type(filtered_record[field])})")
            #     
            #     # Check for Detectability
            #     for field in ['Detectability', 'fldfVsQ4b7qc8TAPP']:
            #         if field in filtered_record:
            #             st.write(f"{field}: {filtered_record[field]} (Type: {type(filtered_record[field])})")
            #     
            #     # Check for Overall Risk Level
            #     for field in ['Overall Risk Level', 'Overall Risk Score', 'fldJtc0r2NsqF5UPV', 'fldqLmmgCcAioHTi4']:
            #         if field in filtered_record:
            #             st.write(f"{field}: {filtered_record[field]} (Type: {type(filtered_record[field])})")

            col1, col2, col3, col4 = st.columns(4)

            # Update options to match the actual format in the data
            severity_options = ["1. High", "2. Medium", "3. Low"]
            likelihood_options = ["1. High", "2. Medium", "3. Low"]
            detectability_options = ["1. High", "2. Medium", "3. Low"]

            # Initialize variables with None - no defaults
            severity_level = None
            likelihood_level = None
            detectability_level = None

            # Get actual values only - no defaults
            # Severity
            if 'Severity' in filtered_record:
                severity_level = filtered_record['Severity']
            elif 'fld195IZccUi69V5D' in filtered_record:
                severity_level = filtered_record['fld195IZccUi69V5D']

            # Likelihood
            if 'Likelihood' in filtered_record:
                likelihood_level = filtered_record['Likelihood']
            elif 'fldhdlk8KsdWNqgff' in filtered_record:
                likelihood_level = filtered_record['fldhdlk8KsdWNqgff']

            # Detectability
            if 'Detectability' in filtered_record:
                detectability_level = filtered_record['Detectability']
            elif 'fldfVsQ4b7qc8TAPP' in filtered_record:
                detectability_level = filtered_record['fldfVsQ4b7qc8TAPP']

            # Overall Risk Level
            overall_risk_level = None
            if 'Overall Risk Level' in filtered_record:
                overall_risk_level = filtered_record['Overall Risk Level']
            elif 'Overall Risk Score' in filtered_record:
                overall_risk_level = filtered_record['Overall Risk Score']
            elif 'fldJtc0r2NsqF5UPV' in filtered_record:
                overall_risk_level = filtered_record['fldJtc0r2NsqF5UPV']
            elif 'fldqLmmgCcAioHTi4' in filtered_record:
                overall_risk_level = filtered_record['fldqLmmgCcAioHTi4']

            # Store original values in session state for this risk
            risk_id_key = f"risk_id_{record_id}"
            if risk_id_key not in st.session_state or st.session_state[risk_id_key] != record_id:
                # First time loading this specific risk, store original values
                st.session_state[risk_id_key] = record_id
                st.session_state['original_severity'] = severity_level
                st.session_state['original_likelihood'] = likelihood_level
                st.session_state['original_detectability'] = detectability_level
                st.session_state['original_risk_level'] = overall_risk_level

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

            # Add comment box if Change is selected
            abbyy_comment = ""
            if abbyy_response == "Change":
                abbyy_comment = st.text_area(
                    "ABBYY Change Comments", 
                    value="", 
                    height=100,
                    key="abbyy_comment",
                    help="Please provide your reasoning for the proposed changes"
                )

            # Show editable fields only if "Change" is selected
            is_editable = (abbyy_response == "Change")

            # Function to update risk level based on current selections
            def update_risk_level():
                severity = st.session_state.get('severity_abbyy')
                likelihood = st.session_state.get('likelihood_abbyy')
                detectability = st.session_state.get('detectability_abbyy')
                
                # Only calculate if all values are available
                if severity and likelihood and detectability:
                    new_level, overall_score = app.calculate_risk_level(severity, likelihood, detectability)
                    st.session_state['new_risk_level'] = new_level
                    st.session_state['risk_score'] = overall_score

            with col1:
                # Severity
                severity_index = severity_options.index(severity_level) if severity_level in severity_options else 0
                severity_display = st.selectbox(
                    "Severity Level", 
                    options=severity_options, 
                    index=severity_index,
                    key="severity_abbyy",
                    disabled=not is_editable,
                    on_change=update_risk_level if is_editable else None
                )

            with col2:
                # Likelihood
                likelihood_index = likelihood_options.index(likelihood_level) if likelihood_level in likelihood_options else 0
                likelihood_display = st.selectbox(
                    "Likelihood Level", 
                    options=likelihood_options, 
                    index=likelihood_index,
                    key="likelihood_abbyy",
                    disabled=not is_editable,
                    on_change=update_risk_level if is_editable else None
                )

            with col3:
                # Detectability
                detectability_index = detectability_options.index(detectability_level) if detectability_level in detectability_options else 0
                detectability_display = st.selectbox(
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
                    severity = st.session_state.get('severity_abbyy')
                    likelihood = st.session_state.get('likelihood_abbyy')
                    detectability = st.session_state.get('detectability_abbyy')
                    
                    # Calculate new risk level only if all values are present
                    if severity and likelihood and detectability:
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
                        st.text_input("Overall Risk Level", 
                                    value="Incomplete data", 
                                    disabled=True,
                                    key="risk_level_incomplete")
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
                            severity_display != st.session_state['original_severity'] or
                            likelihood_display != st.session_state['original_likelihood'] or
                            detectability_display != st.session_state['original_detectability']
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
                            "fldTr9bdRevGV7zyi": str(st.session_state.get('original_severity', severity_level)),  # Original Severity Level
                            "fldEYZSgQTr00GHf5": str(severity_display) if abbyy_response == "Change" else "",  # New Severity Level
                            "fldUZEGlpdaMMGTC9": str(st.session_state.get('original_likelihood', likelihood_level)),  # Original Likelihood Level
                            "fld860nkAw1DUJaro": str(likelihood_display) if abbyy_response == "Change" else "",  # New Likelihood Level
                            "fldXO1FfoUa89lnsA": str(st.session_state.get('original_detectability', detectability_level)),  # Original Detectability Level
                            "fld60ppjc9HEM8RPo": str(detectability_display) if abbyy_response == "Change" else "",  # New Detectability Level
                            "fldXsSjjUWPjRftIm": str(st.session_state.get('original_risk_level', overall_risk_level)),  # Original Overall Risk Level
                            "fldDJXURZKKyfz8pg": str(st.session_state.get('new_risk_level', "")),  # New Overall Risk Level
                            "fldQ66bxR2keyBdHm": str(abbyy_response),  # ABBYY's Response
                            "fldv1dx6ISiPTrzx4": str(abbyy_comment) if abbyy_comment else "",  # ABBYY Comments
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
                                    "Components": str(components) if components else "",
                                    "Original Severity Level": str(st.session_state.get('original_severity', severity_level)),
                                    "New Severity Level": str(severity_display) if abbyy_response == "Change" else "",
                                    "Original Likelihood Level": str(st.session_state.get('original_likelihood', likelihood_level)),
                                    "New Likelihood Level": str(likelihood_display) if abbyy_response == "Change" else "",
                                    "Original Detectability Level": str(st.session_state.get('original_detectability', detectability_level)),
                                    "New Detectability Level": str(detectability_display) if abbyy_response == "Change" else "",
                                    "Original Overall Risk Level": str(st.session_state.get('original_risk_level', overall_risk_level)),
                                    "New Overall Risk Level": str(st.session_state.get('new_risk_level', "")),
                                    "ABBYY's Response": str(abbyy_response),
                                    "ABBYY Comments": str(abbyy_comment) if abbyy_comment else "",
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
    # Add debug options
    if st.button("Reload Data"):
        # Force a reload of the data
        st.session_state.pop('records_df', None)
        st.session_state.pop('connected', None)
        app.load_risk_data()
        st.rerun() 