# Workflow Documentation: Run Trigger Download.command

This document describes step-by-step what happens when you execute `Run Trigger Download.command`.

## Overview

The workflow automates downloading videos/audio from URLs stored in iCloud Notes, then imports MP3s to Music.app on your iMac. The entire process runs automatically with a single command.

## Execution Flow

When you double-click `Run Trigger Download.command` or run `python3 trigger_download.py`, the following steps execute in sequence:

---

## STEP 1: SYNC URLs FROM iCLOUD NOTES

**Script:** `sync_notes_to_urls.py`

**What happens:**
1. Reads the iCloud Note titled "Download_URLs" from your Mac's Notes app
2. Extracts URLs from the note content (handles HTML formatting)
3. Separates URLs by markers:
   - URLs under `___mp3___` marker → MP3 downloads
   - URLs under `___mp4___` marker → MP4 downloads
   - URLs without markers → treated as MP4 (default)
4. Checks for duplicate URLs against existing `_workarea/urls/urls.txt`
5. Creates timestamped URL files:
   - `_workarea/urls/YYYYMMDD_HHMM_<count>_mp3_urls.txt` (for MP3 URLs)
   - `_workarea/urls/YYYYMMDD_HHMM_<count>_mp4_urls.txt` (for MP4 URLs)
6. Appends new URLs to the main `_workarea/urls/urls.txt` file (skips duplicates)

**Output:**
- Console shows: Number of MP3 URLs found, MP4 URLs found, duplicates skipped
- Files created: Timestamped URL files in `_workarea/urls/`
- Returns: Dictionary with paths to created MP3 and MP4 URL files

**Example output:**
```
============================================================
   STEP 1: SYNC URLs FROM iCLOUD NOTES
============================================================

✅ Found 5 MP3 URL(s) and 3 MP4 URL(s)
✅ Synced MP3 file: 20251125_1430_5_mp3_urls.txt
✅ Synced MP4 file: 20251125_1430_3_mp4_urls.txt
```

---

## STEP 2: DOWNLOAD VIDEOS/AUDIO

**Script:** `download_video.py`

**What happens:**

### For MP3 URLs (if found):
1. Runs `download_video.py --file <mp3_urls_file> --type audio`
2. Downloads each URL as MP3 audio using yt-dlp
3. Saves files to: `~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP3/YYYYMMDD_##/`
   - Creates date folders in format `YYYYMMDD_##` (e.g., `20251125_01`)
   - Files are named: `Title - Artist.mp3` or similar
4. Creates CSV log file: `_workarea/logs/YYYYMMDD_HHMM_<count>_mp3_urls_log.csv`
   - Log contains: Status, Title, Duration, Download Time, Video ID, URL, Timestamp, Error

### For MP4 URLs (if found):
1. Runs `download_video.py --file <mp4_urls_file> --type video`
2. Downloads each URL as MP4 video using yt-dlp
3. Saves files to: `~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP4/YYYYMMDD_##/`
   - Creates date folders in format `YYYYMMDD_##`
4. Creates CSV log file: `_workarea/logs/YYYYMMDD_HHMM_<count>_mp4_urls_log.csv`

**Output:**
- Console shows: Download progress for each file, success/failure status
- Files created: MP3/MP4 files in dated folders, CSV log files
- Returns: Success status and path to log file(s)

**Example output:**
```
============================================================
   STEP 2: DOWNLOAD MP3s
============================================================

📄 Using latest timestamped file: 20251125_1430_5_mp3_urls.txt
📥 Downloading: Song Title - Artist
   ✅ Success: 3:45 (25s)
📥 Downloading: Another Song - Artist
   ✅ Success: 4:12 (30s)
...
```

---

## STEP 2.6: IMPORT TO MUSIC ON iMAC

**Script:** `import_and_create_playlists.py` (executed on iMac via SSH)

**What happens:**
1. Checks if iMac import is enabled in `config.json` (`imac.enabled: true`)
2. Filters log files to find MP3 log files only
3. If MP3 log files found:
   - Connects to iMac via SSH: `ssh zen@192.168.1.34`
   - Executes on iMac: `python3 /Users/zen/Desktop/vid_dLoadr/import_and_create_playlists.py --all-date-folders`
4. On the iMac, the script:
   - Finds all date folders (`YYYYMMDD_##`) in `~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP3/`
   - For each date folder:
     - Runs `import_to_music.py` to import MP3s to Music.app
       - Checks if files already exist in Music.app library
       - Imports new files only
       - Verifies imports were successful
     - Then runs `create_playlist.py` to create playlists
       - Creates playlists named after date folders (e.g., "20251125_01")
       - Adds tracks from matching folders to their playlists
       - Skips tracks already in playlists

