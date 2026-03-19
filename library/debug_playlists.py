#!/usr/bin/env python3
"""
Debug script to check why playlists aren't being created.
This will help identify issues with track paths and folder names.
"""

import subprocess
import sys

def check_tracks_with_marker(base_marker="/Zen/mp3/"):
    """Check if any tracks in Music.app have the base marker in their path."""
    escaped_marker = base_marker.replace('\\', '\\\\').replace('"', '\\"')
    
    apple_script = f'''
    tell application "Music"
        set baseMarker to "{escaped_marker}"
        set libPlaylist to playlist "Library"
        
        set matchingTracks to {{}}
        set totalTracks to count of tracks of libPlaylist
        
        repeat with t in tracks of libPlaylist
            try
                set locAlias to location of t
                if locAlias is not missing value then
                    set p to POSIX path of locAlias
                    
                    if p contains baseMarker then
                        set end of matchingTracks to p
                    end if
                end if
            on error
            end try
        end repeat
        
        return "total:" & totalTracks & "|matching:" & (count of matchingTracks) & "|sample:" & (item 1 of matchingTracks as string)
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ AppleScript error: {result.stderr.strip()}")
            return None
        
        output = result.stdout.strip()
        return output
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def check_folder_names(base_marker="/Zen/mp3/"):
    """Check what folder names are found in track paths."""
    escaped_marker = base_marker.replace('\\', '\\\\').replace('"', '\\"')
    
    apple_script = f'''
    tell application "Music"
        set baseMarker to "{escaped_marker}"
        set libPlaylist to playlist "Library"
        
        set folderNames to {{}}
        
        repeat with t in tracks of libPlaylist
            try
                set locAlias to location of t
                if locAlias is not missing value then
                    set p to POSIX path of locAlias
                    
                    if p contains baseMarker then
                        set AppleScript's text item delimiters to baseMarker
                        set tailPart to text item 2 of p
                        set AppleScript's text item delimiters to "/"
                        
                        set batchName to text item 1 of tailPart
                        set AppleScript's text item delimiters to ""
                        
                        if batchName is not in folderNames then
                            set end of folderNames to batchName
                        end if
                    end if
                end if
            on error
            end try
        end repeat
        
        set AppleScript's text item delimiters to ", "
        return folderNames as string
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ AppleScript error: {result.stderr.strip()}")
            return None
        
        output = result.stdout.strip()
        return output
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    print("\n" + "=" * 70)
    print("   PLAYLIST CREATION DEBUG")
    print("=" * 70)
    
    base_marker = "/Zen/mp3/"
    print(f"\n📁 Checking base marker: {base_marker}")
    
    # Check 1: Do tracks exist with this marker?
    print("\n🔍 Step 1: Checking if any tracks match the base marker...")
    result = check_tracks_with_marker(base_marker)
    if result:
        parts = result.split("|")
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                print(f"   {key}: {value}")
    else:
        print("   ❌ Could not check tracks")
    
    # Check 2: What folder names are found?
    print("\n🔍 Step 2: Checking folder names in track paths...")
    folder_names = check_folder_names(base_marker)
    if folder_names:
        names = [n.strip() for n in folder_names.split(",") if n.strip()]
        print(f"   Found {len(names)} unique folder name(s):")
        for name in names[:10]:  # Show first 10
            print(f"      - {name}")
            # Check if it matches expected format
            if len(name) == 11 and name[8] == '_':
                print(f"        ✅ Matches YYYYMMDD_## format")
            else:
                print(f"        ⚠️  Does NOT match YYYYMMDD_## format (length: {len(name)})")
        if len(names) > 10:
            print(f"      ... and {len(names) - 10} more")
    else:
        print("   ⚠️  No folder names found (no tracks match the base marker)")
    
    # Check 3: Sample track path
    print("\n🔍 Step 3: Sample track path...")
    if result and "sample:" in result:
        sample = result.split("sample:")[1].strip()
        print(f"   {sample}")
        if base_marker in sample:
            print(f"   ✅ Contains base marker")
        else:
            print(f"   ❌ Does NOT contain base marker")
    
    print("\n" + "=" * 70)
    print("\n💡 TROUBLESHOOTING:")
    print("   1. If 'matching: 0', no tracks have paths containing '/Zen/mp3/'")
    print("   2. Check if your tracks are actually imported to Music.app")
    print("   3. Check if track paths use different casing (e.g., '/zen/MP3/' vs '/Zen/mp3/')")
    print("   4. Folder names must be exactly 11 characters: YYYYMMDD_##")
    print("   5. Try running: python3 create_playlist.py --dry-run --verbose")
    print()


if __name__ == "__main__":
    main()

