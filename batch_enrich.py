#!/usr/bin/env python3
"""
Batch Enrichment Script
Processes Excel records one by one, enriches with Gemini, and saves to CSV
Tracks processed records to avoid duplicates
"""

import os
import json
import sys
import csv
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import Tool
from read_excel_to_json import read_excel_to_json

# Load environment variables
load_dotenv()

# Configuration
TRACKING_FILE = "processed_records.json"
OUTPUT_CSV = "enriched_data.csv"


def load_processed_records():
    """Load list of already processed record indices"""
    if Path(TRACKING_FILE).exists():
        try:
            with open(TRACKING_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('processed_indices', []))
        except:
            return set()
    return set()


def save_processed_record(index):
    """Save processed record index to tracking file"""
    processed = load_processed_records()
    processed.add(index)
    
    with open(TRACKING_FILE, 'w') as f:
        json.dump({'processed_indices': list(processed)}, f, indent=2)


def setup_gemini_client():
    """Setup Gemini API client with Google Grounding enabled"""
    api_key = os.getenv('GOOGLE_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError(
            "GOOGLE_API_KEY not found in .env file. "
            "Please add your API key to the .env file."
        )
    
    genai.configure(api_key=api_key)
    
    try:
        google_grounding_tool = Tool(google_search_retrieval=None)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[google_grounding_tool]
        )
        print("✅ Google Grounding enabled")
    except Exception as e:
        print(f"⚠️  Could not enable grounding: {e}")
        model = genai.GenerativeModel(model_name='gemini-2.5-flash')
    
    return model


def enrich_record_with_gemini(model, record):
    """Enrich a single record with Gemini"""
    enterprise_name = record.get('EnterpriseName', '')
    communication_address = record.get('CommunicationAddress', '')
    district = record.get('District', '')
    state = record.get('State', '')
    activities = record.get('Activities', '')
    
    prompt = f"""You are a business data researcher with access to Google Grounding. I need you to use Google Grounding to find contact information and business type for the following enterprise:

Enterprise Name: {enterprise_name}
Address: {communication_address}
District: {district}
State: {state}
Activities: {activities}

IMPORTANT: Use Google Grounding to find real-time information about this business. The grounding will search for:
1. Phone number and email of "{enterprise_name}" located at "{communication_address}"
2. Phone number and email of "{enterprise_name}" in "{district}, {state}"
3. Whether "{enterprise_name}" is a manufacturer or wholeseller based on their activities: {activities}

Return ONLY a valid JSON object with this exact structure:
{{
    "phone_number": "phone or null",
    "email": "email or null",
    "business_type": "manufacturer" or "wholeseller" or "unknown",
    "source_urls": ["list of URLs where you found the information"]
}}

IMPORTANT: Include the source_urls array with all the website URLs where you found the phone number, email, or business information.

Do not include any text before or after the JSON. Only return the JSON object."""

    try:
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        response_text = response.text.strip()
        
        # Extract JSON from response
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        try:
            enriched_data = json.loads(response_text)
        except json.JSONDecodeError:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                enriched_data = json.loads(response_text[start_idx:end_idx])
            else:
                raise ValueError("Could not parse JSON from Gemini response")
        
        # Clean source URLs
        source_urls = enriched_data.get("source_urls", [])
        cleaned_urls = []
        for url in source_urls:
            if url:
                cleaned = str(url).replace('\\', '').replace('\n', '').replace('\r', '').strip().rstrip('\\')
                if cleaned and (cleaned.startswith('http://') or cleaned.startswith('https://')):
                    cleaned_urls.append(cleaned)
        
        result = {
            "phone_number": enriched_data.get("phone_number") or None,
            "email": enriched_data.get("email") or None,
            "business_type": enriched_data.get("business_type", "unknown").lower(),
            "source": "gemini_grounding",
            "source_links": list(set(cleaned_urls))
        }
        
        if result["business_type"] not in ["manufacturer", "wholeseller", "unknown"]:
            result["business_type"] = "unknown"
        
        return result
    
    except Exception as e:
        print(f"⚠️  Error during enrichment: {str(e)}")
        return {
            "phone_number": None,
            "email": None,
            "business_type": "unknown",
            "source": "gemini_grounding",
            "source_links": [],
            "error": str(e)
        }


