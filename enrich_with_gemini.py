#!/usr/bin/env python3
"""
Enrich Excel data with Gemini API using Google Grounding
Reads first record from Excel and enriches it with phone, email, and business type
Uses Google Grounding feature (not Google Search API directly)
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import Tool
from google.generativeai import protos
from read_excel_to_json import read_excel_to_json

# Load environment variables
load_dotenv()


def get_first_record(excel_file_path, sheet_name=None):
    """
    Read Excel file and return the first record
    
    Args:
        excel_file_path (str): Path to the Excel file
        sheet_name (str, optional): Specific sheet name to read
    
    Returns:
        dict: First record from Excel
    """
    try:
        json_data = read_excel_to_json(excel_file_path, sheet_name)
        
        # Get first sheet and first record
        if sheet_name:
            # Single sheet format
            records = json_data.get('data', [])
        else:
            # Multiple sheets format - get first sheet
            first_sheet = list(json_data.keys())[0]
            records = json_data[first_sheet]
        
        if not records:
            raise ValueError("No records found in Excel file")
        
        return records[0]
    
    except Exception as e:
        print(f"Error reading first record: {str(e)}", file=sys.stderr)
        raise


def setup_gemini_client():
    """
    Setup Gemini API client with Google Grounding enabled
    Google Grounding uses Google Search as the data source for real-time information
    
    Returns:
        genai.GenerativeModel: Configured Gemini model with Google Grounding
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError(
            "GOOGLE_API_KEY not found in .env file. "
            "Please add your API key to the .env file."
        )
    
    # Configure the API
    genai.configure(api_key=api_key)
    
    # Create model with Google Grounding enabled
    # For gemini-2.5-flash, Google Grounding may need to be enabled differently
    try:
        # Try creating Tool with empty GoogleSearchRetrieval (no config)
        # Some models may require this to be None or empty
        google_grounding_tool = Tool(
            google_search_retrieval=None
        )
        
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            tools=[google_grounding_tool]
        )
        print("✅ Google Grounding enabled (using Google Search as data source)")
    except Exception as e1:
        try:
            # Try with empty dict for google_search_retrieval
            google_grounding_tool = Tool(
                google_search_retrieval={}
            )
            model = genai.GenerativeModel(
                model_name='gemini-2.5-flash',
                tools=[google_grounding_tool]
            )
            print("✅ Google Grounding enabled (using Google Search as data source)")
        except Exception as e2:
            # Last fallback: try without tools - some models have grounding enabled by default
            print(f"⚠️  Could not enable grounding with tools: {e1}, {e2}")
            print("   Trying model without explicit tools (grounding may be enabled by default)")
            model = genai.GenerativeModel(model_name='gemini-2.5-flash')
    
    return model


