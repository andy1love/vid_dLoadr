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
- `--skip-import-imac` - Skip importing to Music.app on iMac
- `--ssh <mode>` - Execution mode for iMac import (local/ssh)

### `remote_trigger_server.py`
HTTP server for triggering downloads remotely from iPhone/iOS Shortcuts.

**Features:**
- Simple HTTP server with REST API
- Web interface for status monitoring
- Background job execution
- Status tracking and output logging

**Usage:**
```bash
# Start server (default port 8080)
python3 remote_trigger_server.py

# Custom port
python3 remote_trigger_server.py --port 9000

# Custom host
python3 remote_trigger_server.py --host 192.168.1.100
```

**Endpoints:**
- `POST /trigger` - Trigger download workflow
- `GET /status` - Get current status (JSON)
- `GET /` - Web interface

See Roadmap section for detailed iOS Shortcuts setup instructions.

### `clean_up.py`
Verifies successful downloads and updates iCloud Notes.

**Features:**
- Verifies MP3/MP4 files exist for successful downloads
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
   - Verifies MP3/MP4 file exists by video ID
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

### ✅ Priority 1: Verification with Real URLs
**Status**: Complete  
**Description**: Verify that the complete trigger workflow works correctly with real URL inputs from iCloud Notes.

**Completed**:
- ✅ Full workflow tested with actual URLs from iCloud Note
- ✅ All steps execute correctly (sync → download → clean up)
- ✅ Notes are updated correctly
- ✅ Edge cases handled (duplicates, failures, etc.)

---

### 🔵 Priority 2: Remote Trigger from Phone
**Status**: In Progress  
**Description**: Enable triggering downloads from iPhone and receive notification when all downloads complete.

**Implementation**: Simple HTTP Server (recommended approach)
- ✅ HTTP server script created (`remote_trigger_server.py`)
- ✅ POST endpoint to trigger downloads
- ✅ Status endpoint to check download progress
- ⏳ iOS Shortcuts integration (documentation needed)
- ⏳ Push notification support (optional enhancement)

**Usage**:

1. **Start the HTTP server on your Mac:**
   ```bash
   python3 remote_trigger_server.py
   # Or on a custom port:
   python3 remote_trigger_server.py --port 9000
   ```

2. **Find your Mac's IP address:**
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   # Or in System Preferences > Network
   ```

3. **Trigger from iPhone/iOS Shortcuts:**
   - Create a Shortcut with "Get Contents of URL" action
   - Method: POST
   - URL: `http://<your-mac-ip>:8080/trigger`
   - Add to Home Screen or Control Center for quick access

4. **Check status:**
   - Visit `http://<your-mac-ip>:8080/` in a browser for web interface
   - Or GET `http://<your-mac-ip>:8080/status` for JSON status

**API Endpoints:**
- `POST /trigger` - Start download workflow
- `GET /status` - Get current download status (JSON)
- `GET /` - Web interface with status and trigger button

**Query Parameters** (for POST /trigger):
- `?skip_sync=true` - Skip syncing from Notes
- `?skip_cleanup=true` - Skip cleanup step
- `?skip_import_imac=true` - Skip iMac import
- `?cookies=chrome` - Use browser cookies
- `?ssh_mode=local` - Run iMac import locally

**Example iOS Shortcuts Setup:**
1. Open Shortcuts app
2. Create new shortcut
3. Add "Get Contents of URL" action
4. Set URL to: `http://<your-mac-ip>:8080/trigger`
5. Set Method to: POST
6. Add "Show Notification" action to confirm trigger
7. Add to Home Screen or Control Center

**Alternative Solutions** (for future consideration):
- Push Notification Service (Pushover, IFTTT)
- Email-based Trigger
- Home Assistant Integration
- iCloud Reminders/Calendar

---

### 🔴 Priority 3: Fix SSH Login to iMac
**Status**: Blocked  
**Description**: Fix SSH connection issues preventing MP3 import to Music.app on iMac.

**Issues:**
- SSH prompts for password (SSH keys not configured)
- Script path incorrect on iMac: `/Users/zen/Desktop/vid_dLoadr/import_and_create_playlists.py` doesn't exist
- Need to verify correct path and set up passwordless SSH or password handling

**Next Steps:**
1. Verify correct script path on iMac
2. Update `config.json` with correct `script_path`
3. Set up SSH keys OR configure password handling
4. Test SSH connection

---

### ✅ MP4 Sync Pipeline
**Status**: ✅ **Satisfactory**  
**Description**: MP4 download and sync to Zen iPad via iCloud Drive.

**Current Status:**
- ✅ MP4 files download successfully
- ✅ Files sync to iPad via iCloud Drive
- ✅ Workflow is stable and reliable

---

### 🔵 Priority 4: MP4 Hardlink Optimization
**Status**: Planned  
**Description**: Optimize iCloud storage usage by using hardlinks instead of duplicating MP4 files.

**Current Workflow:**
- Files download to "postoffice" directory (package# naming)
- Postoffice syncs to iPad via iCloud Drive

**Proposed Workflow:**
- Files download to "postoffice" directory (staging area, not synced to iPad)
- Create hardlinks from postoffice to Infuse library
- Only Infuse library syncs to iPad
- **Benefit**: Files stored once, saves iCloud storage space (currently 250GB limit)

**Implementation:**
- Use `os.link()` or `ln` command for hardlinks
- Modify download script to create hardlinks after download
- Update iCloud Drive sync settings to exclude postoffice directory

---

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

**Last Updated**: December 2025

