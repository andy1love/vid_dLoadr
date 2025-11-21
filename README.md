# Video Download Automation System

Automated workflow for downloading videos from YouTube and Instagram, synced with iCloud Notes.

## Overview

This system automates the complete workflow:
1. **Sync URLs** from iCloud Notes to local files
2. **Download videos** using yt-dlp
3. **Verify downloads** and **update iCloud Notes** automatically

## System Architecture

```
iCloud Notes (iPhone) 
    ↓
sync_notes_to_urls.py → workarea/urls/ (timestamped files)
    ↓
trigger_download.py
    ↓
download_video.py → Downloads videos + creates CSV logs
    ↓
clean_up.py → Verifies downloads + updates Notes
```

## Files Structure

```
py/
├── sync_notes_to_urls.py   # Syncs URLs from iCloud Notes
├── download_video.py        # Downloads videos and creates logs
├── trigger_download.py      # Main automation trigger
├── clean_up.py             # Verifies downloads and updates Notes
└── workarea/
    ├── urls/               # URL files (timestamped)
    │   ├── urls.txt
    │   └── YYYYMMDD_HHMM_<count>_urls.txt
    └── logs/               # CSV download logs
        └── YYYYMMDD_HHMM_<count>_urls_log.csv
```

## Scripts

### `sync_notes_to_urls.py`
Syncs URLs from an iCloud Note to local files.

**Features:**
- Reads URLs from iCloud Note (handles HTML formatting)
- Creates timestamped URL files: `YYYYMMDD_HHMM_<count>_urls.txt`
- Skips duplicates
- Appends to main `urls.txt` file

**Usage:**
```bash
python3 sync_notes_to_urls.py
```

**Configuration:**
- Note title: `Download_URLs` (configurable in script)
- Output: `workarea/urls/`

### `download_video.py`
Downloads videos from URL files using yt-dlp.

**Features:**
- Supports YouTube and Instagram
- Batch processing from files
- Creates CSV logs with download metadata
- Tracks download duration
- Handles 403 errors with retries

**Usage:**
```bash
# From file
python3 download_video.py --file workarea/urls/urls.txt

# Interactive mode
python3 download_video.py

# With cookies (helps avoid 403 errors)
python3 download_video.py --file urls.txt --cookies chrome
```

**CSV Log Format:**
- Status (✅ Success / ❌ Failed)
- Title
- Duration (video length)
- Download Time (time taken to download)
- Video ID
- URL (full URL, not truncated)
- Timestamp
- Error (if any)

**Output:**
- Videos: `~/Downloads/Videos/YYYYMMDD/` (default, can be changed with `--output`)
- Logs: `workarea/logs/<filename>_log.csv` (relative to script directory)

### `trigger_download.py`
Main automation script that chains all steps together.

**Workflow:**
1. Syncs URLs from iCloud Notes → creates timestamped file
2. Downloads all videos from the timestamped file
3. Automatically runs clean up to verify and update Notes

**Usage:**
```bash
# Full workflow
python3 trigger_download.py

# Skip sync (use existing URLs)
python3 trigger_download.py --skip-sync

# Skip clean up
python3 trigger_download.py --skip-cleanup

# Preview clean up changes
python3 trigger_download.py --cleanup-dry-run

# Use Chrome cookies
python3 trigger_download.py --cookies chrome

# Custom URLs file
python3 trigger_download.py --file /path/to/urls.txt
```

**Options:**
- `--skip-sync` - Skip syncing from Notes
- `--skip-cleanup` - Skip verification and Note updates
- `--cleanup-dry-run` - Preview clean up changes
- `--file <path>` - Use specific URLs file
- `--output <dir>` - Custom download directory
- `--cookies <browser>` - Use browser cookies (chrome/firefox/safari/edge)

### `clean_up.py`
Verifies successful downloads and updates iCloud Notes.

**Features:**
- Verifies MP4 files exist for successful downloads
- Removes successfully downloaded URLs from Note
- Moves failed URLs to `---FAILED URLS---` section
- Interactive mode for manual runs

**Usage:**
```bash
# Interactive mode (prompts for file)
python3 clean_up.py

# Command line
python3 clean_up.py log.csv

# Dry run (preview changes)
python3 clean_up.py log.csv --dry-run

# Custom settings
python3 clean_up.py log.csv --download-dir /path --note "MyNote"
```