**Output:**
- Console shows: SSH connection status, full output from iMac script
- On iMac: Import progress, playlist creation progress
- Returns: Success status

**Example output:**
```
============================================================
   STEP 2.6: IMPORT TO MUSIC ON iMAC
============================================================

   Found 1 MP3 log file(s)

📡 Connecting to iMac (192.168.1.34)...
   Running: /Users/zen/Desktop/vid_dLoadr/import_and_create_playlists.py

======================================================================
   IMPORT MP3s AND CREATE PLAYLISTS
======================================================================

📁 Base directory: ~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP3
   Found 3 date folder(s) to process

======================================================================
   IMPORTING: 20251125_01
======================================================================
   Found 5 MP3 file(s)
   📥 Importing 5 new file(s) to Music.app...
   ✅ Successfully imported from: 20251125_01

======================================================================
   CREATING PLAYLISTS
======================================================================
   Tracks processed: 5
   Tracks added to playlists: 5
   Playlists created: 1

✅ iMac import completed successfully!
```

**Note:** This step requires:
- SSH key authentication set up (passwordless login)
- Scripts exist on iMac at configured path
- iMac is reachable on network

---

## STEP 3: CLEAN UP & UPDATE NOTES

**Script:** `clean_up.py`

**What happens:**
1. For each log file created during downloads:
   - Reads the CSV log file
   - For each successful download:
     - Verifies the MP3/MP4 file exists in the download directory
     - If verified, removes the URL from iCloud Note "Download_URLs"
   - For each failed download:
     - Moves the URL to "---FAILED URLS---" section in the Note
     - Removes it from the main content
2. Updates the iCloud Note with changes

**Output:**
- Console shows: Verification results, URLs removed, URLs moved to failed section
- iCloud Note: Updated with successful URLs removed, failed URLs moved

**Example output:**
```
============================================================
   STEP 3: CLEAN UP & UPDATE NOTES
============================================================

📄 Processing log file: 20251125_1430_5_mp3_urls_log.csv
   ✅ Verified: 5 files found
   📝 Removed 5 URLs from Note
   ⚠️  Moved 0 failed URLs to failed section
```

---

## FINAL SUMMARY

At the end, a summary is displayed showing the status of each step:

```
============================================================
   FINAL SUMMARY
============================================================

✅ Sync: Completed
✅ Download: Completed
   • MP3 downloads: Completed
   • MP4 downloads: Completed
✅ iMac Import: Completed
✅ Clean Up: Completed

🎉 All done!
```

---

## File Locations

### Created During Workflow:
- **URL files:** `_workarea/urls/YYYYMMDD_HHMM_<count>_<type>_urls.txt`
- **Log files:** `_workarea/logs/YYYYMMDD_HHMM_<count>_<type>_urls_log.csv`
- **MP3 downloads:** `~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP3/YYYYMMDD_##/`
- **MP4 downloads:** `~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP4/YYYYMMDD_##/`

### On iMac:
- **MP3s imported to:** Music.app library
- **Playlists created:** Named after date folders (e.g., "20251125_01")

---

## Skipping Steps

You can skip individual steps using command-line flags:

```bash
python3 trigger_download.py --skip-sync          # Skip syncing from Notes
python3 trigger_download.py --skip-import-imac # Skip iMac import
python3 trigger_download.py --skip-cleanup     # Skip Note updates
```

---

## Error Handling

- If any step fails critically, the workflow may abort
- Non-critical errors (like duplicate URLs) are logged but don't stop the workflow
- Failed downloads are preserved in the Note for retry
- SSH connection failures are logged but don't abort the entire workflow

---

## Prerequisites

1. **iCloud Note:** Must exist with title "Download_URLs" and be synced to iCloud
2. **SSH Access:** SSH keys must be set up for passwordless access to iMac
3. **iMac Scripts:** `import_and_create_playlists.py`, `import_to_music.py`, and `create_playlist.py` must exist on iMac
4. **Network:** iMac must be reachable at configured IP/hostname
5. **iCloud Drive:** Must be syncing properly for files to be accessible on iMac

---

## Configuration

Settings are stored in `config.json`:

```json
{
  "download_dir_mp3": "~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP3",
  "download_dir_mp4": "~/Library/Mobile Documents/com~apple~CloudDocs/Zen/MP4",
  "imac": {
    "hostname": "192.168.1.34",
    "username": "zen",
    "script_path": "/Users/zen/Desktop/vid_dLoadr",
    "enabled": true
  }
}
```

---

