#!/usr/bin/env python3
"""
Import MP3s to Music.app
Takes a directory path, imports all MP3s, and verifies they were imported
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def find_mp3_files_via_finder(directory_path):
    """Find MP3 files using Finder/AppleScript when direct access is denied."""
    # Escape the directory path for AppleScript
    escaped_dir = str(Path(directory_path).absolute()).replace('\\', '\\\\').replace('"', '\\"')
    
    apple_script = f'''
    tell application "Finder"
        try
            set folderPath to POSIX file "{escaped_dir}"
            set folderRef to folder folderPath
            set mp3Files to every file of folderRef whose name ends with ".mp3" or name ends with ".MP3"
            
            set filePaths to {{}}
            set fileNames to {{}}
            
            repeat with fileRef in mp3Files
                set filePath to POSIX path of (fileRef as alias)
                set fileName to name of fileRef
                set end of filePaths to filePath
                set end of fileNames to fileName
            end repeat
            
            -- Build comma-separated strings for easier parsing
            set pathsStr to ""
            set namesStr to ""
            set itemCount to count of filePaths
            
            if itemCount > 0 then
                repeat with i from 1 to itemCount
                    set pathsStr to pathsStr & item i of filePaths
                    set namesStr to namesStr & item i of fileNames
                    if i < itemCount then
                        set pathsStr to pathsStr & ":::"
                        set namesStr to namesStr & ":::"
                    end if
                end repeat
            end if
            
            return pathsStr & "|||" & namesStr
        on error errMsg
            return "ERROR:" & errMsg
        end try
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return None, f"Error discovering files: {result.stderr.strip()}"
        
        output = result.stdout.strip()
        
        if output.startswith("ERROR:"):
            return None, output.replace("ERROR:", "").strip()
        
        if "|||" not in output:
            return None, "No MP3 files found in directory"
        
        # Parse the results
        file_paths_str, file_names_str = output.split("|||", 1)
        
        # Split by ::: delimiter
        file_paths = [p.strip() for p in file_paths_str.split(":::") if p.strip()]
        file_names = [n.strip() for n in file_names_str.split(":::") if n.strip()]
        
        if not file_paths or not file_names:
            return None, "No MP3 files found in directory"
        
        if len(file_paths) != len(file_names):
            return None, f"Mismatch: found {len(file_paths)} paths but {len(file_names)} names"
        
        return (file_paths, file_names), None
        
    except subprocess.TimeoutExpired:
        return None, "Timeout discovering files"
    except Exception as e:
        return None, f"Error discovering files: {str(e)}"


def find_mp3_files(directory_path):
    """Find all MP3 files in the directory and return their paths and names."""
    directory = Path(directory_path)
    
    if not directory.exists():
        return None, f"Directory not found: {directory_path}"
    
    if not directory.is_dir():
        return None, f"Path is not a directory: {directory_path}"
    
    # Check if we can actually read the directory contents
    # This will catch permission errors with iCloud Drive
    try:
        # Try to list directory contents - this will raise PermissionError if we can't access
        list(directory.iterdir())
    except (PermissionError, OSError):
        # If permission denied (common with iCloud Drive), use AppleScript/Finder
        print("   ⚠️  Permission denied accessing directory, using Finder to discover files...")
        return find_mp3_files_via_finder(directory_path)
    
    # Try to find MP3 files using direct file system access
    try:
        mp3_files = list(directory.glob("*.mp3")) + list(directory.glob("*.MP3"))
        
        if not mp3_files:
            # If no files found, double-check with Finder (might be iCloud sync issue)
            print("   ⚠️  No MP3s found via direct access, checking with Finder...")
            finder_result = find_mp3_files_via_finder(directory_path)
            if finder_result[0] is not None:
                return finder_result
            return None, "No MP3 files found in directory"
        
        # Get absolute paths and file names
        file_paths = [str(f.absolute()) for f in mp3_files]
        file_names = [f.name for f in mp3_files]
        
        return (file_paths, file_names), None
        
    except (PermissionError, OSError) as e:
        # If permission denied during glob, use AppleScript/Finder
        print("   ⚠️  Permission denied accessing directory, using Finder to discover files...")
        return find_mp3_files_via_finder(directory_path)


def check_files_already_imported(file_paths):
    """Check which files are already in Music.app library by file path.
    Returns: set of indices of files that are already imported."""
    if not file_paths:
        return set()
    
    print("   🔍 Checking for existing files in Music.app...")
    
    # Escape paths for AppleScript
    escaped_paths = [path.replace('\\', '\\\\').replace('"', '\\"') for path in file_paths]
    
    # Build AppleScript to check each file path by location
    # We check by file location (POSIX path) which is the most reliable way
    check_statements = []
    for i, path in enumerate(escaped_paths):
        check_statements.append(f'''
        try
            set filePath to "{path}"
            set fileAlias to POSIX file filePath as alias
            set foundTrack to some track of library playlist 1 whose location is fileAlias
            set end of results to "{i}:found"
        on error
            set end of results to "{i}:missing"
        end try''')
    
    apple_script = f'''
    tell application "Music"
        set results to {{}}
        {"".join(check_statements)}
        return results as string
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
            print(f"   ⚠️  Warning: Could not check for existing files: {result.stderr.strip()}")
            return set()  # If check fails, assume none are imported (safer to skip check than create duplicates)
        
        output = result.stdout.strip()
        already_imported_indices = set()
        
        # Parse results - AppleScript returns list as string like "{0:found, 1:missing, ...}"
        if output and output != '{}':
            output = output.strip('{}')
            for item in output.split(', '):
                item = item.strip()
                if ':found' in item:
                    try:
                        idx = int(item.split(':')[0])
                        already_imported_indices.add(idx)
                    except ValueError:
                        pass
        
        return already_imported_indices
        
    except subprocess.TimeoutExpired:
        print("   ⚠️  Warning: Timeout checking for existing files")
        return set()
    except Exception as e:
        print(f"   ⚠️  Warning: Could not check for existing files: {e}")
        return set()  # If check fails, assume none are imported


def import_files_to_music(file_paths):
    """Import MP3 files to Music.app library using AppleScript."""
    if not file_paths:
        return False, "No files to import"
    
    # Check which files are already imported
    already_imported_indices = check_files_already_imported(file_paths)
    
    if already_imported_indices:
        print(f"   ⏭️  Skipping {len(already_imported_indices)} file(s) already in library")
    
    # Filter out already imported files
    files_to_import = [path for i, path in enumerate(file_paths) if i not in already_imported_indices]
    
    if not files_to_import:
        skipped_count = len(already_imported_indices)
        return True, f"imported:0|failed:0|failedFiles:{{}}|skipped:{skipped_count}"
    
    print(f"   📥 Importing {len(files_to_import)} new file(s)...")
    
    # Escape paths for AppleScript
    escaped_paths = [path.replace('\\', '\\\\').replace('"', '\\"') for path in files_to_import]
    file_paths_script = ', '.join([f'POSIX file "{path}"' for path in escaped_paths])
    
    apple_script = f'''
    tell application "Music"
        activate
        
        set importedFiles to {{{file_paths_script}}}
        set importedCount to 0
        set failedCount to 0
        set failedFiles to {{}}
        
        repeat with fileRef in importedFiles
            try
                add fileRef to library playlist 1
                set importedCount to importedCount + 1
                delay 0.5
            on error errMsg
                set failedCount to failedCount + 1
                try
                    set fileName to name of (fileRef as alias)
                    set end of failedFiles to fileName
                on error
                    set end of failedFiles to "unknown file"
                end try
            end try
        end repeat
        
        return "imported:" & importedCount & "|failed:" & failedCount & "|failedFiles:" & (failedFiles as string)
    end tell
    '''
        
    try:
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, f"AppleScript error: {error_msg}"
        
        output = result.stdout.strip()
        # Add skipped count to output if any files were skipped
        skipped_count = len(already_imported_indices)
        if skipped_count > 0:
            output += f"|skipped:{skipped_count}"
        return True, output
        
    except subprocess.TimeoutExpired:
        return False, "Timeout: Music.app took too long to respond"
    except Exception as e:
        return False, f"Error executing AppleScript: {str(e)}"


def verify_imported_files(file_names):
    """Verify which files were successfully imported to Music.app."""
    # Escape file names for AppleScript
    escaped_names = [name.replace('"', '\\"') for name in file_names]
    
    # Build AppleScript to check each file
    check_statements = []
    for name in escaped_names:
        check_statements.append(f'''
        try
            set foundTrack to some track of library playlist 1 whose name is "{name}"
            set end of results to "{name}:found"
        on error
            -- Try without extension
            set nameWithoutExt to "{name}"
            if nameWithoutExt ends with ".mp3" then
                set nameWithoutExt to text 1 thru -5 of nameWithoutExt
            end if
            try
                set foundTrack to some track of library playlist 1 whose name contains nameWithoutExt
                set end of results to "{name}:found"
            on error
                set end of results to "{name}:missing"
            end try
        end try''')
    
    apple_script = f'''
    tell application "Music"
        set results to {{}}
        {"".join(check_statements)}
        return results as string
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
            return None, f"Error verifying files: {result.stderr.strip()}"
        
        output = result.stdout.strip()
        return output, None
        
    except Exception as e:
        return None, f"Error verifying files: {str(e)}"


def parse_import_result(result_string):
    """Parse the import result string from AppleScript."""
    imported_count = 0
    failed_count = 0
    skipped_count = 0
    failed_files = []
    
    try:
        parts = result_string.split('|')
        for part in parts:
            if part.startswith('imported:'):
                imported_count = int(part.split(':')[1])
            elif part.startswith('failed:'):
                failed_count = int(part.split(':')[1])
            elif part.startswith('skipped:'):
                skipped_count = int(part.split(':')[1])
            elif part.startswith('failedFiles:'):
                failed_list = part.split(':', 1)[1]
                # Parse AppleScript list format: {file1, file2, ...}
                if failed_list and failed_list != '{}':
                    failed_list = failed_list.strip('{}')
                    failed_files = [f.strip().strip('"') for f in failed_list.split(',')]
    except Exception as e:
        pass  # Return defaults if parsing fails
    
    return imported_count, failed_count, failed_files, skipped_count


def print_report(file_names, imported_count, failed_count, failed_files, verification_results, skipped_count=0):
    """Print a detailed report of the import process."""
    print("\n" + "=" * 70)
    print("   IMPORT REPORT")
    print("=" * 70)
    
    print(f"\n📊 SUMMARY")
    print(f"   Total MP3 files found: {len(file_names)}")
    print(f"   Successfully imported: {imported_count}")
    if skipped_count > 0:
        print(f"   Skipped (already in library): {skipped_count}")
    print(f"   Failed to import: {failed_count}")
    
    verified_found = 0
    verified_missing = 0
    if verification_results:
        verified_found = sum(1 for r in verification_results if ':found' in r)
        verified_missing = sum(1 for r in verification_results if ':missing' in r)
        print(f"   Verified in library: {verified_found}")
        print(f"   Missing from library: {verified_missing}")
    
    if failed_files:
        print(f"\n❌ FAILED FILES:")
        for file_name in failed_files:
            print(f"   - {file_name}")
    
    if verification_results:
        missing_files = [r.split(':')[0] for r in verification_results if ':missing' in r]
        if missing_files:
            print(f"\n⚠️  VERIFICATION - MISSING FROM LIBRARY:")
            for file_name in missing_files:
                print(f"   - {file_name}")
    
    print("\n" + "=" * 70)
    
    # Overall status
    if failed_count == 0 and (not verification_results or verified_missing == 0):
        print("✅ All files imported successfully!")
    elif failed_count > 0 or (verification_results and verified_missing > 0):
        print("⚠️  Some files may not have been imported. Check the details above.")
    else:
        print("✅ Import completed")


def main():
    parser = argparse.ArgumentParser(
        description="Import MP3s from a directory into Music.app",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python import_to_music.py ~/Music/MyAlbum
  python import_to_music.py /path/to/mp3s
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing MP3 files to import'
    )
    
    parser.add_argument(
        '--no-verify',
        action='store_true',
        help='Skip verification step after import'
    )
    
    args = parser.parse_args()
    
    # Expand user home directory if path starts with ~
    directory_path = os.path.expanduser(args.directory)
    
    print("\n" + "=" * 70)
    print("   IMPORT MP3s TO MUSIC.APP")
    print("=" * 70)
    print(f"\n📁 Directory: {directory_path}")
    
    # Step 1: Find MP3 files
    print("\n🔍 Analyzing directory...")
    file_data, error = find_mp3_files(directory_path)
    
    if error:
        print(f"\n❌ Error: {error}")
        sys.exit(1)
    
    file_paths, file_names = file_data
    print(f"   Found {len(file_names)} MP3 file(s)")
    print("   Files to import:")
    for name in file_names:
        print(f"      - {name}")
    
    # Step 2: Import files
    print(f"\n📥 Importing {len(file_paths)} file(s) to Music.app...")
    success, result = import_files_to_music(file_paths)
    
    if not success:
        print(f"\n❌ Error during import: {result}")
        sys.exit(1)
    
    # Parse import results
    imported_count, failed_count, failed_files, skipped_count = parse_import_result(result)
    
    # Step 3: Verify imported files
    verification_results = None
    if not args.no_verify:
        print("\n🔍 Verifying imported files...")
        # Wait a bit for Music.app to finish processing
        import time
        time.sleep(2)
        
        verify_output, verify_error = verify_imported_files(file_names)
        if verify_error:
            print(f"   ⚠️  Verification error: {verify_error}")
        else:
            # Parse verification results (AppleScript returns list as string like "{item1, item2, ...}")
            if verify_output:
                # Remove curly braces and split by comma
                verify_output = verify_output.strip('{}')
                verification_results = [r.strip().strip('"') for r in verify_output.split(',') if r.strip()]
    
    # Step 4: Print report
    print_report(file_names, imported_count, failed_count, failed_files, verification_results, skipped_count)


if __name__ == "__main__":
    main()
