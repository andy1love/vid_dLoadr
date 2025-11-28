#!/usr/bin/env python3
"""
Import MP3s and Create Playlists
Runs import_to_music.py and create_playlist.py sequentially.
Can be executed manually on iMac or via SSH from download machine.
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path


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


def get_default_mp3_directory():
    """Get default MP3 directory from config.json"""
    config = load_config()
    download_dir = config.get('download_dir_mp3', None)
    
    if download_dir:
        return os.path.expanduser(download_dir)
    
    # Fallback to default
    return os.path.join(os.path.expanduser("~"), "Library", "Mobile Documents", "com~apple~CloudDocs", "Zen", "MP3")


def run_import_to_music(directory_path, no_verify=False):
    """Run import_to_music.py on the specified directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, 'import_to_music.py')
    
    if not os.path.exists(script_path):
        return False, f"Could not find import_to_music.py at {script_path}"
    
    cmd = [sys.executable, script_path, directory_path]
    if no_verify:
        cmd.append('--no-verify')
    
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=False,
            text=True
        )
        return result.returncode == 0, None
    except Exception as e:
        return False, str(e)


def run_create_playlist(base_marker="/Zen/mp3/", dry_run=False, verbose=False):
    """Run create_playlist.py"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, 'create_playlist.py')
    
    if not os.path.exists(script_path):
        return False, f"Could not find create_playlist.py at {script_path}"
    
    cmd = [sys.executable, script_path, '--base-marker', base_marker]
    if dry_run:
        cmd.append('--dry-run')
    if verbose:
        cmd.append('--verbose')
    
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=False,
            text=True
        )
        return result.returncode == 0, None
    except Exception as e:
        return False, str(e)


def find_date_folders(base_directory):
    """Find all date folders (YYYYMMDD_## format) in the base directory"""
    base_path = Path(base_directory)
    if not base_path.exists():
        return []
    
    date_folders = []
    try:
        for item in base_path.iterdir():
            if item.is_dir():
                folder_name = item.name
                # Check if it matches YYYYMMDD_## format
                if len(folder_name) >= 11 and folder_name[8] == '_':
                    date_part = folder_name[:8]
                    if date_part.isdigit():
                        date_folders.append(str(item))
    except (PermissionError, OSError):
        # If we can't read the directory, return empty list
        pass
    
    return sorted(date_folders)


def main():
    parser = argparse.ArgumentParser(
        description="Import MP3s to Music.app and create playlists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script runs two steps sequentially:
1. Import MP3s from directory to Music.app (import_to_music.py)
2. Create playlists based on folder structure (create_playlist.py)

Examples:
  python import_and_create_playlists.py ~/Music/MyAlbum
  python import_and_create_playlists.py --all-date-folders
  python import_and_create_playlists.py --directory /path/to/mp3s --no-verify
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        nargs='?',
        default=None,
        help='Directory containing MP3 files to import (default: from config.json download_dir_mp3)'
    )
    
    parser.add_argument(
        '--all-date-folders',
        action='store_true',
        help='Process all date folders (YYYYMMDD_##) in the base MP3 directory'
    )
    
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip verification step after import'
    )
    
    parser.add_argument(
        '--skip-playlist',
        action='store_true',
        help='Skip playlist creation step'
    )
    
    parser.add_argument(
        '--base-marker',
        type=str,
        default="/Zen/mp3/",
        help='Base marker for playlist creation (default: "/Zen/mp3/")'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run playlist creation in dry-run mode (preview only)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress information'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("   IMPORT MP3s AND CREATE PLAYLISTS")
    print("=" * 70)
    
    # Determine directory to process
    directories_to_process = []
    
    if args.all_date_folders:
        # Process all date folders
        base_dir = get_default_mp3_directory()
        print(f"\n📁 Base directory: {base_dir}")
        directories_to_process = find_date_folders(base_dir)
        
        if not directories_to_process:
            print("   ⚠️  No date folders found")
            sys.exit(1)
        
        print(f"   Found {len(directories_to_process)} date folder(s) to process")
    elif args.directory:
        # Use specified directory
        directory_path = os.path.expanduser(args.directory)
        directories_to_process = [directory_path]
    else:
        # Use default from config
        default_dir = get_default_mp3_directory()
        directories_to_process = [default_dir]
        print(f"\n📁 Using default directory: {default_dir}")
    
    # Step 1: Import MP3s
    import_success = True
    import_errors = []
    
    for directory in directories_to_process:
        print(f"\n{'=' * 70}")
        print(f"   IMPORTING: {os.path.basename(directory)}")
        print("=" * 70)
        
        success, error = run_import_to_music(directory, no_verify=args.no_verify)
        
        if not success:
            import_success = False
            if error:
                import_errors.append(f"{directory}: {error}")
            else:
                import_errors.append(f"{directory}: Import failed")
        else:
            print(f"\n✅ Successfully imported from: {directory}")
    
    # Step 2: Create playlists (if import was successful or we're continuing anyway)
    playlist_success = None
    
    if not args.skip_playlist:
        print(f"\n{'=' * 70}")
        print("   CREATING PLAYLISTS")
        print("=" * 70)
        
        success, error = run_create_playlist(
            base_marker=args.base_marker,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        playlist_success = success
        
        if not success:
            if error:
                print(f"\n❌ Playlist creation error: {error}")
            else:
                print(f"\n❌ Playlist creation failed")
        else:
            print(f"\n✅ Playlist creation completed")
    else:
        print("\n⏭️  Skipping playlist creation (--skip-playlist flag used)")
    
    # Final summary
    print("\n" + "=" * 70)
    print("   FINAL SUMMARY")
    print("=" * 70)
    
    if import_success:
        print("✅ Import: Completed")
    else:
        print("⚠️  Import: Completed with errors")
        for error in import_errors:
            print(f"   - {error}")
    
    if playlist_success is not None:
        if playlist_success:
            print("✅ Playlist Creation: Completed")
        else:
            print("⚠️  Playlist Creation: Failed")
    elif args.skip_playlist:
        print("⏭️  Playlist Creation: Skipped")
    
    if import_success and (playlist_success is None or playlist_success):
        print("\n🎉 All done!")
        sys.exit(0)
    else:
        print("\n⚠️  Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()

