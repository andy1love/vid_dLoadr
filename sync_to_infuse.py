#!/usr/bin/env python3
"""
Sync to INFUSE Script
Copies downloaded MP3 and MP4 files to iCloud Drive for INFUSE app
Tracks synced files to avoid duplicates
"""

import os
import sys
import json
import csv
import shutil
import argparse
import glob
from datetime import datetime
from urllib.parse import urlparse, parse_qs

def load_config():
    """Load configuration from config.json
    Returns: dict with config values, or empty dict if file not found"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Warning: Could not load config.json: {e}")
            return {}
    return {}

def get_default_download_dir(file_type='video'):
    """Get default download directory from config.json based on file type
    file_type: 'video' for MP4, 'audio' for MP3
    Returns: base directory path for the file type"""
    config = load_config()
    
    if file_type == 'audio':
        download_dir = config.get('download_dir_mp3', None)
    else:
        download_dir = config.get('download_dir_mp4', None)
    
    if download_dir:
        # Expand user home directory if path starts with ~
        return os.path.expanduser(download_dir)
    
    # Fallback to default
    return os.path.join(os.path.expanduser("~"), "Downloads", "Videos")

# Import helper functions from clean_up.py
sys.path.insert(0, os.path.dirname(__file__))
try:
    from clean_up import extract_video_id, find_downloaded_file, detect_file_type_from_log_filename
except ImportError:
    # Fallback if import fails
    def extract_video_id(url):
        """Extract video ID from YouTube/Instagram URL"""
        try:
            parsed = urlparse(url)
            if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
                if 'youtu.be' in parsed.netloc:
                    return parsed.path.lstrip('/').split('?')[0]
                elif 'watch' in parsed.path:
                    params = parse_qs(parsed.query)
                    return params.get('v', [None])[0]
            elif 'instagram.com' in parsed.netloc:
                path_parts = [p for p in parsed.path.split('/') if p]
                if len(path_parts) >= 2:
                    return path_parts[-1].rstrip('/')
            return None
        except:
            return None
    
    def find_downloaded_file(video_id, download_base_dir, file_type='video'):
        """Find downloaded file by video ID
        Searches in dated package folders (YYYYMMDD_## format)"""
        if not video_id:
            return None
        ext = 'mp3' if file_type == 'audio' else 'mp4'
        # Search in dated package folders (YYYYMMDD_## format)
        patterns = [
            os.path.join(download_base_dir, f'{datetime.now().strftime("%Y%m%d")}_*', f'*{video_id}*.{ext}'),
            os.path.join(download_base_dir, '*_*', f'*{video_id}*.{ext}'),
            os.path.join(download_base_dir, f'*{video_id}*.{ext}'),
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None
    
    def detect_file_type_from_log_filename(log_file):
        """Detect file type from log filename"""
        if not log_file:
            return 'video'
        filename = os.path.basename(log_file).lower()
        if 'mp3' in filename:
            return 'audio'
        elif 'mp4' in filename:
            return 'video'
        return 'video'

def get_tracking_file_path():
    """Get path to tracking JSON file"""
    script_dir = os.path.dirname(__file__)
    workarea_dir = os.path.join(script_dir, '_workarea')
    os.makedirs(workarea_dir, exist_ok=True)
    return os.path.join(workarea_dir, 'sync_tracking.json')

def load_tracking_data():
    """Load tracking data from JSON file"""
    tracking_file = get_tracking_file_path()
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not load tracking file: {e}")
            return {}
    return {}

def save_tracking_data(tracking_data):
    """Save tracking data to JSON file"""
    tracking_file = get_tracking_file_path()
    try:
        with open(tracking_file, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving tracking file: {e}")
        return False

def get_icloud_infuse_paths():
    """Get iCloud Drive INFUSE folder paths"""
    icloud_base = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
    base_folder = os.path.join(icloud_base, "Infuse")
    return {
        'base': base_folder,
        'mp3': os.path.join(base_folder, "MP3"),
        'mp4': os.path.join(base_folder, "MP4")
    }

def get_date_folder_from_source(source_path):
    """Extract date folder (YYYYMMDD) from source file path
    Handles both old format (YYYYMMDD) and new format (YYYYMMDD_##)"""
    # Source path format: ~/Library/.../YYYYMMDD_01/file.mp3
    parts = source_path.split(os.sep)
    for part in parts:
        # Check for new format: YYYYMMDD_##
        if '_' in part and len(part) >= 9:  # At least YYYYMMDD_01
            date_part = part.split('_')[0]
            if date_part.isdigit() and len(date_part) == 8:  # YYYYMMDD format
                return date_part
        # Check for old format: YYYYMMDD
        elif part.isdigit() and len(part) == 8:  # YYYYMMDD format
            return part
    # Fallback: use today's date
    return datetime.now().strftime('%Y%m%d')

def copy_file_to_icloud(source_file, icloud_base_folder, date_folder, file_type='video'):
    """Copy file to iCloud Drive maintaining date folder structure"""
    if not os.path.exists(source_file):
        return None, f"Source file not found: {source_file}"
    
    # Determine destination folder
    if file_type == 'audio':
        dest_base = os.path.join(icloud_base_folder, 'MP3')
    else:
        dest_base = os.path.join(icloud_base_folder, 'MP4')
    
    # Create date folder in destination
    dest_date_folder = os.path.join(dest_base, date_folder)
    os.makedirs(dest_date_folder, exist_ok=True)
    
    # Destination file path
    filename = os.path.basename(source_file)
    dest_file = os.path.join(dest_date_folder, filename)
    
    # Check if file already exists (by name)
    if os.path.exists(dest_file):
        # Compare file sizes to see if it's the same file
        source_size = os.path.getsize(source_file)
        dest_size = os.path.getsize(dest_file)
        if source_size == dest_size:
            return dest_file, "File already exists (same size)"
    
    try:
        # Copy file
        shutil.copy2(source_file, dest_file)
        return dest_file, None
    except Exception as e:
        return None, str(e)

def read_log_csv(log_file):
    """Read CSV log file"""
    if not os.path.exists(log_file):
        return []
    
    try:
        entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append(row)
        return entries
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return []

def sync_log_to_infuse(log_file, download_base_dir, icloud_paths, tracking_data, dry_run=False):
    """Sync files from log to INFUSE iCloud Drive folder"""
    # Detect file type from log filename
    file_type = detect_file_type_from_log_filename(log_file)
    file_type_name = "MP3" if file_type == 'audio' else "MP4"
    
    print(f"\n📄 Processing log file: {os.path.basename(log_file)}")
    print(f"   Type: {file_type_name}")
    
    # Read log entries
    log_entries = read_log_csv(log_file)
    if not log_entries:
        print("   ⚠️  No entries found in log file")
        return 0, 0, 0
    
    successful_syncs = 0
    skipped_syncs = 0
    failed_syncs = 0
    
    for entry in log_entries:
        status = entry.get('Status', '')
        video_id = entry.get('Video ID', '')
        url = entry.get('URL', '')
        title = entry.get('Title', 'Unknown')[:50]
        
        # Only process successful downloads
        if '✅ Success' not in status:
            continue
        
        if not video_id:
            print(f"\n⚠️  Skipping (no video ID): {title}...")
            skipped_syncs += 1
            continue
        
        # Check if already synced
        if video_id in tracking_data:
            tracked_info = tracking_data[video_id]
            if tracked_info.get('synced', False):
                dest_path = tracked_info.get('icloud_path', '')
                if dest_path and os.path.exists(dest_path):
                    print(f"\n⏭️  Already synced: {title}...")
                    skipped_syncs += 1
                    continue
        
        # Find downloaded file
        source_file = find_downloaded_file(video_id, download_base_dir, file_type)
        if not source_file or not os.path.exists(source_file):
            print(f"\n⚠️  File not found: {title}... (Video ID: {video_id})")
            skipped_syncs += 1
            continue
        
        # Get date folder from source path
        date_folder = get_date_folder_from_source(source_file)
        
        if dry_run:
            print(f"\n🔍 [DRY RUN] Would sync: {title}...")
            print(f"   Source: {source_file}")
            print(f"   Dest: {icloud_paths['mp3' if file_type == 'audio' else 'mp4']}/{date_folder}/")
            successful_syncs += 1
        else:
            # Copy file to iCloud Drive
            print(f"\n📤 Syncing: {title}...")
            dest_file, error = copy_file_to_icloud(
                source_file,
                icloud_paths['base'],
                date_folder,
                file_type
            )
            
            if dest_file and not error:
                print(f"   ✅ Copied to: {dest_file}")
                # Update tracking data
                tracking_data[video_id] = {
                    'synced': True,
                    'synced_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source_path': source_file,
                    'icloud_path': dest_file,
                    'file_type': file_type,
                    'title': title
                }
                successful_syncs += 1
            elif error and "already exists" in error.lower():
                print(f"   ⏭️  {error}")
                # Update tracking even if file exists
                tracking_data[video_id] = {
                    'synced': True,
                    'synced_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source_path': source_file,
                    'icloud_path': dest_file,
                    'file_type': file_type,
                    'title': title
                }
                skipped_syncs += 1
            else:
                print(f"   ❌ Error: {error}")
                failed_syncs += 1
    
    return successful_syncs, skipped_syncs, failed_syncs

def main():
    parser = argparse.ArgumentParser(
        description="Sync downloaded files to INFUSE via iCloud Drive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_to_infuse.py log.csv                    # Sync from log file
  python sync_to_infuse.py --all                       # Sync all recent logs
  python sync_to_infuse.py log.csv --dry-run          # Preview changes
        """
    )
    
    parser.add_argument(
        'log_file',
        type=str,
        nargs='*',  # Accept multiple log files
        help='Path(s) to CSV log file(s) (optional - use --all for all recent logs)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all recent log files in _workarea/logs/'
    )
    
    parser.add_argument(
        '--download-dir',
        type=str,
        default=None,  # Will be set to config value or default in main()
        help='Base download directory (default: from config.json or ~/Downloads/Videos)'
    )
    
    parser.add_argument(
        '--icloud-base',
        type=str,
        help='iCloud Drive base path (default: auto-detect)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without copying files'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("   SYNC TO INFUSE (iCloud Drive)")
    print("=" * 60)
    
    # Get iCloud paths
    if args.icloud_base:
        icloud_paths = {
            'base': args.icloud_base,
            'mp3': os.path.join(args.icloud_base, 'MP3'),
            'mp4': os.path.join(args.icloud_base, 'MP4')
        }
    else:
        icloud_paths = get_icloud_infuse_paths()
    
    # Note: download_dir will be determined per log file based on file type
    # If --download-dir is provided, it will override config for all files
    download_dir_override = args.download_dir
    
    print(f"\n📁 Download directories (from config):")
    print(f"   MP3: {get_default_download_dir('audio')}")
    print(f"   MP4: {get_default_download_dir('video')}")
    if download_dir_override:
        print(f"   Override: {download_dir_override}")
    print(f"📁 iCloud Drive base: {icloud_paths['base']}")
    print(f"   MP3 folder: {icloud_paths['mp3']}")
    print(f"   MP4 folder: {icloud_paths['mp4']}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be copied")
    
    # Load tracking data
    tracking_data = load_tracking_data()
    print(f"\n📊 Tracking {len(tracking_data)} previously synced files")
    
    # Determine which log files to process
    log_files = []
    
    if args.all:
        # Find all log files in _workarea/logs/
        script_dir = os.path.dirname(__file__)
        logs_dir = os.path.join(script_dir, '_workarea', 'logs')
        if os.path.exists(logs_dir):
            log_files = glob.glob(os.path.join(logs_dir, '*_log.csv'))
            log_files.sort(key=os.path.getmtime, reverse=True)  # Most recent first
            print(f"\n📄 Found {len(log_files)} log file(s) to process")
        else:
            print(f"\n❌ Logs directory not found: {logs_dir}")
            sys.exit(1)
    elif args.log_file and len(args.log_file) > 0:
        # Filter to only existing files
        existing_files = [f for f in args.log_file if os.path.exists(f)]
        if existing_files:
            log_files = existing_files
            print(f"\n📄 Processing {len(log_files)} log file(s)")
        else:
            print(f"\n❌ None of the specified log files were found")
            sys.exit(1)
    else:
        print("\n❌ No log file specified. Use --all or provide log file path(s).")
        parser.print_help()
        sys.exit(1)
    
    # Process each log file
    total_successful = 0
    total_skipped = 0
    total_failed = 0
    
    for log_file in log_files:
        # Determine the correct download directory for this log file
        # Detect file type from log filename
        file_type = detect_file_type_from_log_filename(log_file)
        # Use override if provided, otherwise use config-based directory for this file type
        download_dir = download_dir_override if download_dir_override else get_default_download_dir(file_type)
        
        successful, skipped, failed = sync_log_to_infuse(
            log_file,
            download_dir,
            icloud_paths,
            tracking_data,
            dry_run=args.dry_run
        )
        total_successful += successful
        total_skipped += skipped
        total_failed += failed
    
    # Save tracking data
    if not args.dry_run:
        save_tracking_data(tracking_data)
    
    # Summary
    print("\n" + "=" * 60)
    print("   SYNC SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully synced: {total_successful}")
    print(f"⏭️  Skipped (already synced/not found): {total_skipped}")
    print(f"❌ Failed: {total_failed}")
    print(f"📊 Total tracked files: {len(tracking_data)}")
    
    if total_successful > 0 and not args.dry_run:
        print("\n💡 Tip: Files are syncing to iCloud Drive.")
        print("   They will appear in INFUSE once iCloud sync completes.")
        print("   You may need to refresh INFUSE library on your iPad.")

if __name__ == "__main__":
    main()

