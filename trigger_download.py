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
import ssh_connection

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

def find_latest_timestamped_file(urls_dir, file_type='', max_age_minutes=60):
    """Find the most recent timestamped URLs file
    file_type: 'mp3', 'mp4', or '' for any
    max_age_minutes: Only return files newer than this (default: 60 minutes)
    Returns: file path or None"""
    import time
    
    pattern = os.path.join(urls_dir, '*_*_urls.txt')
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Filter by file type if specified
    if file_type:
        files = [f for f in files if f'_{file_type}_urls.txt' in os.path.basename(f)]
    
    if not files:
        return None
    
    # Sort by modification time, most recent first
    files.sort(key=os.path.getmtime, reverse=True)
    
    # Check if the most recent file is within the age limit
    if max_age_minutes > 0:
        most_recent = files[0]
        file_age_minutes = (time.time() - os.path.getmtime(most_recent)) / 60
        
        if file_age_minutes > max_age_minutes:
            # File is too old, don't use it
            return None
    
    return files[0]

def run_import_on_imac(log_files, dry_run=False, ssh_mode='ssh'):
    """Run import_and_create_playlists.py on iMac via SSH or locally
    ssh_mode: 'ssh' to run via SSH, 'local' to run locally
    Returns: success status (True/False) or None if skipped"""
    print("\n" + "=" * 60)
    print("   STEP 2.6: IMPORT TO MUSIC ON iMAC")
    print("=" * 60)
    print()
    
    config = load_config()
    imac_config = config.get('imac', {})
    
    if not imac_config.get('enabled', False):
        print("⏭️  iMac import is disabled in config.json")
        return None
    
    # Check if we have any MP3 log files
    mp3_logs = [f for f in log_files if f and os.path.exists(f) and 'mp3' in os.path.basename(f).lower()]
    
    if not mp3_logs:
        print("⏭️  No MP3 log files found - skipping iMac import")
        return None
    
    print(f"   Found {len(mp3_logs)} MP3 log file(s)")
    
    if ssh_mode == 'local':
        # Run locally
        script_path = os.path.join(os.path.dirname(__file__), 'import_and_create_playlists.py')
        
        if not os.path.exists(script_path):
            print(f"❌ Error: Could not find import_and_create_playlists.py at {script_path}")
            return False
        
        # Build local command
        cmd = [sys.executable, script_path, '--all-date-folders']
        
        if dry_run:
            cmd.append('--dry-run')
        
        print(f"\n💻 Running locally...")
        print(f"   Running: {script_path}")
        
        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print("\n✅ Local import completed successfully!")
                return True
            else:
                print(f"\n⚠️  Local import completed with exit code {result.returncode}")
                return False
                
        except FileNotFoundError:
            print(f"\n❌ Error: Could not find import_and_create_playlists.py at {script_path}")
            return False
        except Exception as e:
            print(f"\n❌ Error running local import command: {e}")
            return False
    
    else:
        # Run via SSH (default)
        hostname, username, script_path = ssh_connection.get_ssh_config()
        
        if not hostname or not username or not script_path:
            print("⚠️  iMac configuration incomplete. Please check config.json")
            return False
        
        # Build the remote command
        remote_script = os.path.join(script_path, 'import_and_create_playlists.py')
        remote_cmd = f'cd {script_path} && python3 {remote_script} --all-date-folders'
        if dry_run:
            remote_cmd += ' --dry-run'
        
        print(f"\n📡 Connecting to iMac ({hostname})...")
        print(f"   Running: {remote_script}")
        
        # Use SSH password from environment variable if available, otherwise use SSH keys
        password = os.environ.get('SSH_PASSWORD', '')
        
        # Execute remote command using ssh_connection module
        success, exit_code, error = ssh_connection.execute_remote_command(
            hostname=hostname,
            username=username,
            remote_cmd=remote_cmd,
            password=password if password else None,
            timeout=600
        )
        
        if success:
            print("\n✅ iMac import completed successfully!")
            return True
        else:
            if error:
                print(f"\n⚠️  iMac import error: {error}")
            else:
                print(f"\n⚠️  iMac import completed with exit code {exit_code}")
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
        # Only use files from current session (within last 60 minutes)
        workarea_dir = os.path.join(os.path.dirname(__file__), '_workarea')
        urls_dir = os.path.join(workarea_dir, 'urls')
        
        file_type = 'mp3' if download_type == 'audio' else 'mp4'
        latest_file = find_latest_timestamped_file(urls_dir, file_type=file_type, max_age_minutes=60)
        
        if latest_file:
            print(f"📄 Using latest timestamped file: {os.path.basename(latest_file)}")
            cmd.extend(['--file', latest_file])
            urls_file = latest_file  # Store for log file generation
        else:
            # No recent file found - skip download for this type
            print(f"⏭️  No recent {file_type.upper()} URLs file found - skipping {download_type_name} download")
            return True, None  # Return success but no log file
    
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
  python trigger_download.py                    # Full workflow (default settings, SSH mode)
  python trigger_download.py --ssh local        # Run iMac import locally instead of SSH
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
        help='Skip syncing files to iCloud Drive (deprecated - no longer used)'
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
    
    parser.add_argument(
        '--skip-import-imac',
        action='store_true',
        help='Skip importing to Music.app on iMac'
    )
    
    parser.add_argument(
        '--ssh',
        type=str,
        choices=['local', 'ssh'],
        default='ssh',
        help='Execution mode for iMac import: "local" to run locally, "ssh" to run via SSH (default: ssh)'
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
    
    # Download MP4s if we have MP4 URLs (only if actually synced, not just because MP3s exist)
    if synced_files.get('mp4') or (args.file and 'mp4' in os.path.basename(args.file).lower()):
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
    
    # Step 2.5: Import to Music.app on iMac (via SSH or locally)
    imac_import_success = None
    if not args.skip_import_imac and download_success and log_files:
        imac_import_success = run_import_on_imac(
            log_files=log_files,
            dry_run=False,
            ssh_mode=args.ssh
        )
    elif args.skip_import_imac:
        print("\n⏭️  Skipping iMac import step (--skip-import-imac flag used)")
    elif not download_success:
        print("\n⏭️  Skipping iMac import step (downloads not completed)")
    elif not log_files or not any(os.path.exists(f) for f in log_files if f):
        print("\n⏭️  Skipping iMac import step (no log files)")
    
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
    
    if imac_import_success is not None:
        if imac_import_success:
            print("✅ iMac Import: Completed")
        else:
            print("⚠️  iMac Import: Completed with warnings")
    elif not args.skip_import_imac:
        print("⏭️  iMac Import: Skipped (not enabled or no MP3 files)")
    
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

