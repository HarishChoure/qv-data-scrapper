# Excel Data Enrichment with Gemini Grounding

Automatically enrich Excel data with phone numbers, email addresses, and business type information using Google Gemini API with Google Grounding. Processes records continuously until all are completed.

## Features

- ✅ **Continuous Processing** - Runs automatically until all records are processed
- ✅ **Multiple API Keys Support** - Automatic fallback when one key fails
- ✅ **Google Grounding** - Uses real-time web search to find accurate information
- ✅ **Progress Tracking** - Tracks processed records, can resume anytime
- ✅ **CSV Output** - Saves all enriched data to CSV file
- ✅ **Source Links** - Includes verification URLs for all found data

## 1. Setup

### Prerequisites

- Python 3.7 or higher
- Google Gemini API key(s)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install pandas openpyxl google-generativeai python-dotenv
```

### Step 2: Configure API Keys

Create or edit the `.env` file in the project directory:

**Option 1: Single API Key**
```bash
GOOGLE_API_KEY=your_api_key_here
```

**Option 2: Multiple API Keys (Recommended)**
```bash
GOOGLE_API_KEYS=key1,key2,key3,key4
```

**Option 3: Both (Primary + Backups)**
```bash
GOOGLE_API_KEY=primary_key
GOOGLE_API_KEYS=backup_key1,backup_key2,backup_key3
```

**How to get API Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it in the `.env` file

### Step 3: Prepare Excel File

Place your Excel file in the project directory. The default file name is:
- `New Microsoft Excel Worksheet.xlsx`

Or use any Excel file with the following columns:
- `EnterpriseName` - Business/Company name
- `CommunicationAddress` - Business address
- `District` - District name
- `State` - State name
- `Activities` - Business activities (optional)

## 2. How to Run

### Basic Usage (Continuous Processing)

Run the script and it will process all records automatically:

```bash
python3 batch_enrich.py
```

The script will:
1. Read all records from Excel
2. Process them one by one
3. Enrich each record with phone, email, and business type
4. Save to `enriched_data.csv`
5. Continue until all records are processed

**To Stop:** Press `Ctrl+C` (progress will be saved)

**To Resume:** Run the script again (it continues from where it left off)

### Custom Excel File

```bash
python3 batch_enrich.py "path/to/your/file.xlsx"
```

### Specify Sheet Name

```bash
python3 batch_enrich.py "file.xlsx" "Sheet1"
```

### Custom Delay Between Records

Add delay (in seconds) to avoid rate limits:

```bash
python3 batch_enrich.py "file.xlsx" "Sheet1" 5
```

This adds a 5-second delay between each record.

## Output Files

### `enriched_data.csv`

Contains all enriched records with:
- **All original Excel columns** (LG_ST_Code, State, District, EnterpriseName, etc.)
- **phone_number** - Phone number found via Google Grounding
- **email** - Email address found via Google Grounding
- **business_type** - `manufacturer`, `wholeseller`, or `unknown`
- **source** - Always `gemini_grounding`
- **source_links** - JSON array of verification URLs

**Example:**
```csv
EnterpriseName,District,State,phone_number,email,business_type,source,source_links
K.K. Raj Cooler,INDORE,MADHYA PRADESH,+91-9826012345,kkrajcooler@gmail.com,manufacturer,gemini_grounding,"[""https://www.justdial.com/...""]"
```

### `processed_records.json`

Tracks which records have been processed:
```json
{
  "processed_indices": [0, 1, 2, 3, ...]
}
```

### `api_keys_status.json`

Tracks which API keys are working/failed:
```json
{
  "failed_keys": [],
  "working_keys": ["key1", "key2"]
}
```

## Progress Monitoring

### Check Current Progress

```bash
# View processed records
cat processed_records.json

# Count total records in CSV (subtract 1 for header)
wc -l enriched_data.csv

# View last processed record
tail -1 enriched_data.csv
```

### Manual Progress Control

**To reprocess a specific record:**
1. Open `processed_records.json`
2. Remove the record index from the array
3. Run the script again

**Example - Reprocess record #16:**
```json
{
  "processed_indices": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, ...]
}
```
(Remove `15` from the array to reprocess record #16)

**To reset all progress:**
```json
{
  "processed_indices": []
}
```

## Configuration

### File Locations

You can modify these in `batch_enrich.py` (lines 23-25):

```python
TRACKING_FILE = "processed_records.json"  # Progress tracking
OUTPUT_CSV = "enriched_data.csv"          # Output file
API_KEYS_FILE = "api_keys_status.json"    # API keys status
```

### Delay Between Records

Default: 2 seconds (line 440 in `batch_enrich.py`)

```python
delay_between_records = 2  # Change this value
```

## Troubleshooting

### Error: "GOOGLE_API_KEY not found"

- Make sure `.env` file exists in the project directory
- Check that `GOOGLE_API_KEY` or `GOOGLE_API_KEYS` is set in `.env`
- Verify there are no extra spaces around the `=` sign

### Error: "Quota exceeded" or "429 error"

- The script automatically switches to the next API key
- Add more API keys to `GOOGLE_API_KEYS` in `.env`
- Wait for quota to reset (usually hourly/daily)

### Error: "All API keys exhausted"

- Check all API keys are valid in `.env`
- Wait for quota to reset
- Add more API keys

### Script stops unexpectedly

- Check `api_keys_status.json` to see which keys failed
- Reset failed keys by clearing `failed_keys` array
- Check error messages in the console

### Want to start fresh

```bash
# Delete tracking files (keeps CSV data)
rm processed_records.json
rm api_keys_status.json

# Or delete everything and start over
rm processed_records.json
rm api_keys_status.json
rm enriched_data.csv
```

## Example Workflow

1. **Setup:**
   ```bash
   pip install -r requirements.txt
   # Add API keys to .env file
   ```

2. **Run:**
   ```bash
   python3 batch_enrich.py
   ```

3. **Monitor:**
   - Watch console for progress updates
   - Check `enriched_data.csv` for results
   - Press `Ctrl+C` to stop anytime

4. **Resume:**
   ```bash
   python3 batch_enrich.py
   # Continues from where it left off
   ```

## Project Structure

```
qv-data-scrapper/
├── batch_enrich.py          # Main script (continuous processing)
├── read_excel_to_json.py    # Excel reading utility
├── requirements.txt         # Python dependencies
├── .env                     # API keys configuration (create this)
├── .gitignore              # Git ignore rules
├── enriched_data.csv        # Output file (auto-created)
├── processed_records.json   # Progress tracking (auto-created)
└── api_keys_status.json     # API keys status (auto-created)
```

## Support

For issues or questions:
- Check the error messages in console
- Verify API keys are correct
- Check `.env` file format
- Review `api_keys_status.json` for key issues

