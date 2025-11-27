#!/usr/bin/env python3
"""
Trigger Script - Sync Notes to URLs then Download Videos
Automates the workflow: iCloud Notes → urls.txt → download videos
"""

import subprocess
import sys
import os
import glob
import json

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

def run_sync_notes():
    """Run sync_notes_to_urls.py to sync URLs from Notes to urls.txt
    Returns: dict with 'mp3' and 'mp4' keys containing file paths, or False on error"""
    print("=" * 60)
    print("   STEP 1: SYNC URLs FROM iCLOUD NOTES")
    print("=" * 60)
    print()
    
    script_path = os.path.join(os.path.dirname(__file__), 'sync_notes_to_urls.py')
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=False,
            capture_output=True,  # Capture to parse output
            text=True
        )
        
        # Print the output
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Extract the output filenames from the output
        output_files = {}
        for line in result.stdout.split('\n'):
            if line.startswith('OUTPUT_FILE_MP3:'):
                output_files['mp3'] = line.split('OUTPUT_FILE_MP3:', 1)[1].strip()
            elif line.startswith('OUTPUT_FILE_MP4:'):
                output_files['mp4'] = line.split('OUTPUT_FILE_MP4:', 1)[1].strip()
            elif line.startswith('OUTPUT_FILE:'):
                # Legacy format - treat as MP4
                output_files['mp4'] = line.split('OUTPUT_FILE:', 1)[1].strip()
        
        if result.returncode == 0:
            print("\n✅ Sync completed successfully!")
            return output_files if output_files else True
        else:
            print(f"\n⚠️  Sync completed with exit code {result.returncode}")
            # Continue anyway - might have skipped duplicates which is fine
            return output_files if output_files else True
            
    except FileNotFoundError:
        print(f"❌ Error: Could not find sync_notes_to_urls.py at {script_path}")
        return False
    except Exception as e:
        print(f"❌ Error running sync script: {e}")
        return False

def find_latest_timestamped_file(urls_dir):
    """Find the most recent timestamped URLs file"""
    pattern = os.path.join(urls_dir, '*_*_urls.txt')
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Sort by modification time, most recent first
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def run_sync_to_infuse(log_files, download_dir, dry_run=False):
    """Run sync_to_infuse.py to copy files to iCloud Drive
    Returns: success status"""
    print("\n" + "=" * 60)
    print("   STEP 2.5: SYNC TO INFUSE (iCloud Drive)")
    print("=" * 60)
    print()
    
    script_path = os.path.join(os.path.dirname(__file__), 'sync_to_infuse.py')
    
    if not log_files:
        print("⏭️  No log files to sync")
        return True
    
    # Filter to only existing log files
    existing_logs = [f for f in log_files if f and os.path.exists(f)]
    if not existing_logs:
        print("⏭️  No valid log files found for syncing")
        return True
    
    try:
        # Build command - process all log files
        cmd = [sys.executable, script_path]
        
        # Add all log files as positional arguments (sync_to_infuse.py accepts multiple)
        cmd.extend(existing_logs)
        
        if download_dir:
            cmd.extend(['--download-dir', download_dir])
        
        if dry_run:
            cmd.append('--dry-run')
        
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=False,
            text=True
        )
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find sync_to_infuse.py at {script_path}")
        return False
    except Exception as e:
        print(f"❌ Error running sync script: {e}")
        return False

def run_clean_up(log_file, download_dir, note_title="Download_URLs", dry_run=False):
    """Run clean_up.py to verify downloads and update iCloud Notes"""
    print("\n" + "=" * 60)
    print("   STEP 3: CLEAN UP & UPDATE NOTES")
    print("=" * 60)
    print()
    
    script_path = os.path.join(os.path.dirname(__file__), 'clean_up.py')
    
    # Build command
    cmd = [sys.executable, script_path, log_file]
    
    if download_dir:
        cmd.extend(['--download-dir', download_dir])
    
    if note_title:
        cmd.extend(['--note', note_title])
    
    if dry_run:
        cmd.append('--dry-run')
    
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=False,
            text=True
        )
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find clean_up.py at {script_path}")
        return False
    except Exception as e:
        print(f"❌ Error running clean up script: {e}")
        return False