## Known Issues & Next Steps

### 🔴 Priority: Fix SSH Login to iMac

**Current Status:** SSH connection to iMac is failing with password prompt and script path error.

**Issue:** 
- Script prompts for SSH password (SSH keys not set up for passwordless login)
- Script path on iMac is incorrect: `/Users/zen/Desktop/vid_dLoadr/import_and_create_playlists.py` doesn't exist
- Error: `can't open file '/Users/zen/Desktop/vid_dLoadr/import_and_create_playlists.py': [Errno 2] No such file or directory`

**Next Steps:**
1. Verify correct script path on iMac
2. Update `config.json` with correct `script_path` for iMac
3. Set up SSH keys for passwordless login OR configure password handling
4. Test SSH connection manually: `ssh zen@192.168.1.34`

---

### ✅ MP4 Sync Pipeline Status

**Current Status:** ✅ **Satisfactory**

The MP4 download and sync pipeline to Zen iPad is working correctly:
- MP4 files download successfully to iCloud Drive
- Files sync to iPad via iCloud Drive
- Workflow is stable and reliable

---

### 🔵 Next Steps: MP4 Hardlink Optimization

**Goal:** Save iCloud storage space (currently limited to 250GB) by using hardlinks instead of duplicating files.

**Current Workflow:**
1. MP4 files download to "postoffice" directory with package# naming (e.g., `20251210_03`)
2. Files sync to iPad via iCloud Drive

**Proposed Workflow:**
1. MP4 files download to "postoffice" directory with package# naming (e.g., `20251210_03`) ✅ Keep as-is
2. Create hardlinks from postoffice to Infuse library directory
3. Infuse library syncs with iPad ✅ Keep as-is
4. **Remove postoffice from iPad sync** - only Infuse library syncs to iPad

