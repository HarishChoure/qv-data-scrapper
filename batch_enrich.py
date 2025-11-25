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
import time
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
API_KEYS_FILE = "api_keys_status.json"  # Track which API keys are working


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


def load_api_keys():
    """Load API keys from environment variables"""
    # Try GOOGLE_API_KEY first (single key)
    single_key = os.getenv('GOOGLE_API_KEY')
    
    # Try GOOGLE_API_KEYS (comma-separated list)
    keys_str = os.getenv('GOOGLE_API_KEYS', '')
    
    api_keys = []
    
    # Add single key if valid
    if single_key and single_key != 'your_api_key_here':
        api_keys.append(single_key)
    
    # Add multiple keys from GOOGLE_API_KEYS
    if keys_str:
        keys_list = [k.strip() for k in keys_str.split(',') if k.strip() and k.strip() != 'your_api_key_here']
        api_keys.extend(keys_list)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_keys = []
    for key in api_keys:
        if key not in seen:
            seen.add(key)
            unique_keys.append(key)
    
    if not unique_keys:
        raise ValueError(
            "No valid API keys found. Please set GOOGLE_API_KEY or GOOGLE_API_KEYS in .env file.\n"
            "For multiple keys, use: GOOGLE_API_KEYS=key1,key2,key3"
        )
    
    return unique_keys


def load_api_keys_status():
    """Load API keys status (which ones are working/failed)"""
    if Path(API_KEYS_FILE).exists():
        try:
            with open(API_KEYS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"failed_keys": [], "working_keys": []}
    return {"failed_keys": [], "working_keys": []}


def save_api_key_status(key, is_working=True):
    """Save API key status"""
    status = load_api_keys_status()
    
    if is_working:
        if key not in status["working_keys"]:
            status["working_keys"].append(key)
        if key in status["failed_keys"]:
            status["failed_keys"].remove(key)
    else:
        if key not in status["failed_keys"]:
            status["failed_keys"].append(key)
        if key in status["working_keys"]:
            status["working_keys"].remove(key)
    
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(status, f, indent=2)


def get_next_working_api_key():
    """Get the next working API key, skipping failed ones"""
    all_keys = load_api_keys()
    status = load_api_keys_status()
    failed_keys = set(status.get("failed_keys", []))
    
    # Try working keys first
    working_keys = [k for k in status.get("working_keys", []) if k in all_keys and k not in failed_keys]
    for key in working_keys:
        if key in all_keys:
            return key
    
    # Try keys that haven't been marked as failed
    untested_keys = [k for k in all_keys if k not in failed_keys]
    if untested_keys:
        return untested_keys[0]
    
    # If all keys are failed, reset and try again
    print("⚠️  All API keys have failed. Resetting and trying again...")
    status["failed_keys"] = []
    with open(API_KEYS_FILE, 'w') as f:
        json.dump(status, f, indent=2)
    
    return all_keys[0] if all_keys else None


def setup_gemini_client(api_key=None):
    """Setup Gemini API client with Google Grounding enabled"""
    if api_key is None:
        api_key = get_next_working_api_key()
    
    if not api_key:
        raise ValueError("No API key available")
    
    genai.configure(api_key=api_key)
    
    try:
        google_grounding_tool = Tool(google_search_retrieval=None)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[google_grounding_tool]
        )
        return model, api_key
    except Exception as e:
        print(f"⚠️  Could not enable grounding: {e}")
        model = genai.GenerativeModel(model_name='gemini-2.5-flash')
        return model, api_key


def enrich_record_with_gemini(model, record, api_key=None):
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
        error_str = str(e).lower()
        
        # Check if it's an API key/quota error
        is_quota_error = any(keyword in error_str for keyword in [
            'quota', '429', 'rate limit', 'billing', 'api key', 'invalid',
            'permission denied', 'authentication', 'unauthorized'
        ])
        
        if is_quota_error and api_key:
            print(f"⚠️  API key quota/error detected. Marking key as failed.")
            save_api_key_status(api_key, is_working=False)
            raise Exception(f"API_KEY_ERROR: {str(e)}")  # Re-raise to trigger key rotation
        
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
    
    # Setup Gemini with automatic key rotation
    max_retries = 5  # Maximum number of API keys to try
    retry_count = 0
    enriched_data = None
    
    while retry_count < max_retries:
        try:
            # Get next working API key and setup model
            api_key = get_next_working_api_key()
            if not api_key:
                raise ValueError("No API keys available")
            
            print(f"\n🔑 Using API key #{retry_count + 1} (ending in ...{api_key[-4:]})")
            model, current_api_key = setup_gemini_client(api_key)
            print("✅ Google Grounding enabled")
            
            # Enrich record
            print("\n🔍 Enriching with Gemini Grounding...")
            enriched_data = enrich_record_with_gemini(model, record, current_api_key)
            
            # If successful, mark key as working
            save_api_key_status(current_api_key, is_working=True)
            break  # Success, exit retry loop
            
        except Exception as e:
            error_str = str(e)
            if "API_KEY_ERROR" in error_str:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"⚠️  Switching to next API key... (Attempt {retry_count + 1}/{max_retries})")
                    continue
                else:
                    print(f"❌ All API keys exhausted. Please check your API keys or wait for quota reset.")
                    raise Exception("All API keys failed. Please check your .env file or wait for quota reset.")
            else:
                # Non-API-key error, don't retry
                raise
    
    if enriched_data is None:
        raise Exception("Failed to enrich record after all retries")
    
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


