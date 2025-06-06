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
        
        # Create multiselect dropdown for responsible party instead of single-select
        selected_responsible = st.multiselect(
            "Who is responsible?",
            options=responsible_options,
            default=[],
            key="filter_responsible"
        )
    
    with filter_col2:
        # Create multiselect for Overall Risk Level with predefined options
        risk_level_options = ["3. Moderate", "4. High", "5. Critical"]
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
    
    # Apply filter for Who is responsible (if any selected)
    if selected_responsible:
        # Find the appropriate column for Who is responsible
        responsible_column = None
        for column in ['fld6jqOm7dmjdXKRy', 'Who is responsible?', 'Who is responsible']:
            if column in filtered_records.columns:
                responsible_column = column
                break
        
        if responsible_column:
            try:
                # Filter records where any of the selected responsible parties are present
                filtered_records_list = []
                
                for _, row in filtered_records.iterrows():
                    if responsible_column in row:
                        value = row[responsible_column]
                        # Handle different data formats
                        if isinstance(value, list):
                            if any(resp in value for resp in selected_responsible):
                                filtered_records_list.append(row)
                        elif isinstance(value, str):
                            str_value = value.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
                            if any(resp in str_value for resp in selected_responsible):
                                filtered_records_list.append(row)
                
                if filtered_records_list:
                    filtered_records = pd.DataFrame(filtered_records_list)
                else:
                    # If no records found with this approach, try a broader match
                    mask = pd.Series(False, index=filtered_records.index)
                    for resp in selected_responsible:
                        mask = mask | filtered_records[responsible_column].astype(str).str.contains(resp, na=False)
                    filtered_records = filtered_records[mask]
            except Exception as e:
                st.warning(f"Error filtering by responsible party: {e}")
    
    # Apply filter for risk levels (if any selected)
    if selected_risk_levels:
        # Find the appropriate column for risk level
        risk_level_column = None
        for column in ['fldJtc0r2NsqF5UPV', 'Overall Risk Level']:
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
            if 'Overall Risk Score' in filtered_record:
                overall_risk_level = filtered_record['Overall Risk Score']
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
                
                # Initialize flags to track if user has changed values
                st.session_state['user_changed_values'] = False

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

            # Function to track changes and update risk score
            def on_value_change():
                # Mark that user has changed values
                st.session_state['user_changed_values'] = True
                
                # Get current dropdown values directly from session state
                severity = st.session_state.get('severity_abbyy')
                likelihood = st.session_state.get('likelihood_abbyy')
                detectability = st.session_state.get('detectability_abbyy')
                
                # Only calculate if all values are available
                if severity and likelihood and detectability:
                    # Custom calculation per the specified formula
                    # For Severity
                    severity_value = 3 if severity == "1. High" else (2 if severity == "2. Medium" else 1)
                    
                    # For Likelihood
                    likelihood_value = 3 if likelihood == "1. High" else (2 if likelihood == "2. Medium" else 1)
                    
                    # For Detectability (note inverse order!)
                    detectability_value = 3 if detectability == "3. Low" else (2 if detectability == "2. Medium" else 1)
                    
                    # Calculate overall score
                    overall_score = severity_value * likelihood_value * detectability_value
                    
                    # Determine risk level based on score
                    if overall_score >= 27:
                        new_level = "5. Critical"
                    elif overall_score >= 18:
                        new_level = "4. High"
                    elif overall_score >= 8:
                        new_level = "3. Moderate"
                    elif overall_score >= 4:
                        new_level = "2. Low"
                    else:
                        new_level = "1. Very Low"
                    
                    # Store results in session state
                    st.session_state['new_risk_level'] = new_level
                    st.session_state['risk_score'] = overall_score
                    
                    # Force a rerun to update the display
                    st.rerun()

            with col1:
                # Severity
                severity_index = severity_options.index(severity_level) if severity_level in severity_options else 0
                severity_display = st.selectbox(
                    "Severity Level", 
                    options=severity_options, 
                    index=severity_index,
                    key="severity_abbyy",
                    disabled=not is_editable,
                    on_change=on_value_change if is_editable else None
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
                    on_change=on_value_change if is_editable else None
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
                    on_change=on_value_change if is_editable else None
                )

            with col4:
                # Display risk score
                if is_editable:
                    # Check if the user has changed any values
                    if st.session_state.get('user_changed_values', False):
                        # User has made changes, show the new calculated risk score
                        new_level = st.session_state.get('new_risk_level')
                        overall_score = st.session_state.get('risk_score')
                        
                        if new_level and overall_score:
                            risk_display = f"{new_level} (Score: {overall_score})"
                        else:
                            # Calculate right here instead of using app.calculate_risk_level
                            severity = st.session_state.get('severity_abbyy')
                            likelihood = st.session_state.get('likelihood_abbyy')
                            detectability = st.session_state.get('detectability_abbyy')
                            
                            if severity and likelihood and detectability:
                                # For Severity
                                severity_value = 3 if severity == "1. High" else (2 if severity == "2. Medium" else 1)
                                
                                # For Likelihood
                                likelihood_value = 3 if likelihood == "1. High" else (2 if likelihood == "2. Medium" else 1)
                                
                                # For Detectability (note inverse order!)
                                detectability_value = 3 if detectability == "3. Low" else (2 if detectability == "2. Medium" else 1)
                                
                                # Calculate overall score
                                overall_score = severity_value * likelihood_value * detectability_value
                                
                                # Determine risk level based on score
                                if overall_score >= 27:
                                    new_level = "5. Critical"
                                elif overall_score >= 18:
                                    new_level = "4. High"
                                elif overall_score >= 8:
                                    new_level = "3. Moderate"
                                elif overall_score >= 4:
                                    new_level = "2. Low"
                                else:
                                    new_level = "1. Very Low"
                                
                                st.session_state['new_risk_level'] = new_level
                                st.session_state['risk_score'] = overall_score
                                risk_display = f"{new_level} (Score: {overall_score})"
                            else:
                                risk_display = "Incomplete data"
                    else:
                        # No changes yet, so show the original risk score
                        original_risk_level = st.session_state.get('original_risk_level', "")
                        
                        # Format for display - same formatting function as in non-editable mode
                        risk_display = ""
                        if original_risk_level:
                            try:
                                if isinstance(original_risk_level, (int, float)) or (isinstance(original_risk_level, str) and original_risk_level.replace('.', '', 1).isdigit()):
                                    score = float(original_risk_level)
                                    if score >= 27:
                                        risk_display = "5. Critical (Score: {})".format(score)
                                    elif score >= 18:
                                        risk_display = "4. High (Score: {})".format(score)
                                    elif score >= 8:
                                        risk_display = "3. Moderate (Score: {})".format(score)
                                    elif score >= 4:
                                        risk_display = "2. Low (Score: {})".format(score)
                                    else:
                                        risk_display = "1. Very Low (Score: {})".format(score)
                                else:
                                    risk_display = str(original_risk_level)
                            except:
                                risk_display = str(original_risk_level)
                        else:
                            risk_display = "No original risk score found"
                    
                    st.text_input("Overall Risk Score", 
                                value=risk_display, 
                                disabled=True,
                                key="risk_score_abbyy")
                else:
                    # Show original risk score when not in edit mode
                    original_risk_level = st.session_state.get('original_risk_level', "")
                    
                    # Format for display
                    risk_level_display = ""
                    if original_risk_level:
                        try:
                            if isinstance(original_risk_level, (int, float)) or (isinstance(original_risk_level, str) and original_risk_level.replace('.', '', 1).isdigit()):
                                score = float(original_risk_level)
                                if score >= 27:
                                    risk_level_display = "5. Critical (Score: {})".format(score)
                                elif score >= 18:
                                    risk_level_display = "4. High (Score: {})".format(score)
                                elif score >= 8:
                                    risk_level_display = "3. Moderate (Score: {})".format(score)
                                elif score >= 4:
                                    risk_level_display = "2. Low (Score: {})".format(score)
                                else:
                                    risk_level_display = "1. Very Low (Score: {})".format(score)
                            else:
                                risk_level_display = str(original_risk_level)
                        except:
                            risk_level_display = str(original_risk_level)
                    
                    st.text_input("Overall Risk Score", 
                                value=risk_level_display, 
                                disabled=True,
                                key="original_risk_score_abbyy")
            
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
                        # Get just the risk level name (without the score part)
                        new_risk_level = st.session_state.get('new_risk_level', "")
                        
                        # Format the original risk level to show just the level name
                        original_risk_display = ""
                        original_risk_level = st.session_state.get('original_risk_level', "")
                        
                        if original_risk_level:
                            try:
                                # If it's a numeric score, convert to level name
                                if isinstance(original_risk_level, (int, float)) or (isinstance(original_risk_level, str) and original_risk_level.replace('.', '', 1).isdigit()):
                                    score = float(original_risk_level)
                                    if score >= 27:
                                        original_risk_display = "5. Critical"
                                    elif score >= 18:
                                        original_risk_display = "4. High"
                                    elif score >= 8:
                                        original_risk_display = "3. Moderate"
                                    elif score >= 4:
                                        original_risk_display = "2. Low"
                                    else:
                                        original_risk_display = "1. Very Low"
                                else:
                                    # If it's already a text format, use it directly
                                    original_risk_display = str(original_risk_level)
                            except:
                                original_risk_display = str(original_risk_level)
                        
                        # Handle linked record fields properly - get record IDs instead of display values
                        # For Risk Type, use the record IDs if available
                        risk_type_value = ""
                        if risk_type_ids:
                            # If we have record IDs, use them as an array
                            risk_type_value = risk_type_ids
                        else:
                            # Fallback to display text if no IDs available
                            risk_type_value = str(risk_type_display) if risk_type_display else ""
                        
                        # Create data dictionary using field IDs directly
                        data = {
                            "fldJwiM65ftTV4wA3": str(selected_risk_reference) if selected_risk_reference else "",  # Original Risk Reference - TEXT FIELD, use string
                            "fldMvXyJc8zCAHJJg": str(selected_fh_personnel) if selected_fh_personnel else "",  # FH Personnel
                            "fld6RKhK7kWfsJost": str(selected_abbyy_personnel) if selected_abbyy_personnel else "",  # ABBYY Personnel
                            "fldfTsmdEsXG2dcAo": "Todo",  # Status
                            "flde0fUGwJlykaRnM": str(risk_category) if risk_category else "",  # Risk Category - text field
                            "fldYdVmw8pCKyRagq": risk_type_value,  # Risk Type - handle as linked record if IDs available
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
                            "fldXsSjjUWPjRftIm": original_risk_display,  # Original Overall Risk Level
                            "fldDJXURZKKyfz8pg": new_risk_level if abbyy_response == "Change" else "",  # New Overall Risk Level
                            "fldQ66bxR2keyBdHm": str(abbyy_response),  # ABBYY's Response
                            "fldv1dx6ISiPTrzx4": str(abbyy_comment) if abbyy_comment else "",  # ABBYY Comments
                        }
                        
                        # Ensure all values are JSON-safe (no NaN values)
                        sanitized_data = {k: app.json_safe_value(v) for k, v in data.items()}
                        
                        try:
                            # Create a record in the Risk Changes table
                            result = risk_changes_table.create(sanitized_data)
                            st.success("✅ ABBYY response saved successfully!")
                            
                            # Store the created record ID in session state for FH page to reference
                            st.session_state[f"risk_changes_id_{record_id}"] = result['id']
                            
                        except Exception as e:
                            st.error(f"Error saving response: {e}")
                            
                    else:
                        st.info("No changes detected. Nothing was saved.")
                        
                except Exception as e:
                    st.error(f"Unexpected error: {e}")
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