def enrich_with_gemini(model, record):
    """
    Use Gemini with Google Grounding to enrich record with phone, email, and business type
    Google Grounding will search the web for real-time information
    
    Args:
        model: Gemini model instance with Google Grounding enabled
        record (dict): Excel record to enrich
    
    Returns:
        dict: Enriched data with phone, email, and business_type
    """
    enterprise_name = record.get('EnterpriseName', '')
    communication_address = record.get('CommunicationAddress', '')
    district = record.get('District', '')
    state = record.get('State', '')
    activities = record.get('Activities', '')
    
    # Build comprehensive prompt for Google Grounding
    prompt = f"""You are a business data researcher with access to Google Grounding (real-time web information). I need you to use Google Grounding to find contact information and business type for the following enterprise:

Enterprise Name: {enterprise_name}
Address: {communication_address}
District: {district}
State: {state}
Activities: {activities}

IMPORTANT: Use Google Grounding to find real-time information about this business. The grounding will search for:
1. Phone number and email of "{enterprise_name}" located at "{communication_address}"
2. Phone number and email of "{enterprise_name}" in "{district}, {state}"
3. Whether "{enterprise_name}" is a manufacturer or wholeseller based on their activities: {activities}

Please use Google Grounding to search the web and provide the following information in JSON format:
1. Phone number (if found, format as string)
2. Email address (if found)
3. Business type: Determine if this is a "manufacturer" or "wholeseller" based on:
   - The Activities field provided above
   - Web search results about the business
   - Use "manufacturer" if they produce/manufacture goods
   - Use "wholeseller" if they primarily distribute/sell goods in bulk
   - Use "unknown" if you cannot determine

Search using both:
- Enterprise name + address: "{enterprise_name} {communication_address}"
- Enterprise name + location: "{enterprise_name} {district} {state}"

Return ONLY a valid JSON object with this exact structure:
{{
    "phone_number": "phone or null",
    "email": "email or null",
    "business_type": "manufacturer" or "wholeseller" or "unknown",
    "source_urls": ["list of URLs where you found the information"]
}}

IMPORTANT: Include the source_urls array with all the website URLs where you found the phone number, email, or business information. This is critical for verification.

Do not include any text before or after the JSON. Only return the JSON object."""

    try:
        print("🔍 Using Google Grounding to search for information...")
        print(f"   Enterprise: {enterprise_name}")
        print(f"   Location: {district}, {state}\n")
        
        # Generate response with Google Grounding
        # The model already has Google Grounding enabled via tools
        generation_config = genai.types.GenerationConfig(
            temperature=0.7,
            top_p=0.8,
            top_k=40,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        # Extract text from response
        response_text = response.text.strip()
        
        # Extract grounding source links from multiple possible locations
        source_links = []
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Method 1: Check citation_metadata (often more reliable)
                if hasattr(candidate, 'citation_metadata') and candidate.citation_metadata:
                    citation_metadata = candidate.citation_metadata
                    if hasattr(citation_metadata, 'citation_sources'):
                        sources = citation_metadata.citation_sources
                        for source in sources:
                            try:
                                # Try different ways to get URI
                                if hasattr(source, 'uri'):
                                    uri = source.uri
                                    if uri and str(uri) not in source_links:
                                        source_links.append(str(uri))
                                elif hasattr(source, 'start_index'):
                                    # Sometimes URI is in a different format
                                    pass
                                # Try accessing as dict
                                if hasattr(source, '__dict__'):
                                    source_dict = source.__dict__
                                    for key in ['uri', 'url', 'link', 'source_uri']:
                                        if key in source_dict:
                                            value = source_dict[key]
                                            if value and str(value) not in source_links:
                                                source_links.append(str(value))
                            except Exception as e:
                                pass
                
                # Method 2: Check grounding_metadata.grounding_chunks
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding_metadata = candidate.grounding_metadata
                    
                    if debug_mode:
                        print(f"DEBUG: Grounding metadata type: {type(grounding_metadata)}")
                        print(f"DEBUG: Grounding metadata dir: {[x for x in dir(grounding_metadata) if not x.startswith('_')]}")
                    
                    if hasattr(grounding_metadata, 'grounding_chunks'):
                        chunks = grounding_metadata.grounding_chunks
                        if debug_mode:
                            print(f"DEBUG: Found {len(chunks)} grounding chunks")
                        
                        for i, chunk in enumerate(chunks):
                            try:
                                if debug_mode:
                                    print(f"DEBUG: Chunk {i} type: {type(chunk)}")
                                    print(f"DEBUG: Chunk {i} dir: {[x for x in dir(chunk) if not x.startswith('_')]}")
                                
                                # Try accessing web.uri
                                if hasattr(chunk, 'web'):
                                    web = chunk.web
                                    if debug_mode:
                                        print(f"DEBUG: Web type: {type(web)}")
                                        print(f"DEBUG: Web dir: {[x for x in dir(web) if not x.startswith('_')]}")
                                    
                                    if hasattr(web, 'uri'):
                                        uri = web.uri
                                        if uri and str(uri) not in source_links:
                                            source_links.append(str(uri))
                                            if debug_mode:
                                                print(f"DEBUG: Found URI from web.uri: {uri}")
                                    
                                    # Also try other web attributes
                                    for attr_name in ['url', 'link', 'source']:
                                        if hasattr(web, attr_name):
                                            attr_value = getattr(web, attr_name)
                                            if attr_value and str(attr_value) not in source_links:
                                                source_links.append(str(attr_value))
                                                if debug_mode:
                                                    print(f"DEBUG: Found from web.{attr_name}: {attr_value}")
                                
                                # Try direct chunk attributes
                                for attr_name in ['uri', 'url', 'link', 'source', 'source_uri']:
                                    if hasattr(chunk, attr_name):
                                        attr_value = getattr(chunk, attr_name)
                                        if attr_value and str(attr_value) not in source_links:
                                            source_links.append(str(attr_value))
                                            if debug_mode:
                                                print(f"DEBUG: Found from chunk.{attr_name}: {attr_value}")
                                
                                # Try accessing via __dict__
                                if hasattr(chunk, '__dict__'):
                                    chunk_dict = chunk.__dict__
                                    for key in ['uri', 'url', 'link', 'source', 'web']:
                                        if key in chunk_dict:
                                            value = chunk_dict[key]
                                            if isinstance(value, dict) and 'uri' in value:
                                                uri = value['uri']
                                                if uri and str(uri) not in source_links:
                                                    source_links.append(str(uri))
                                            elif value and str(value) not in source_links and ('http' in str(value) or 'www' in str(value)):
                                                source_links.append(str(value))
                            except Exception as chunk_error:
                                if debug_mode:
                                    print(f"DEBUG: Error processing chunk {i}: {chunk_error}")
                                pass
                    
                    # Check for search_entry_point
                    if hasattr(grounding_metadata, 'search_entry_point'):
                        try:
                            entry_point = grounding_metadata.search_entry_point
                            for attr_name in ['rendered_content', 'uri', 'url', 'link']:
                                if hasattr(entry_point, attr_name):
                                    content = getattr(entry_point, attr_name)
                                    if content and str(content) not in source_links:
                                        source_links.append(str(content))
                        except:
                            pass
                
                # Method 3: Check grounding_attributions (often contains source info)
                if hasattr(candidate, 'grounding_attributions') and candidate.grounding_attributions:
                    attributions = candidate.grounding_attributions
                    for attr in attributions:
                        try:
                            # Check all possible attributes
                            for attr_name in ['source_id', 'uri', 'url', 'link', 'source_uri', 'web_uri']:
                                if hasattr(attr, attr_name):
                                    value = getattr(attr, attr_name)
                                    if value and str(value) not in source_links:
                                        value_str = str(value)
                                        if 'http' in value_str or 'www.' in value_str:
                                            source_links.append(value_str)
                            
                            # Also check if it has a web attribute
                            if hasattr(attr, 'web'):
                                web = attr.web
                                for web_attr in ['uri', 'url', 'link']:
                                    if hasattr(web, web_attr):
                                        value = getattr(web, web_attr)
                                        if value and str(value) not in source_links:
                                            source_links.append(str(value))
                        except Exception as e:
                            pass
                
                # Method 4: Extract URLs from response text and metadata using regex
                try:
                    import re
                    # Check response text for URLs
                    if hasattr(response, 'text') and response.text:
                        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', response.text)
                        for url in urls:
                            if url not in source_links:
                                source_links.append(url)
                    
                    # Also check the string representation of the response object
                    response_str = str(response)
                    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', response_str)
                    for url in urls:
                        if url not in source_links:
                            source_links.append(url)
                except:
                    pass
                
                # Method 4: Try to access response.prompt_feedback or other response-level metadata
                if hasattr(response, 'prompt_feedback'):
                    try:
                        # Some responses have sources at response level
                        pass
                    except:
                        pass
                        
        except Exception as e:
            # If extraction fails, print error for debugging
            print(f"⚠️  Error extracting source links: {e}")
            import traceback
            traceback.print_exc()
        
        # Print grounding sources if available
        if source_links:
            print("\n📚 Grounding Sources:")
            for link in source_links:
                print(f"   - {link}")
            print()
        
        # Try to extract JSON from response
        # Sometimes Gemini wraps JSON in markdown code blocks
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Parse JSON
        try:
            enriched_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON object from text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                enriched_data = json.loads(response_text[start_idx:end_idx])
            else:
                raise ValueError("Could not parse JSON from Gemini response")
        
        # Extract source URLs from the response if provided by Gemini
        response_source_urls = enriched_data.get("source_urls", [])
        if isinstance(response_source_urls, list):
            # Clean URLs (remove backslashes and whitespace)
            cleaned_urls = []
            for url in response_source_urls:
                if url:
                    # Remove backslashes, newlines, and strip whitespace
                    cleaned = str(url).replace('\\', '').replace('\n', '').replace('\r', '').strip()
                    # Remove trailing backslashes that might still be there
                    cleaned = cleaned.rstrip('\\').strip()
                    if cleaned and (cleaned.startswith('http://') or cleaned.startswith('https://')):
                        cleaned_urls.append(cleaned)
            # Merge with extracted source links and remove duplicates
            all_source_links = list(set(source_links + cleaned_urls))
        else:
            all_source_links = source_links if source_links else []
        
        # Final cleanup: remove any empty strings, backslashes, and ensure all are valid URLs
        final_links = []
        for url in all_source_links:
            if url:
                # Clean the URL
                cleaned = str(url).replace('\\', '').replace('\n', '').replace('\r', '').strip().rstrip('\\')
                if cleaned and (cleaned.startswith('http://') or cleaned.startswith('https://')):
                    if cleaned not in final_links:
                        final_links.append(cleaned)
        
        all_source_links = final_links
        
        # Validate and set defaults
        result = {
            "phone_number": enriched_data.get("phone_number") or None,
            "email": enriched_data.get("email") or None,
            "business_type": enriched_data.get("business_type", "unknown").lower(),
            "source": "gemini_grounding",
            "source_links": all_source_links
        }
        
        # Validate business_type
        if result["business_type"] not in ["manufacturer", "wholeseller", "unknown"]:
            result["business_type"] = "unknown"
        
        return result
    
    except Exception as e:
        print(f"⚠️  Error during Gemini enrichment: {str(e)}", file=sys.stderr)
        # Return default structure on error
        return {
            "phone_number": None,
            "email": None,
            "business_type": "unknown",
            "source": "gemini_grounding",
            "source_links": [],
            "error": str(e)
        }


def create_enriched_json(original_record, enriched_data):
    """
    Create enriched JSON structure with original data + enriched fields
    
    Args:
        original_record (dict): Original Excel record
        enriched_data (dict): Enriched data from Gemini
    
    Returns:
        dict: Combined enriched JSON structure
    """
    return {
        "original_data": original_record,
        "enriched_data": enriched_data
    }


def main():
    """Main function to run the enrichment script"""
    # Default Excel file path
    excel_file = "New Microsoft Excel Worksheet.xlsx"
    
    # Check if custom file path is provided as command line argument
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    # Optional: specify sheet name as second argument
    sheet_name = None
    if len(sys.argv) > 2:
        sheet_name = sys.argv[2]
    
    # Optional: specify output file as third argument
    output_file = None
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    
    try:
        print("="*60)
        print("Gemini Grounding Data Enrichment")
        print("="*60)
        print(f"Reading first record from: {excel_file}\n")
        
        # Read first record from Excel
        first_record = get_first_record(excel_file, sheet_name)
        
        print("📋 First Record Found:")
        print(f"   Enterprise: {first_record.get('EnterpriseName', 'N/A')}")
        print(f"   District: {first_record.get('District', 'N/A')}")
        print(f"   State: {first_record.get('State', 'N/A')}\n")
        
        # Setup Gemini client
        model = setup_gemini_client()
        
        # Enrich with Gemini
        enriched_data = enrich_with_gemini(model, first_record)
        
        # Create enriched JSON structure
        enriched_json = create_enriched_json(first_record, enriched_data)
        
        # Print results
        print("\n" + "="*60)
        print("Enriched Data:")
        print("="*60)
        print(json.dumps(enriched_json, indent=2, ensure_ascii=False))
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_json, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Enriched data saved to: {output_file}")
        
        return enriched_json
    
    except ValueError as e:
        print(f"❌ Configuration Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to process: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