def run_download_videos(urls_file=None, use_cookies=None, cookies_browser=None, output_dir=None, download_type='video'):
    """Run download_video.py to download videos or audio from urls.txt
    download_type: 'video' or 'audio'
    Returns: (success: bool, log_file: str or None)"""
    download_type_name = "MP3s" if download_type == 'audio' else "VIDEOS"
    print("\n" + "=" * 60)
    print(f"   STEP 2: DOWNLOAD {download_type_name}")
    print("=" * 60)
    print()
    
    script_path = os.path.join(os.path.dirname(__file__), 'download_video.py')
    
    # Build command
    cmd = [sys.executable, script_path]
    
    if urls_file:
        # If urls_file is True (from sync), use default logic
        if isinstance(urls_file, bool):
            urls_file = None
        else:
            cmd.extend(['--file', urls_file])
    
    if not urls_file:
        # Try to find the latest timestamped file in urls/ directory
        workarea_dir = os.path.join(os.path.dirname(__file__), '_workarea')
        urls_dir = os.path.join(workarea_dir, 'urls')
        latest_file = find_latest_timestamped_file(urls_dir)
        
        if latest_file:
            print(f"📄 Using latest timestamped file: {os.path.basename(latest_file)}")
            cmd.extend(['--file', latest_file])
            urls_file = latest_file  # Store for log file generation
        else:
            # Fallback to default
            default_file = os.path.join(urls_dir, 'urls.txt')
            print(f"📄 Using default file: {os.path.basename(default_file)}")
            cmd.extend(['--file', default_file])
            urls_file = default_file
    
    # Add download type
    cmd.extend(['--type', download_type])
    
    if output_dir:
        cmd.extend(['--output', output_dir])
    
    if use_cookies and cookies_browser:
        cmd.extend(['--cookies', cookies_browser])
    
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=False,
            text=True
        )
        
        # Generate expected log file path
        log_file = None
        if urls_file:
            # Log file is created by download_video.py with pattern: <urls_file_base>_log.csv
            # in _workarea/logs/ directory
            base_name = os.path.splitext(os.path.basename(urls_file))[0]
            workarea_dir = os.path.join(os.path.dirname(__file__), '_workarea')
            logs_dir = os.path.join(workarea_dir, 'logs')
            log_file = os.path.join(logs_dir, f"{base_name}_log.csv")
        
        return result.returncode == 0, log_file
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find download_video.py at {script_path}")
        return False, None
    except Exception as e:
        print(f"❌ Error running download script: {e}")
        return False, None

