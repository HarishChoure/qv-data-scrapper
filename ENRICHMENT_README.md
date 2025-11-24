# Gemini Grounding Data Enrichment

This script enriches Excel data using Google Gemini API with Google Grounding (Google Search) to find phone numbers, email addresses, and determine business type (manufacturer/wholeseller).

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit the `.env` file and add your Google API key:

```bash
GOOGLE_API_KEY=your_actual_api_key_here
```

**How to get Google API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key and paste it in the `.env` file

## Usage

### Basic Usage (Read first record and enrich)

```bash
python3 enrich_with_gemini.py
```

### Custom Excel File

```bash
python3 enrich_with_gemini.py path/to/your/file.xlsx
```

### Specify Sheet Name

```bash
python3 enrich_with_gemini.py "New Microsoft Excel Worksheet.xlsx" "Sheet1"
```

### Save to JSON File

```bash
python3 enrich_with_gemini.py "New Microsoft Excel Worksheet.xlsx" None output.json
```

## Output Format

The script returns enriched JSON with the following structure:

```json
{
  "original_data": {
    "LG_ST_Code": 23,
    "State": "MADHYA PRADESH",
    "EnterpriseName": "Example Company",
    "CommunicationAddress": "...",
    "District": "INDORE",
    "Activities": "...",
    ...
  },
  "enriched_data": {
    "phone_number": "+91-1234567890",
    "email": "contact@example.com",
    "business_type": "manufacturer",
    "source": "gemini_grounding"
  }
}
```

## Features

- ✅ Reads first record from Excel automatically
- ✅ Uses Google Grounding (Google Search) via Gemini API
- ✅ Searches using multiple query strategies:
  - EnterpriseName + CommunicationAddress
  - EnterpriseName + District + State
- ✅ Extracts phone number and email
- ✅ Determines business type (manufacturer/wholeseller) based on:
  - Activities field from Excel
  - Web search results
- ✅ Handles errors gracefully
- ✅ Outputs structured JSON

## Business Type Detection

The script determines if a business is a **manufacturer** or **wholeseller** by:
1. Analyzing the `Activities` field from Excel
2. Searching the web for business information
3. Classifying based on whether they produce/manufacture goods (manufacturer) or primarily distribute/sell in bulk (wholeseller)

## Troubleshooting

### Error: "GOOGLE_API_KEY not found"
- Make sure you've added your API key to the `.env` file
- Check that the `.env` file is in the same directory as the script

### Error: "No records found in Excel file"
- Verify your Excel file has data
- Check the sheet name if using a specific sheet

### API Errors
- Verify your API key is valid
- Check your API quota/limits
- Ensure you have internet connection for Google Grounding

## Example Output

```
============================================================
Gemini Grounding Data Enrichment
============================================================
Reading first record from: New Microsoft Excel Worksheet.xlsx

📋 First Record Found:
   Enterprise: Example Company
   District: INDORE
   State: MADHYA PRADESH

🔍 Searching with Gemini Grounding...
   Enterprise: Example Company
   Location: INDORE, MADHYA PRADESH

============================================================
Enriched Data:
============================================================
{
  "original_data": { ... },
  "enriched_data": {
    "phone_number": "+91-1234567890",
    "email": "info@example.com",
    "business_type": "manufacturer",
    "source": "gemini_grounding"
  }
}
```