**What it does:**
1. Reads CSV log file
2. For each successful download:
   - Verifies MP4 file exists by video ID
   - Removes URL from iCloud Note if verified
3. For each failed download:
   - Moves URL to `---FAILED URLS---` section in Note
   - Removes from main content

## Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd video_curator_downloader
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Set up environment variables for `discover_video.py`:
   ```bash
   export YOUTUBE_API_KEY=your_api_key_here
   ```
   Get your YouTube API key at: https://console.cloud.google.com

## Setup

### Prerequisites
- Python 3.x
- macOS (for AppleScript/iCloud Notes integration)

### Configuration
1. Create an iCloud Note titled "Download_URLs" on your iPhone
2. Add video URLs to the note (one per line)
3. Ensure the note syncs to iCloud

### Default Paths
- **Downloads**: `~/Downloads/Videos/` (relative to user home directory)
- **URLs**: `workarea/urls/` (relative to script directory)
- **Logs**: `workarea/logs/` (relative to script directory)

All paths are relative - you can move the `py` folder anywhere and it will work!

## Workflow Example

### Basic Usage
1. **On iPhone**: Add URLs to "Download_URLs" note in Notes app
2. **On Mac**: Run `python3 trigger_download.py`
3. **Result**:
   - URLs synced to timestamped file
   - Videos downloaded to dated folder
   - CSV log created
   - Note automatically updated (successful URLs removed, failed ones moved)

### File Naming
- **URL files**: `20251103_1430_5_urls.txt` (5 URLs at 2:30 PM on Nov 3, 2025)
- **Log files**: `20251103_1430_5_urls_log.csv` (matching log file)

## Roadmap

### 🔴 Priority 1: Verification with Real URLs
**Status**: Pending  
**Description**: Verify that the complete trigger workflow works correctly with real URL inputs from iCloud Notes.

**Tasks**:
- Test full workflow with actual URLs from iCloud Note
- Verify all steps execute correctly (sync → download → clean up)
- Confirm Notes are updated correctly
- Test edge cases (duplicates, failures, etc.)

---

### 🔵 Priority 2: Remote Trigger from Phone
**Status**: Planned  
**Description**: Enable triggering downloads from iPhone and receive notification when all downloads complete.

**Potential Solutions**:
1. **iOS Shortcuts Integration**
   - Create Shortcuts automation
   - Use URL scheme or SSH to trigger script
   - Send notification via Shortcuts

2. **Push Notification Service**
   - Integrate with Pushover, IFTTT, or similar
   - Script sends notification when complete
   - Can trigger from phone via API

3. **Email-based Trigger**
   - Send email to trigger downloads
   - Script monitors email inbox
   - Reply with status when complete

4. **Home Assistant Integration**
   - Use Home Assistant automation
   - HTTP endpoint to trigger script
   - Push notification via HA app

5. **Simple HTTP Server**
   - Run small HTTP server on Mac
   - Phone sends POST request to trigger
   - Server responds with status
   - Could use ngrok for external access

6. **iCloud Reminders/Calendar**
   - Use Reminders app as trigger mechanism
   - Script monitors Reminders
   - Mark as complete when done

**Recommended Approach**: Start with iOS Shortcuts + HTTP endpoint or email-based trigger for simplicity.

## Troubleshooting

### 403 Errors
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Use cookies: `--cookies chrome`
- YouTube may block some requests temporarily

### Notes Not Syncing
- Ensure Note is in iCloud account (not On My Mac)
- Check iCloud sync status in Notes app
- Wait a few seconds for sync to complete

### Files Not Found
- Verify directories exist: `workarea/urls/` and `workarea/logs/`
- Check file permissions
- Ensure paths are correct

### Clean Up Not Working
- Verify CSV log file exists
- Check that Note title matches exactly (case-sensitive)
- Run with `--dry-run` first to preview changes

## Notes

- All scripts use UTF-8 encoding
- CSV logs are optimized for 13" monitor readability
- URL files preserve full URLs (no truncation)
- Timestamped files help track sync sessions
- Failed URLs are preserved in Notes for retry

## License

See [LICENSE](LICENSE) file for details.

---

**Last Updated**: November 2025

