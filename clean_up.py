#!/usr/bin/env python3
"""
Clean Up Script
Verifies successful downloads and updates iCloud Notes:
- Removes successfully downloaded URLs from note
- Moves failed URLs to ---FAILED URLS--- section
"""

import os
import sys
import csv
import argparse
import subprocess
import glob
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML"""
    def __init__(self):
        super().__init__()
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data.strip())
    
    def get_text(self):
        return '\n'.join(line for line in self.text if line)

def strip_html(html_content):
    """Strip HTML tags and extract plain text"""
    if not html_content:
        return ""
    
    if '<' in html_content and '>' in html_content:
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        return parser.get_text()
    else:
        return html_content

def get_note_content(note_title):
    """Retrieve content from an iCloud Note using AppleScript"""
    apple_script = f'''
    tell application "Notes"
        set noteContent to ""
        repeat with n in notes
            if name of n is "{note_title}" then
                set noteContent to body of n
                exit repeat
            end if
        end repeat
        return noteContent
    end tell
    '''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"❌ Error running AppleScript: {result.stderr}")
            return None
        
        content = result.stdout.strip()
        return content if content else None
        
    except Exception as e:
        print(f"❌ Error accessing Notes: {e}")
        return None

def update_note_content(note_title, new_content):
    """Update iCloud Note content using AppleScript"""
    # Use a temporary file to avoid escaping issues
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(new_content)
        temp_file = f.name
    
    try:
        # Read file content and set it in Notes
        # Use longer timeout for large notes
        apple_script = f'''
        set tempFile to POSIX file "{temp_file}"
        set fileContent to read tempFile
        tell application "Notes"
            activate
            repeat with n in notes
                if name of n is "{note_title}" then
                    set body of n to fileContent
                    exit repeat
                end if
            end repeat
        end tell
        '''
        
        result = subprocess.run(
            ['osascript', '-e', apple_script],
            capture_output=True,
            text=True,
            timeout=30  # Increased timeout for large notes
        )
        
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except:
            pass
        
        if result.returncode != 0:
            print(f"❌ Error updating note: {result.stderr}")
            if result.stdout:
                print(f"   stdout: {result.stdout[:200]}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        # Clean up temp file on timeout
        try:
            os.unlink(temp_file)
        except:
            pass
        print(f"⏱️  Note update timed out (30 seconds) - note may be very large")
        print(f"   The note update may have partially completed")
        return False
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_file)
        except:
            pass
        print(f"❌ Error updating Notes: {e}")
        return False

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
            # Instagram URLs: extract shortcode
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) >= 2:
                return path_parts[-1].rstrip('/')
        
        return None
    except:
        return None

def find_downloaded_video(video_id, download_base_dir):
    """Find downloaded MP4 file by video ID"""
    if not video_id:
        return None
    
    # Search in dated folders (YYYYMMDD format)
    today = datetime.now().strftime('%Y%m%d')
    search_patterns = [
        os.path.join(download_base_dir, today, f'*{video_id}*.mp4'),
        os.path.join(download_base_dir, '*', f'*{video_id}*.mp4'),  # Any dated folder
    ]
    
    for pattern in search_patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    
    return None

def verify_successful_download(row, download_base_dir):
    """Verify that MP4 file exists for successful download"""
    if '✅ Success' not in row.get('Status', ''):
        return False
    
    url = row.get('URL', '')
    video_id = row.get('Video ID', '')
    
    if not url or not video_id:
        return False
    
    # Try to find the downloaded file
    video_file = find_downloaded_video(video_id, download_base_dir)
    
    if video_file and os.path.exists(video_file):
        file_size = os.path.getsize(video_file)
        # Check if file is reasonable size (at least 1KB)
        if file_size > 1024:
            return True
    
    return False

def read_log_csv(log_file):
    """Read and parse the CSV log file"""
    log_entries = []
    
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                log_entries.append(row)
        
        return log_entries
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return []

def remove_url_from_text(text, url):
    """Remove a URL from text (handles both plain text and HTML)"""
    lines = text.split('\n')
    new_lines = []
    
    for line in lines:
        # Check if this line contains the URL
        if url in line:
            # Remove the URL but keep the line if it has other content
            cleaned_line = line.replace(url, '').strip()
            if cleaned_line and cleaned_line != url:
                new_lines.append(cleaned_line)
            # Otherwise skip the line entirely
        else:
            new_lines.append(line)
    
    return '\n'.join(new_lines)

def extract_urls_from_text(text):
    """Extract all URLs from text"""
    import re
    url_pattern = r'https?://[^\s<>"\']+'
    return re.findall(url_pattern, text)

def update_note_with_changes(note_title, successful_urls, failed_urls):
    """Update the iCloud Note by removing successful URLs and moving failed ones"""
    print(f"\n📝 Reading current note content...")
    note_content = get_note_content(note_title)
    
    if note_content is None:
        print(f"❌ Could not read note '{note_title}'")
        return False
    
    # Extract all URLs and their positions from the note
    import re
    url_pattern = r'https?://[^\s<>"\']+'
    
    # Get plain text for processing
    text_content = strip_html(note_content)
    
    # Find all URLs in the note
    all_urls_in_note = re.findall(url_pattern, text_content)
    
    # Remove successful URLs
    print(f"\n🗑️  Removing {len(successful_urls)} successful URL(s)...")
    for url in successful_urls:
        # Remove from HTML content
        note_content = note_content.replace(url, '')
        # Also clean up any empty divs that might result
        note_content = re.sub(r'<div>\s*</div>', '', note_content)
        note_content = re.sub(r'<div><br></div>\s*<div><br></div>', '<div><br></div>', note_content)
    
    # Handle failed URLs
    if failed_urls:
        print(f"\n⚠️  Moving {len(failed_urls)} failed URL(s) to FAILED section...")
        
        # Remove failed URLs from main content first
        for url in failed_urls:
            note_content = note_content.replace(url, '')
            # Clean up empty divs
            note_content = re.sub(r'<div>\s*</div>', '', note_content)
            note_content = re.sub(r'<div><br></div>\s*<div><br></div>', '<div><br></div>', note_content)
        
        # Check if FAILED URLS section exists
        failed_section_marker = "---FAILED URLS---"
        
        # Find the section in HTML
        if failed_section_marker not in note_content:
            # Add the section at the end
            note_content = f"{note_content}<div><br></div><div><h2>{failed_section_marker}</h2></div><div><br></div>"
        
        # Add failed URLs to FAILED section
        failed_urls_html = '<div><br></div>'.join([f'<div>{url}</div>' for url in failed_urls])
        
        # Insert failed URLs after the marker
        marker_pos = note_content.find(failed_section_marker)
        if marker_pos != -1:
            # Find the end of the marker div
            marker_end = note_content.find('</div>', marker_pos + len(failed_section_marker))
            if marker_end != -1:
                # Insert failed URLs after the marker
                note_content = (note_content[:marker_end + 6] + 
                              f'<div><br></div>{failed_urls_html}<div><br></div>' + 
                              note_content[marker_end + 6:])
    
    # Add cleanup timestamp log at the end (only if there were changes)
    cleanup_timestamp = None
    if successful_urls or failed_urls:
        cleanup_timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        cleanup_log_marker = "---CLEANUP LOG---"
        
        # Check if cleanup log section exists
        if cleanup_log_marker not in note_content:
            # Add the section at the end
            note_content = f"{note_content}<div><br></div><div><h2>{cleanup_log_marker}</h2></div><div><br></div>"
        
        # Add this cleanup timestamp
        cleanup_entry = f"Cleanup: {cleanup_timestamp} (Removed {len(successful_urls)} successful, Moved {len(failed_urls)} failed)"
        cleanup_entry_html = f'<div>{cleanup_entry}</div>'
        
        # Insert cleanup log entry after the marker
        log_marker_pos = note_content.find(cleanup_log_marker)
        if log_marker_pos != -1:
            # Find the end of the marker div
            log_marker_end = note_content.find('</div>', log_marker_pos + len(cleanup_log_marker))
            if log_marker_end != -1:
                # Insert cleanup log entry after the marker
                note_content = (note_content[:log_marker_end + 6] + 
                              f'<div><br></div>{cleanup_entry_html}<div><br></div>' + 
                              note_content[log_marker_end + 6:])
    
    # Clean up excessive empty divs
    note_content = re.sub(r'(<div><br></div>){3,}', '<div><br></div><div><br></div>', note_content)
    
    # Update the note
    print(f"\n💾 Updating iCloud Note...")
    if cleanup_timestamp:
        print(f"📝 Logging cleanup timestamp: {cleanup_timestamp}")
    success = update_note_content(note_title, note_content)
    
    return success

def interactive_mode():
    """Interactive mode - prompt user for input"""
    print("\n" + "=" * 60)
    print("   INTERACTIVE MODE")
    print("=" * 60)
    
    # Prompt for log file
    print("\n📄 Enter the path to the CSV log file:")
    print("   (You can also drag and drop the file here)")
    log_file = input("   Log file path: ").strip()
    
    # Remove quotes if user dragged and dropped
    log_file = log_file.strip('"').strip("'")
    
    if not log_file:
        print("❌ No log file specified. Exiting.")
        return None
    
    if not os.path.exists(log_file):
        print(f"❌ File not found: {log_file}")
        return None
    
    # Prompt for optional settings
    print("\n⚙️  Optional settings (press Enter to use defaults):")
    
    default_download_dir = os.path.join(os.path.expanduser("~"), "Downloads", "Videos")
    download_dir = input(f"   Download directory [default: {default_download_dir}]: ").strip()
    if not download_dir:
        download_dir = default_download_dir
    
    note_title = input("   iCloud Note title [default: Download_URLs]: ").strip()
    if not note_title:
        note_title = "Download_URLs"
    
    print("\n🔍 Preview changes before applying?")
    dry_run_choice = input("   Dry run? (y/n) [default: n]: ").strip().lower()
    dry_run = dry_run_choice in ['y', 'yes']
    
    return {
        'log_file': log_file,
        'download_dir': download_dir,
        'note': note_title,
        'dry_run': dry_run
    }

def main():
    parser = argparse.ArgumentParser(
        description="Clean up: Verify downloads and update iCloud Notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clean_up.py                          # Interactive mode
  python clean_up.py log.csv                  # Use default settings
  python clean_up.py log.csv --download-dir /path  # Custom download directory
  python clean_up.py log.csv --note "MyNote"    # Custom note name
        """
    )
    
    parser.add_argument(
        'log_file',
        type=str,
        nargs='?',  # Make it optional
        help='Path to the CSV log file (optional - will prompt in interactive mode)'
    )
    
    parser.add_argument(
        '--download-dir',
        type=str,
        default=os.path.join(os.path.expanduser("~"), "Downloads", "Videos"),
        help='Base download directory (default: ~/Downloads/Videos)'
    )
    
    parser.add_argument(
        '--note',
        type=str,
        default="Download_URLs",
        help='iCloud Note title (default: Download_URLs)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    # If no log file provided, enter interactive mode
    if not args.log_file:
        interactive_args = interactive_mode()
        if not interactive_args:
            sys.exit(1)
        # Use interactive mode values
        log_file = interactive_args['log_file']
        download_dir = interactive_args['download_dir']
        note_title = interactive_args['note']
        dry_run = interactive_args['dry_run']
    else:
        # Use command line arguments
        log_file = args.log_file
        download_dir = args.download_dir
        note_title = args.note
        dry_run = args.dry_run
    
    print("\n" + "=" * 60)
    print("   CLEAN UP: VERIFY DOWNLOADS & UPDATE NOTES")
    print("=" * 60)
    print(f"\n📄 Log file: {log_file}")
    print(f"📁 Download directory: {download_dir}")
    print(f"📝 Note: {note_title}")
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    print()
    
    # Read log file
    log_entries = read_log_csv(log_file)
    
    if not log_entries:
        print("❌ No log entries found. Exiting.")
        sys.exit(1)
    
    print(f"📊 Found {len(log_entries)} log entries")
    
    # Process each entry
    successful_urls = []
    failed_urls = []
    verified_count = 0
    not_found_count = 0
    
    print("\n" + "=" * 60)
    print("🔍 VERIFYING DOWNLOADS")
    print("=" * 60)
    
    for entry in log_entries:
        url = entry.get('URL', '')
        status = entry.get('Status', '')
        video_id = entry.get('Video ID', '')
        title = entry.get('Title', 'Unknown')
        
        if not url:
            continue
        
        if '✅ Success' in status:
            print(f"\n✅ Checking: {title[:40]}...")
            if verify_successful_download(entry, download_dir):
                successful_urls.append(url)
                verified_count += 1
                print(f"   ✓ MP4 file found - will remove from note")
            else:
                not_found_count += 1
                print(f"   ⚠️  MP4 file not found - keeping in note")
        elif '❌ Failed' in status:
            failed_urls.append(url)
            print(f"\n❌ Failed: {title[:40]}...")
            print(f"   → Will move to FAILED URLS section")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Verified successful: {verified_count}")
    print(f"⚠️  Not found: {not_found_count}")
    print(f"❌ Failed URLs: {len(failed_urls)}")
    
    # Update note if not dry run
    if dry_run:
        print("\n🔍 DRY RUN - Would update note with:")
        if successful_urls:
            print(f"   Remove {len(successful_urls)} successful URL(s)")
        if failed_urls:
            print(f"   Move {len(failed_urls)} failed URL(s) to FAILED section")
    else:
        if successful_urls or failed_urls:
            success = update_note_with_changes(note_title, successful_urls, failed_urls)
            if success:
                print("\n✅ Note updated successfully!")
            else:
                print("\n❌ Failed to update note")
        else:
            print("\n💡 No changes needed")

if __name__ == "__main__":
    main()