**Benefits:**
- Files stored once in iCloud (hardlinks don't duplicate data)
- Postoffice acts as staging area (not synced to iPad)
- Infuse library contains hardlinks (synced to iPad)
- Saves significant iCloud storage space

**Implementation Notes:**
- Use `os.link()` or `ln` command to create hardlinks
- Hardlinks work within same filesystem (iCloud Drive)
- Need to identify Infuse library directory path
- Modify download script to create hardlinks after download completes
- Update iCloud Drive sync settings to exclude postoffice directory

---

### 🔵 Priority 5: Codebase Organization & Security

**Status**: Planned  
**Description**: Clean up directory structure and secure sensitive information.

#### Directory Structure Cleanup

**Current Issue:** Too many Python files in root directory (10+ files):
- `trigger_download.py`
- `remote_trigger_server.py`
- `ssh_connection.py`
- `import_to_music.py`
- `download_video.py`
- `crate_maker.py`
- `create_playlist.py`
- `import_and_create_playlists.py`
- `sync_notes_to_urls.py`
- `clean_up.py`

**Proposed Structure:**
```
video_curator_downloader/
├── src/                    # Main application code
│   ├── core/              # Core workflow scripts
│   │   ├── trigger_download.py
│   │   ├── sync_notes_to_urls.py
│   │   └── clean_up.py
│   ├── download/          # Download-related scripts
│   │   └── download_video.py
│   ├── music/             # Music import scripts
│   │   ├── import_to_music.py
│   │   ├── create_playlist.py
│   │   └── import_and_create_playlists.py
│   ├── remote/             # Remote access scripts
│   │   ├── remote_trigger_server.py
│   │   └── ssh_connection.py
│   └── utils/              # Utility scripts
│       └── crate_maker.py
├── scripts/                # Shell scripts and commands
│   ├── Run Trigger Download.command
│   └── Create Playlists.command
├── config/                 # Configuration files
│   ├── config.json.example
│   └── profiles.json
├── _workarea/              # Working directories (gitignored)
├── docs/                   # Documentation
│   └── WORKFLOW.md
├── README.md
└── requirements.txt
```

**Benefits:**
- Better organization and maintainability
- Clear separation of concerns
- Easier to navigate and understand codebase
- Follows Python project best practices

#### Security Hardening

**Current Security Issues:**

1. **`config.json` contains sensitive information:**
   - Local network IP address: `192.168.1.34`
   - Username: `zen`
   - Script paths
   - **Risk**: Currently committed to GitHub (public repository)

2. **SSH credentials exposure:**
   - IP addresses and usernames visible in code and documentation
   - Need secure remote SSH access solution

**Security Fixes Needed:**

1. **Add `config.json` to `.gitignore`:**
   - Prevent committing sensitive configuration
   - Create `config.json.example` template with placeholder values
   - Document required configuration in README

2. **Secure SSH Access for Remote Use:**
   - **Option A: VPN Solution** (Recommended)
     - Set up VPN server (WireGuard, Tailscale, or macOS Server VPN)
     - Connect to VPN when away from home network
     - Use local IP address through VPN tunnel
     - Most secure, encrypted connection
   
   - **Option B: SSH Tunnel/Port Forwarding**
     - Use SSH jump host or port forwarding
     - Requires intermediate server (VPS, cloud instance)
     - More complex setup
   
   - **Option C: Tailscale/ZeroTier** (Easiest)
     - Install Tailscale on both Macs
     - Creates secure mesh network
     - Access via Tailscale IP address
     - No port forwarding or VPN server needed
     - Free for personal use
   
   - **Option D: Dynamic DNS + Port Forwarding** (Less Secure)
     - Use dynamic DNS service (DuckDNS, No-IP)
     - Forward SSH port on router
     - Access via domain name
     - **Security concerns**: Exposes SSH to internet, use key-only auth

3. **Remove sensitive data from documentation:**
   - Replace real IPs/usernames with placeholders in examples
   - Add security notes about not committing real credentials

4. **Environment variables for sensitive data:**
   - Move SSH password to environment variables (already implemented)
   - Consider moving IP/username to environment variables too
   - Document in README

**Recommended Approach:**
1. ✅ Add `config.json` to `.gitignore` immediately
2. ✅ Create `config.json.example` template
3. 🔵 Set up Tailscale for secure remote access (easiest solution)
4. 🔵 Update documentation with security best practices

#### Git History Security Assessment

**Status:** ⚠️ **Action Required** - Sensitive information found in git history

**Sensitive Information Found:**
- IP address: `192.168.1.34` (local network IP)
- Username: `zen`
- Script path: `/Users/zen/Desktop/vid_dLoadr`

**Where It Appears in Git History:**
- Commit `7c4e861` (HEAD - already pushed to GitHub)
- Commit `9595c37` (Update config.json)
- Commit `f705000` (Update Run Trigger Download.command and config.json)
- Commit `d236b2c` (Add additional MP3 workflow scripts and update config)
- Commit `3df3e50` (Initial commit)

**Repository:** `https://github.com/andy1love/vid_dLoadr.git`

**Risk Assessment:**

**Why It's Relatively Safe:**
1. ✅ `192.168.1.34` is a **private/local IP address**
   - Not routable from the internet
   - Only accessible within your local network
   - Cannot be accessed directly from outside
2. ✅ Username `zen` is generic
   - Not a full credential
   - Still requires password/SSH key to access

**Why It's Still a Concern:**
1. ⚠️ Publicly visible on GitHub
2. ⚠️ If someone gains local network access, they know the target IP
3. ⚠️ Best practice is to avoid exposing any network information

**Recommendations:**

**Option 1: Leave As-Is (Low Risk) - Recommended for Now**
- ✅ Since it's a local IP, the risk is minimal
- ✅ Monitor for any suspicious activity
- ✅ Ensure strong SSH authentication (keys only, no passwords)
- **Action:** No immediate action required, but document decision

**Option 2: Clean Git History (More Secure)**
- Remove `config.json` from all commits
- Rewrite git history using `git filter-branch` or `git filter-repo`
- Force push to GitHub (⚠️ rewrites history, affects collaborators)
- **Command:** `git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch config.json' --prune-empty --tag-name-filter cat -- --all`
- **Action:** Only if maximum security is required

**Option 3: Rotate Credentials (Recommended Long-Term)**
- Change iMac's local IP if possible (router DHCP reservation)
- Use different username if desired
- Set up SSH keys and disable password authentication
- Update `config.json` with new values (now gitignored)
- **Action:** Good security practice, but not urgent

**Immediate Actions Already Taken:**
- ✅ Added `config.json` to `.gitignore` (prevents future commits)
- ✅ Created `config.json.example` template (safe to commit)
- ✅ Documentation updated with security notes

**Decision Required:**
When you next open this project, decide how to proceed:
1. **Accept current risk** (local IP is relatively safe) - No action needed
2. **Clean git history** - Use `git filter-branch` or `git filter-repo` to remove sensitive data
3. **Rotate credentials** - Change IP/username and update config (now gitignored)

**Current Recommendation:** 
Given that `192.168.1.34` is a local IP, the immediate risk is **low**. Focus on:
- Strong SSH security (key-based auth, disable passwords)
- Network security (firewall, VPN if accessing remotely)
- Monitoring for suspicious access attempts

Cleaning git history is **not critical** but provides maximum security.

---

**Last Updated:** December 2025