def get_total_records(excel_file_path, sheet_name=None):
    """Get total number of records in Excel file"""
    try:
        json_data = read_excel_to_json(excel_file_path, sheet_name)
        if sheet_name:
            records = json_data.get('data', [])
        else:
            first_sheet = list(json_data.keys())[0]
            records = json_data[first_sheet]
        return len(records)
    except:
        return 0


def main():
    """Main function - processes all records continuously"""
    
    excel_file = "New Microsoft Excel Worksheet.xlsx"
    
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    sheet_name = None
    if len(sys.argv) > 2:
        sheet_name = sys.argv[2]
    
    # Optional: delay between records (in seconds) to avoid rate limits
    delay_between_records = 2  # 2 seconds delay
    
    if len(sys.argv) > 3:
        try:
            delay_between_records = float(sys.argv[3])
        except:
            pass
    
    try:
        # Get total records
        total_records = get_total_records(excel_file, sheet_name)
        processed_count = len(load_processed_records())
        
        print("="*60)
        print("🚀 Continuous Batch Enrichment Started")
        print("="*60)
        print(f"📁 Excel File: {excel_file}")
        print(f"📊 Total Records: {total_records}")
        print(f"✅ Already Processed: {processed_count}")
        print(f"⏳ Remaining: {total_records - processed_count}")
        print(f"⏱️  Delay between records: {delay_between_records} seconds")
        print("="*60)
        print("\n💡 Press Ctrl+C to stop (progress will be saved)\n")
        
        record_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        # Continuous loop - process all records
        while True:
            try:
                # Process one record
                has_more = process_one_record(excel_file, sheet_name)
                
                if not has_more:
                    # All records processed
                    processed_count = len(load_processed_records())
                    print("\n" + "="*60)
                    print("🎉 ALL RECORDS PROCESSED!")
                    print("="*60)
                    print(f"✅ Total Processed: {processed_count}/{total_records}")
                    print(f"📁 Output File: {OUTPUT_CSV}")
                    print("="*60)
                    break
                
                record_count += 1
                consecutive_errors = 0  # Reset error counter on success
                
                # Show progress
                processed_count = len(load_processed_records())
                remaining = total_records - processed_count
                print(f"\n📈 Progress: {processed_count}/{total_records} records done | {remaining} remaining")
                
                # Delay before next record (to avoid rate limits)
                if delay_between_records > 0:
                    print(f"⏳ Waiting {delay_between_records} seconds before next record...\n")
                    time.sleep(delay_between_records)
                
            except KeyboardInterrupt:
                # User pressed Ctrl+C
                processed_count = len(load_processed_records())
                print("\n\n" + "="*60)
                print("⏸️  PROCESSING STOPPED BY USER")
                print("="*60)
                print(f"✅ Processed so far: {processed_count}/{total_records}")
                print(f"📁 Progress saved to: {TRACKING_FILE}")
                print(f"📁 Output saved to: {OUTPUT_CSV}")
                print(f"💡 Run again to continue from where you left off")
                print("="*60)
                break
                
            except Exception as e:
                consecutive_errors += 1
                error_msg = str(e)
                
                # Check if it's an API key error (will be handled by retry logic)
                if "API_KEY_ERROR" in error_msg or "All API keys failed" in error_msg:
                    print(f"\n❌ API Key Error: {error_msg}")
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"\n⚠️  Too many consecutive errors. Stopping.")
                        print(f"💡 Check your API keys in .env file")
                        break
                    print(f"⏳ Waiting 5 seconds before retry...")
                    time.sleep(5)
                    continue
                
                # Other errors
                print(f"\n⚠️  Error processing record: {error_msg}")
                if consecutive_errors >= max_consecutive_errors:
                    print(f"\n⚠️  Too many consecutive errors ({consecutive_errors}). Stopping.")
                    print(f"💡 Check the error messages above")
                    break
                
                print(f"⏳ Waiting 3 seconds before retry...")
                time.sleep(3)
                continue
    
    except Exception as e:
        print(f"\n❌ Fatal Error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