def main():
    """Main trigger function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Trigger script: Sync Notes → Download Videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trigger_download.py                    # Full workflow (default settings)
  python trigger_download.py --skip-sync        # Skip sync, just download
  python trigger_download.py --cookies chrome   # Use Chrome cookies for downloads
  python trigger_download.py --file custom.txt  # Use custom URLs file
        """
    )
    
    parser.add_argument(
        '--skip-sync',
        action='store_true',
        help='Skip syncing from Notes, just download from existing urls.txt'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='Path to URLs file (default: workarea/urls.txt)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output directory for downloads (default: from download_video.py)'
    )
    
    parser.add_argument(
        '--cookies',
        type=str,
        choices=['chrome', 'firefox', 'safari', 'edge'],
        help='Browser to extract cookies from (helps avoid 403 errors)'
    )
    
    parser.add_argument(
        '--skip-sync-infuse',
        action='store_true',
        help='Skip syncing files to INFUSE/iCloud Drive'
    )
    
    parser.add_argument(
        '--skip-cleanup',
        action='store_true',
        help='Skip the clean up step after downloads'
    )
    
    parser.add_argument(
        '--cleanup-dry-run',
        action='store_true',
        help='Run clean up in dry-run mode (preview changes without applying)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("   TRIGGER: SYNC & DOWNLOAD AUTOMATION")
    print("=" * 60)
    print()
    
    # Step 1: Sync from Notes (unless skipped)
    synced_files = {}
    if not args.skip_sync:
        sync_result = run_sync_notes()
        if not sync_result:
            print("\n❌ Sync failed. Aborting.")
            sys.exit(1)
        # sync_result could be a dict with 'mp3' and 'mp4' keys, or True
        if isinstance(sync_result, dict):
            synced_files = sync_result
            if 'mp3' in synced_files:
                print(f"\n✅ Synced MP3 file: {os.path.basename(synced_files['mp3'])}")
            if 'mp4' in synced_files:
                print(f"\n✅ Synced MP4 file: {os.path.basename(synced_files['mp4'])}")
        elif isinstance(sync_result, str):
            # Legacy format - treat as MP4
            synced_files['mp4'] = sync_result
            print(f"\n✅ Synced file: {os.path.basename(sync_result)}")
    else:
        print("⏭️  Skipping sync step (--skip-sync flag used)")
    
    # Step 2: Download videos and/or audio
    download_success = True
    log_files = []
    
    # Download MP3s if we have MP3 URLs
    if synced_files.get('mp3') or (args.file and 'mp3' in os.path.basename(args.file).lower()):
        mp3_file = synced_files.get('mp3') or args.file
        mp3_success, mp3_log = run_download_videos(
            urls_file=mp3_file,
            use_cookies=bool(args.cookies),
            cookies_browser=args.cookies,
            output_dir=args.output,
            download_type='audio'
        )
        if mp3_log:
            log_files.append(mp3_log)
        if not mp3_success:
            download_success = False
    
    # Download MP4s if we have MP4 URLs
    if synced_files.get('mp4') or (args.file and 'mp4' in os.path.basename(args.file).lower()) or not synced_files.get('mp3'):
        mp4_file = synced_files.get('mp4') or args.file
        mp4_success, mp4_log = run_download_videos(
            urls_file=mp4_file,
            use_cookies=bool(args.cookies),
            cookies_browser=args.cookies,
            output_dir=args.output,
            download_type='video'
        )
        if mp4_log:
            log_files.append(mp4_log)
        if not mp4_success:
            download_success = False
    
    # Step 2.5: Sync to INFUSE (iCloud Drive)
    sync_infuse_success = None
    if not args.skip_sync_infuse and download_success and log_files:
        # Note: sync_to_infuse.py will determine the correct directory per log file
        # based on file type (MP3 vs MP4), so we don't need to specify it here
        # If --output is provided, it will override the config for all files
        default_download_dir = None  # Let sync_to_infuse.py use config per file type
        
        sync_infuse_success = run_sync_to_infuse(
            log_files=log_files,
            download_dir=args.output,  # Only use if provided, otherwise None
            dry_run=False  # Always run for real (not dry-run)
        )
    elif args.skip_sync_infuse:
        print("\n⏭️  Skipping INFUSE sync step (--skip-sync-infuse flag used)")
    elif not log_files or not any(os.path.exists(f) for f in log_files if f):
        print(f"\n⚠️  Log files not found")
        print("   Skipping INFUSE sync step")
    
    # Step 3: Clean up (verify downloads and update Notes)
    cleanup_success = None
    if not args.skip_cleanup and download_success and log_files:
        # Get note title from sync result or use default
        note_title = "Download_URLs"  # Default
        
        # Note: clean_up.py will determine the correct directory per log file
        # based on file type (MP3 vs MP4), so we don't need to specify it here
        # If --output is provided, it will override the config for all files
        
        # Run clean up for each log file
        for log_file in log_files:
            if log_file and os.path.exists(log_file):
                cleanup_success = run_clean_up(
                    log_file=log_file,
                    download_dir=args.output,  # Only use if provided, otherwise None
                    note_title=note_title,
                    dry_run=args.cleanup_dry_run
                )
    elif args.skip_cleanup:
        print("\n⏭️  Skipping clean up step (--skip-cleanup flag used)")
    elif not log_files or not any(os.path.exists(f) for f in log_files if f):
        print(f"\n⚠️  Log files not found")
        print("   Skipping clean up step")
    
    # Final summary
    print("\n" + "=" * 60)
    print("   FINAL SUMMARY")
    print("=" * 60)
    
    if args.skip_sync:
        print("⏭️  Sync: Skipped")
    else:
        print("✅ Sync: Completed")
    
    if download_success:
        print("✅ Download: Completed")
        if synced_files.get('mp3'):
            print("   • MP3 downloads: Completed")
        if synced_files.get('mp4'):
            print("   • MP4 downloads: Completed")
    else:
        print("❌ Download: Failed or had errors")
    
    if sync_infuse_success is not None:
        if sync_infuse_success:
            print("✅ INFUSE Sync: Completed")
        else:
            print("⚠️  INFUSE Sync: Completed with warnings")
    elif not args.skip_sync_infuse:
        print("⏭️  INFUSE Sync: Skipped (no log files)")
    
    if cleanup_success is not None:
        if cleanup_success:
            print("✅ Clean Up: Completed")
        else:
            print("⚠️  Clean Up: Completed with warnings")
    elif not args.skip_cleanup:
        print("⏭️  Clean Up: Skipped (log file not found)")
    
    if download_success:
        print("\n🎉 All done!")
        sys.exit(0)
    else:
        print("\n⚠️  Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()

