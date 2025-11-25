# Multiple API Keys Support

The batch enrichment script now supports multiple Gemini API keys with automatic fallback. If one key fails (quota exceeded, invalid, etc.), it automatically switches to the next key.

## Setup

### Option 1: Single API Key (Original Method)

In your `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

### Option 2: Multiple API Keys (Recommended)

In your `.env` file, add multiple keys separated by commas:
```
GOOGLE_API_KEYS=key1,key2,key3,key4
```

### Option 3: Both Methods (Combined)

You can use both:
```
GOOGLE_API_KEY=primary_key
GOOGLE_API_KEYS=backup_key1,backup_key2,backup_key3
```

The script will use all keys, prioritizing the single `GOOGLE_API_KEY` first.

## How It Works

1. **Automatic Key Rotation**: When an API key fails (quota exceeded, invalid, etc.), the script automatically switches to the next key
2. **Key Status Tracking**: The script tracks which keys are working and which have failed in `api_keys_status.json`
3. **Smart Selection**: 
   - Tries working keys first
   - Falls back to untested keys
   - Resets failed keys if all keys are exhausted
4. **Continuous Processing**: Processing continues seamlessly even when keys fail

## Error Detection

The script automatically detects these errors and switches keys:
- Quota exceeded (429 errors)
- Rate limit errors
- Invalid API key errors
- Authentication errors
- Billing/permission errors

## Files Created

- `api_keys_status.json` - Tracks which API keys are working/failed
  ```json
  {
    "failed_keys": ["key_ending_in_xxxx"],
    "working_keys": ["key_ending_in_yyyy"]
  }
  ```

## Example Workflow

1. Start processing with multiple keys configured
2. Key 1 works for 10 records, then hits quota
3. Script automatically switches to Key 2
4. Key 2 works for 15 records, then hits quota
5. Script automatically switches to Key 3
6. Processing continues without interruption

## Monitoring

Check which keys are working:
```bash
cat api_keys_status.json
```

## Manual Key Management

If you want to reset a failed key (e.g., after quota resets):
1. Open `api_keys_status.json`
2. Remove the key from `failed_keys` array
3. The script will try it again on next run

## Tips

- Add as many API keys as you have available
- Keys are tried in order (GOOGLE_API_KEY first, then GOOGLE_API_KEYS)
- Failed keys are automatically skipped
- If all keys fail, the script will reset and try again
- Processing is continuous - no manual intervention needed

## Troubleshooting

### All keys failed
If you see "All API keys exhausted":
- Check your `.env` file has valid keys
- Wait for quota to reset (usually hourly/daily)
- Add more API keys to `GOOGLE_API_KEYS`

### Key not being used
- Check `api_keys_status.json` - key might be marked as failed
- Remove it from `failed_keys` to retry
- Verify the key is correctly formatted in `.env` (no extra spaces)

