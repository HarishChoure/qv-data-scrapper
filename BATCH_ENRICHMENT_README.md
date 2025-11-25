# Batch Enrichment Script

This script processes Excel records one by one, enriches them with Gemini Grounding, and saves the results to a CSV file. It tracks which records have been processed to avoid duplicates.

## Features

- ✅ Processes one record at a time
- ✅ **Multiple API Keys Support** - Automatic fallback when one key fails
- ✅ Tracks processed records (no duplicates)
- ✅ Saves to CSV file (creates if doesn't exist)
- ✅ Includes all original fields + enriched fields
- ✅ Can resume from where it left off
- ✅ Uses Google Grounding to find phone, email, and business type
- ✅ Continuous processing - automatically switches API keys on quota errors

## Usage

### Basic Usage

Process one record at a time:

```bash
python3 batch_enrich.py
```

Each time you run it, it will:
1. Find the next unprocessed record
2. Enrich it with Gemini Grounding
3. Save to `enriched_data.csv`
4. Mark it as processed

### Custom Excel File

```bash
python3 batch_enrich.py path/to/your/file.xlsx
```

### Specify Sheet Name

```bash
python3 batch_enrich.py "New Microsoft Excel Worksheet.xlsx" "Sheet1"
```

## Output Files

### `enriched_data.csv`
Contains all enriched records with:
- All original Excel columns
- `phone_number` - Phone number found via Google Grounding
- `email` - Email address found via Google Grounding
- `business_type` - manufacturer/wholeseller/unknown
- `source` - Always "gemini_grounding"
- `source_links` - JSON array of source URLs

### `processed_records.json`
Tracks which record indices have been processed:
```json
{
  "processed_indices": [0, 1, 2, ...]
}
```

## Workflow

1. **First Run**: Processes record #1, creates `enriched_data.csv` and `processed_records.json`
2. **Subsequent Runs**: Processes the next unprocessed record
3. **Continue**: Keep running until all records are processed
4. **Resume**: If you stop and restart, it will continue from where it left off

## Example Output

```csv
LG_ST_Code,State,District,EnterpriseName,phone_number,email,business_type,source,source_links
23,MADHYA PRADESH,INDORE,K.K. Raj Cooler,+91-9826012345,kkrajcooler@gmail.com,manufacturer,gemini_grounding,"[""https://www.justdial.com/...""]"
```

## Progress Tracking

Check how many records have been processed:

```bash
cat processed_records.json
```

Check how many records are in the CSV:

```bash
wc -l enriched_data.csv
```

(Note: The first line is the header, so subtract 1 for actual record count)

## Tips

- Run the script multiple times to process all records
- The script automatically skips already processed records
- If an error occurs, the record won't be marked as processed, so you can retry
- You can manually edit `processed_records.json` to reprocess specific records (remove the index from the array)

## Troubleshooting

### All records processed
If you see "✅ All records have been processed!", you're done!

### Want to reprocess a record
1. Open `processed_records.json`
2. Remove the index number from the `processed_indices` array
3. Run the script again

### CSV file issues
- The CSV is created automatically
- If you delete it, it will be recreated with headers
- Already processed records will be skipped (won't duplicate)

## Multiple API Keys Setup

The script supports multiple API keys with automatic fallback. See [MULTIPLE_API_KEYS.md](MULTIPLE_API_KEYS.md) for detailed instructions.

**Quick Setup:**
1. Add multiple keys to `.env` file:
   ```
   GOOGLE_API_KEYS=key1,key2,key3,key4
   ```
2. The script will automatically:
   - Use the first working key
   - Switch to next key if quota exceeded
   - Continue processing without interruption

## Configuration

You can modify these constants in the script:
- `TRACKING_FILE = "processed_records.json"` - File to track processed records
- `OUTPUT_CSV = "enriched_data.csv"` - Output CSV file name
- `API_KEYS_FILE = "api_keys_status.json"` - File to track API key status

