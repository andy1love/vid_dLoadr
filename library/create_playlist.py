#!/usr/bin/env python3
"""
Create playlists in Music.app based on iCloud batch folders.

Groups tracks into playlists based on their folder structure:
  .../Zen/mp3/YYYYMMDD_##/TrackName.mp3

Creates playlists named "YYYYMMDD_##" and adds tracks to them.
"""

import subprocess
import argparse
import sys


def create_playlists_from_batch_folders(base_marker="/Zen/mp3/", dry_run=False, verbose=False):
    """Create playlists based on batch folder names in track paths.
    
    Args:
        base_marker: Path marker to identify tracks (default: "/Zen/mp3/")
        dry_run: If True, only preview what would be done
        verbose: If True, print detailed progress
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Escape the base marker for AppleScript
    escaped_marker = base_marker.replace('\\', '\\\\').replace('"', '\\"')
    
    if dry_run:
        apple_script = f'''
        tell application "Music"
            set baseMarker to "{escaped_marker}"
            set libPlaylist to playlist "Library"
            
            set processedCount to 0
            set playlistCount to 0
            set playlistsCreated to {{}}
            set tracksByPlaylist to {{}}
            
            repeat with t in tracks of libPlaylist
                try
                    set locAlias to location of t
                    if locAlias is not missing value then
                        set p to POSIX path of locAlias
                        
                        if p contains baseMarker then
                            set processedCount to processedCount + 1
                            
                            set AppleScript's text item delimiters to baseMarker
                            set tailPart to text item 2 of p
                            set AppleScript's text item delimiters to "/"
                            
                            set batchName to text item 1 of tailPart
                            set AppleScript's text item delimiters to ""
                            
                            if (count of batchName) is 11 and character 9 of batchName is "_" then
                                set playlistName to batchName
                                
                                -- Check if playlist exists
                                set playlistExists to false
                                repeat with pl in user playlists
                                    if name of pl is playlistName then
                                        set playlistExists to true
                                        exit repeat
                                    end if
                                end repeat
                                
                                if not playlistExists then
                                    set playlistCount to playlistCount + 1
                                    set end of playlistsCreated to playlistName
                                end if
                                
                                -- Track which tracks would go to which playlist
                                if tracksByPlaylist does not contain playlistName then
                                    set tracksByPlaylist to tracksByPlaylist & {{playlistName}}
                                end if
                            end if
                        end if
                    end if
                end try
            end repeat
            
            set AppleScript's text item delimiters to ""
            
            return "processed:" & processedCount & "|playlists:" & playlistCount & "|playlistNames:" & (playlistsCreated as string)
        end tell
        '''
    else:
        apple_script = f'''
        tell application "Music"
            activate
            set baseMarker to "{escaped_marker}"
            set libPlaylist to playlist "Library"
            
            set processedCount to 0
            set addedCount to 0
            set skippedCount to 0
            set playlistsCreated to 0
            set playlistsFound to 0
            set errorCount to 0
            
            repeat with t in tracks of libPlaylist
                try
                    set locAlias to location of t
                    if locAlias is not missing value then
                        set p to POSIX path of locAlias
                        
                        if p contains baseMarker then
                            set processedCount to processedCount + 1
                            
                            set AppleScript's text item delimiters to baseMarker
                            set tailPart to text item 2 of p
                            set AppleScript's text item delimiters to "/"
                            
                            set batchName to text item 1 of tailPart
                            set AppleScript's text item delimiters to ""
                            
                            if (count of batchName) is 11 and character 9 of batchName is "_" then
                                set playlistName to batchName
                                set targetPlaylist to missing value
                                
                                -- Find existing playlist
                                repeat with pl in user playlists
                                    if name of pl is playlistName then
                                        set targetPlaylist to pl
                                        set playlistsFound to playlistsFound + 1
                                        exit repeat
                                    end if
                                end repeat
                                
                                -- Create playlist if it doesn't exist
                                if targetPlaylist is missing value then
                                    set targetPlaylist to make new user playlist with properties {{name:playlistName}}
                                    set playlistsCreated to playlistsCreated + 1
                                end if
                                
                                -- Check if track is already in playlist by comparing file locations
                                set alreadyInPlaylist to false
                                set currentTrackLocation to p
                                
                                -- Get all track locations from the playlist first
                                try
                                    set playlistTracks to tracks of targetPlaylist
                                    set trackCountBefore to count of playlistTracks
                                    
                                    -- Check each track in playlist for duplicate
                                    repeat with pt in playlistTracks
                                        try
                                            set ptLocationAlias to location of pt
                                            if ptLocationAlias is not missing value then
                                                set ptLocation to POSIX path of ptLocationAlias
                                                -- Direct string comparison of POSIX paths
                                                if ptLocation is currentTrackLocation then
                                                    set alreadyInPlaylist to true
                                                    exit repeat
                                                end if
                                            end if
                                        on error
                                            -- Try persistent ID comparison as fallback
                                            try
                                                if persistent ID of pt is persistent ID of t then
                                                    set alreadyInPlaylist to true
                                                    exit repeat
                                                end if
                                            on error
                                            end try
                                        end try
                                    end repeat
                                on error checkErr
                                    -- If check fails, assume not duplicate (will be caught on add)
                                    set alreadyInPlaylist to false
                                end try
                                
                                -- Only add if not already in playlist
                                if not alreadyInPlaylist then
                                    try
                                        -- Add track to playlist
                                        duplicate t to targetPlaylist
                                        
                                        -- Verify it was actually added (not a duplicate)
                                        delay 0.2
                                        set playlistTracksAfter to tracks of targetPlaylist
                                        set trackCountAfter to count of playlistTracksAfter
                                        
                                        if trackCountAfter is trackCountBefore then
                                            -- Count didn't increase, might be duplicate
                                            set alreadyInPlaylist to false
                                            repeat with pt in playlistTracksAfter
                                                try
                                                    set ptLocationAlias to location of pt
                                                    if ptLocationAlias is not missing value then
                                                        set ptLocation to POSIX path of ptLocationAlias
                                                        if ptLocation is currentTrackLocation then
                                                            set alreadyInPlaylist to true
                                                            exit repeat
                                                        end if
                                                    end if
                                                on error
                                                end try
                                            end repeat
                                            
                                            if alreadyInPlaylist then
                                                -- Was already there, count as skipped
                                                set skippedCount to skippedCount + 1
                                            else
                                                -- Something else went wrong
                                                set errorCount to errorCount + 1
                                            end if
                                        else
                                            -- Successfully added
                                            set addedCount to addedCount + 1
                                        end if
                                    on error addErr
                                        -- Add failed, check if it's because it's already there
                                        set alreadyInPlaylist to false
                                        try
                                            set playlistTracks to tracks of targetPlaylist
                                            repeat with pt in playlistTracks
                                                try
                                                    set ptLocationAlias to location of pt
                                                    if ptLocationAlias is not missing value then
                                                        set ptLocation to POSIX path of ptLocationAlias
                                                        if ptLocation is currentTrackLocation then
                                                            set alreadyInPlaylist to true
                                                            set skippedCount to skippedCount + 1
                                                            exit repeat
                                                        end if
                                                    end if
                                                on error
                                                end try
                                            end repeat
                                        end try
                                        if not alreadyInPlaylist then
                                            set errorCount to errorCount + 1
                                        end if
                                    end try
                                else
                                    -- Already in playlist, skip
                                    set skippedCount to skippedCount + 1
                                end if
                            end if
                        end if
                    end if
                on error errMsg
                    set errorCount to errorCount + 1
                end try
            end repeat
            
            set AppleScript's text item delimiters to ""
            
            return "processed:" & processedCount & "|added:" & addedCount & "|skipped:" & skippedCount & "|created:" & playlistsCreated & "|found:" & playlistsFound & "|errors:" & errorCount
        end tell
        '''
    
    try:
        if verbose:
            print("🔧 Executing AppleScript...")
        
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout for large libraries
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, f"AppleScript error: {error_msg}"
        
        output = result.stdout.strip()
        return True, output
        
    except subprocess.TimeoutExpired:
        return False, "Timeout: Music.app took too long to respond"
    except Exception as e:
        return False, f"Error executing AppleScript: {str(e)}"


def parse_result(result_string):
    """Parse the result string from AppleScript."""
    stats = {}
    try:
        parts = result_string.split('|')
        for part in parts:
            if ':' in part:
                key, value = part.split(':', 1)
                try:
                    stats[key] = int(value)
                except ValueError:
                    stats[key] = value
    except Exception:
        pass
    return stats


def print_report(stats, dry_run=False):
    """Print a detailed report of the playlist creation process."""
    print("\n" + "=" * 70)
    if dry_run:
        print("   PLAYLIST CREATION PREVIEW")
    else:
        print("   PLAYLIST CREATION REPORT")
    print("=" * 70)
    
    if dry_run:
        print(f"\n📊 SUMMARY")
        print(f"   Tracks processed: {stats.get('processed', 0)}")
        print(f"   Playlists that would be created: {stats.get('playlists', 0)}")
        
        if 'playlistNames' in stats:
            playlist_names = stats['playlistNames']
            if isinstance(playlist_names, str):
                # Parse AppleScript list format
                playlist_names = playlist_names.strip('{}')
                if playlist_names:
                    names = [n.strip().strip('"') for n in playlist_names.split(',') if n.strip()]
                    if names:
                        print(f"\n📋 Playlists that would be created:")
                        for name in names:
                            print(f"   - {name}")
        
        print("\n" + "=" * 70)
        print("🔍 This was a dry run - no changes were made")
    else:
        print(f"\n📊 SUMMARY")
        print(f"   Tracks processed: {stats.get('processed', 0)}")
        print(f"   Tracks added to playlists: {stats.get('added', 0)}")
        print(f"   Tracks skipped (already in playlist): {stats.get('skipped', 0)}")
        print(f"   Playlists created: {stats.get('created', 0)}")
        print(f"   Playlists found (existing): {stats.get('found', 0)}")
        if stats.get('errors', 0) > 0:
            print(f"   Errors encountered: {stats.get('errors', 0)}")
        
        print("\n" + "=" * 70)
        
        total_added = stats.get('added', 0)
        total_created = stats.get('created', 0)
        
        if total_added > 0 or total_created > 0:
            print("✅ Playlist creation completed successfully!")
        else:
            print("ℹ️  No changes were made (all tracks may already be in playlists)")


def main():
    parser = argparse.ArgumentParser(
        description="Create playlists in Music.app based on batch folder names",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script groups Music.app tracks into playlists based on their folder structure.
Tracks under .../Zen/mp3/YYYYMMDD_##/ will be added to playlists named "YYYYMMDD_##".

Examples:
  python create_playlist.py
  python create_playlist.py --base-marker "/Music/mp3/"
  python create_playlist.py --dry-run
        """
    )
    
    parser.add_argument(
        '--base-marker',
        type=str,
        default="/Zen/mp3/",
        help='Path marker to identify batch folders (default: "/Zen/mp3/")'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be done without making changes'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed progress information'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("   CREATE PLAYLISTS FROM BATCH FOLDERS")
    print("=" * 70)
    print(f"\n📁 Base marker: {args.base_marker}")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    # Create playlists
    print("\n🔄 Processing tracks...")
    success, result = create_playlists_from_batch_folders(
        base_marker=args.base_marker,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    if not success:
        print(f"\n❌ Error: {result}")
        sys.exit(1)
    
    # Parse and display results
    stats = parse_result(result)
    print_report(stats, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

