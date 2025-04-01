# Risk Management System

A Streamlit application for managing risk data with Airtable integration.

## Features

- Connect to an Airtable base to retrieve and update risk register entries
- View and modify risk details including categories, types, impacts, and components
- Update risk assessment levels (severity, likelihood, detectability)
- Track changes to risk assessments in a separate table
- Conditional form logic based on ABBYY's response

## Requirements

- Python 3.8+
- Streamlit
- PyAirtable
- pandas
- python-dotenv

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd risk-management-form
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your Airtable credentials:
```
AIRTABLE_API_KEY=your_api_key_here
AIRTABLE_BASE_ID=your_base_id_here
AIRTABLE_TABLE_ID=your_table_id_here
```

4. Airtable Structure:
   
   The application works with an Airtable base that has the following structure:
   
   **Process Risk Assessment Sheet (Main Table):**
   - Risk reference (fldvQEaSVFnK3tmAo): Auto Number
   - Risk types (fldNqIWQ5VqVT7itc): Link to another record
   - Risk category (fldARoA6U91O9wKiZ): Lookup
   - Risk description (fldqKOmtleXVuuhKE): Long text
   - Component (fldlCW5th0RdZg1in): Multiple select
   - Impact (fldc2ec6pUigCtOSb): Multiple select
   - Likelihood (fldhdlk8KsdWNqgff): Single select (High, Medium, Low)
   - Severity (fld195IZccUi69V5D): Single select (High, Medium, Low)
   - Detectability (fldfVsQ4b7qc8TAPP): Single select (High, Medium, Low)
   - Overall Risk Level (fldJtc0r2NsqF5UPV): Formula
   - ABBYY Response (fldPQRI4yOhY8bXRn): Single select (Accept, Change)
   - FH Response (fldYzOHPPF7q9wx9p): Single select (Accept, Unsure)
   - ABBYY personnel (fldCkZfIp6AzVjF9E): Single select
   - FH Personnel (fldkvQBS1MuEflOUv): Single select
   - Rootcause description (fld00wYhLLvTGZkPM): Lookup

   **Risk Changes Table:**
   - Original Risk Reference: Linked record to main table
   - FH Personnel: Single select/text
   - ABBYY Personnel: Single select/text
   - Risk Category: Text
   - Risk Type: Text
   - Risk Description: Long text
   - Impact: Multiple select
   - Root Causes: Long text
   - Components: Multiple select
   - Original Severity Level: Single select (High, Medium, Low)
   - New Severity Level: Single select (High, Medium, Low)
   - Original Likelihood Level: Single select (High, Medium, Low)
   - New Likelihood Level: Single select (High, Medium, Low)
   - Original Detectability Level: Single select (High, Medium, Low)
   - New Detectability Level: Single select (High, Medium, Low)
   - Original Overall Risk Level: Text
   - ABBYY's Response: Single select (Accept, Change)
   - FH Response: Single select (Accept, Unsure)
   - FH Change Response: Single select (Accept, Unsure)
   - Change Notes: Long Text

## Running the Application

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your web browser and go to the URL provided by Streamlit (typically http://localhost:8501)

3. The application will automatically connect to Airtable using the credentials from your .env file

4. Use the form to view and update risk data as needed

## Notes

- The application automatically reads the Airtable API key, Base ID, and Table ID from the .env file
- For the "Risk Changes" table to work correctly, it must be created in your Airtable base before using the application
- When ABBYY's response is "Accept", the risk assessment fields are disabled
- When ABBYY's response is "Change", the original and new values are saved to the "Risk Changes" table 