def get_csv_headers(original_record, enriched_data):
    """Get all headers for CSV file"""
    headers = list(original_record.keys())
    headers.extend(['phone_number', 'email', 'business_type', 'source', 'source_links'])
    return headers


def append_to_csv(original_record, enriched_data):
    """Append enriched record to CSV file"""
    file_exists = Path(OUTPUT_CSV).exists()
    
    # Prepare row data
    row_data = {}
    
    # Add all original fields
    for key, value in original_record.items():
        row_data[key] = value
    
    # Add enriched fields
    row_data['phone_number'] = enriched_data.get('phone_number')
    row_data['email'] = enriched_data.get('email')
    row_data['business_type'] = enriched_data.get('business_type')
    row_data['source'] = enriched_data.get('source')
    # Convert source_links list to string for CSV
    row_data['source_links'] = json.dumps(enriched_data.get('source_links', []))
    
    # Get headers
    headers = get_csv_headers(original_record, enriched_data)
    
    # Write to CSV
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(row_data)


def get_next_unprocessed_record(excel_file_path, sheet_name=None):
    """Get the next unprocessed record from Excel"""
    processed_indices = load_processed_records()
    
    # Read all records
    json_data = read_excel_to_json(excel_file_path, sheet_name)
    
    if sheet_name:
        records = json_data.get('data', [])
    else:
        first_sheet = list(json_data.keys())[0]
        records = json_data[first_sheet]
    
    # Find first unprocessed record
    for index, record in enumerate(records):
        if index not in processed_indices:
            return index, record
    
    return None, None


def process_one_record(excel_file_path, sheet_name=None):
    """Process one record from Excel"""
    print("="*60)
    print("Batch Enrichment - Processing One Record")
    print("="*60)
    
    # Get next unprocessed record
    index, record = get_next_unprocessed_record(excel_file_path, sheet_name)
    
    if record is None:
        print("✅ All records have been processed!")
        return False
    
    print(f"\n📋 Processing record #{index + 1}")
    print(f"   Enterprise: {record.get('EnterpriseName', 'N/A')}")
    print(f"   District: {record.get('District', 'N/A')}")
    print(f"   State: {record.get('State', 'N/A')}")
    
    # Setup Gemini
    model = setup_gemini_client()
    
    # Enrich record
    print("\n🔍 Enriching with Gemini Grounding...")
    enriched_data = enrich_record_with_gemini(model, record)
    
    # Display results
    print(f"\n✅ Enrichment Complete:")
    print(f"   Phone: {enriched_data.get('phone_number', 'Not found')}")
    print(f"   Email: {enriched_data.get('email', 'Not found')}")
    print(f"   Business Type: {enriched_data.get('business_type', 'unknown')}")
    print(f"   Sources: {len(enriched_data.get('source_links', []))} URLs found")
    
    # Save to CSV
    append_to_csv(record, enriched_data)
    print(f"\n💾 Saved to {OUTPUT_CSV}")
    
    # Mark as processed
    save_processed_record(index)
    print(f"✅ Record #{index + 1} marked as processed")
    
    return True


def main():
    """Main function"""
    excel_file = "New Microsoft Excel Worksheet.xlsx"
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    sheet_name = None
    if len(sys.argv) > 2:
        sheet_name = sys.argv[2]
    
    try:
        # Process one record
        has_more = process_one_record(excel_file, sheet_name)
        
        if has_more:
            print(f"\n📊 Progress: Check {TRACKING_FILE} for processed records")
            print(f"📁 Output: {OUTPUT_CSV}")
            print(f"\n💡 Run again to process the next record")
        else:
            print(f"\n🎉 All done! Check {OUTPUT_CSV} for all enriched data")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

