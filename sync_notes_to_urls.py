#!/usr/bin/env python3
"""
iCloud Notes to URLs Script
Reads URLs from a shared iCloud Note and appends them to urls.txt
"""

import subprocess
import os
import re
from datetime import datetime
from urllib.parse import urlparse
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML"""
    def __init__(self):
        super().__init__()
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data.strip())
    
    def get_text(self):
        return ' '.join(self.text)

def strip_html(html_content):
    """Strip HTML tags and extract plain text"""
    if not html_content:
        return ""
    
    # Check if it's actually HTML
    if '<' in html_content and '>' in html_content:
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        return '\n'.join(line for line in parser.get_text().split() if line)
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
        
    except subprocess.TimeoutExpired:
        print("❌ Timeout: Notes app took too long to respond")
        return None
    except Exception as e:
        print(f"❌ Error accessing Notes: {e}")
        return None

def extract_urls_by_marker(text_or_html):
    """Extract URLs from text, separated by ___mp3___ and ___mp4___ markers
    Returns: (mp3_urls: list, mp4_urls: list, all_urls: list)"""
    mp3_urls = []
    mp4_urls = []
    all_urls = []
    
    if not text_or_html:
        return mp3_urls, mp4_urls, all_urls
    
    # First, strip HTML to get plain text
    text = strip_html(text_or_html)
    
    # Split by markers
    mp3_marker = "___mp3___"
    mp4_marker = "___mp4___"
    
    # Find marker positions
    lines = text.split('\n')
    current_section = None  # 'mp3', 'mp4', or None
    
    url_pattern = r'https?://[^\s<>"\']+'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for markers (case-insensitive)
        if mp3_marker.lower() in line.lower():
            current_section = 'mp3'
            continue
        elif mp4_marker.lower() in line.lower():
            current_section = 'mp4'
            continue
        
        # Extract URLs from the line
        found_urls = re.findall(url_pattern, line)
        if not found_urls:
            # Check if entire line is a URL
            if line.startswith('http://') or line.startswith('https://'):
                found_urls = [line]
        
        # Add URLs to appropriate list
        for url in found_urls:
            url = url.rstrip('.,;!?)')
            try:
                parsed = urlparse(url)
                if parsed.netloc:
                    if current_section == 'mp3' and url not in mp3_urls:
                        mp3_urls.append(url)
                        all_urls.append(url)
                    elif current_section == 'mp4' and url not in mp4_urls:
                        mp4_urls.append(url)
                        all_urls.append(url)
                    elif current_section is None:
                        # URLs before any marker go to mp4 (default behavior)
                        if url not in mp4_urls:
                            mp4_urls.append(url)
                            all_urls.append(url)
            except:
                pass
    
    return mp3_urls, mp4_urls, all_urls

def extract_urls(text_or_html):
    """Extract URLs from text (handles both plain text and HTML)
    Legacy function for backward compatibility"""
    _, _, all_urls = extract_urls_by_marker(text_or_html)
    return all_urls

def read_existing_urls(file_path):
    """Read existing URLs from file to avoid duplicates"""
    if not os.path.exists(file_path):
        return set()
    
    existing = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    existing.add(line)
    except Exception as e:
        print(f"⚠️  Warning: Could not read existing URLs: {e}")
    
    return existing

def append_urls_to_file(file_path, new_urls, existing_urls):
    """Append new URLs to file, skipping duplicates"""
    if not new_urls:
        return 0, [], []
    
    added_count = 0
    added_urls = []
    skipped_urls = []
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
    
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            for url in new_urls:
                if url not in existing_urls:
                    f.write(f"{url}\n")
                    existing_urls.add(url)  # Update set to prevent duplicates in same run
                    added_count += 1
                    added_urls.append(url)
                else:
                    skipped_urls.append(url)
        
        return added_count, added_urls, skipped_urls
        
    except Exception as e:
        print(f"❌ Error writing to file: {e}")
        return 0, [], []

def create_timestamped_file(all_urls, base_dir, file_type=''):
    """Create a timestamped file with URLs
    file_type: 'mp3', 'mp4', or '' for combined"""
    # Generate timestamp: YYYYMMDD_HHMM
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    # Count total URLs
    url_count = len(all_urls)
    
    # Create filename: YYYYMMDD_HHMM_<count>_<type>_urls.txt
    type_suffix = f"_{file_type}" if file_type else ""
    filename = f"{timestamp}_{url_count}{type_suffix}_urls.txt"
    file_path = os.path.join(base_dir, filename)
    
    # Write all URLs to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for url in sorted(all_urls):  # Sort for consistency
                f.write(f"{url}\n")
        
        return file_path, filename
    except Exception as e:
        print(f"❌ Error creating timestamped file: {e}")
        return None, None

def main():
    # Configuration
    NOTE_TITLE = "Download_URLs"  # Change this to match your note title
    # Use relative path from script location
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    WORKAREA_DIR = os.path.join(SCRIPT_DIR, "_workarea")
    URLS_DIR = os.path.join(WORKAREA_DIR, "urls")
    URLS_FILE = os.path.join(URLS_DIR, "urls.txt")
    
    # Ensure directories exist
    os.makedirs(URLS_DIR, exist_ok=True)
    
    print("=" * 50)
    print("   iCLOUD NOTES TO URLS SCRIPT")
    print("=" * 50)
    print(f"\n📝 Looking for note: '{NOTE_TITLE}'")
    print(f"📄 Target file: {URLS_FILE}\n")
    
    # Step 1: Get note content
    print("🔍 Reading note from iCloud Notes...")
    note_content = get_note_content(NOTE_TITLE)
    
    if note_content is None or note_content.strip() == "":
        print(f"❌ Note '{NOTE_TITLE}' not found or empty.")
        print("\n💡 Make sure:")
        print("   1. The note exists in Notes app")
        print("   2. The note title matches exactly (case-sensitive)")
        print("   3. The note is synced to iCloud")
        return
    
    print(f"✅ Found note content ({len(note_content)} characters)")
    
    # Step 2: Extract URLs by marker (MP3 vs MP4)
    print("\n🔗 Extracting URLs by marker (___mp3___ / ___mp4___)...")
    mp3_urls, mp4_urls, all_urls = extract_urls_by_marker(note_content)
    
    if not all_urls:
        print("❌ No URLs found in note")
        return
    
    print(f"✅ Found {len(mp3_urls)} MP3 URL(s) and {len(mp4_urls)} MP4 URL(s)")
    print(f"📊 Total: {len(all_urls)} URL(s)")
    
    # Step 3: Check existing URLs
    print("\n📋 Checking for duplicates...")
    existing_urls = read_existing_urls(URLS_FILE)
    print(f"📊 Existing URLs in file: {len(existing_urls)}")
    
    # Step 4: Append new URLs to main file
    print(f"\n💾 Appending to {URLS_FILE}...")
    added_count, added_urls, skipped_urls = append_urls_to_file(
        URLS_FILE, all_urls, existing_urls
    )
    
    # Step 5: Create timestamped files with URLs from Note only
    # Create separate files for MP3 and MP4 URLs
    timestamped_files = {}
    
    if mp3_urls:
        mp3_file, mp3_filename = create_timestamped_file(set(mp3_urls), URLS_DIR, 'mp3')
        if mp3_file:
            timestamped_files['mp3'] = mp3_file
            print(f"\n📄 Created MP3 timestamped file: {mp3_filename}")
            print(f"OUTPUT_FILE_MP3:{mp3_file}")
    
    if mp4_urls:
        mp4_file, mp4_filename = create_timestamped_file(set(mp4_urls), URLS_DIR, 'mp4')
        if mp4_file:
            timestamped_files['mp4'] = mp4_file
            print(f"\n📄 Created MP4 timestamped file: {mp4_filename}")
            print(f"OUTPUT_FILE_MP4:{mp4_file}")
    
    # For backward compatibility, also create combined file if no markers found
    if not mp3_urls and not mp4_urls:
        # Fallback: treat all URLs as MP4 (default behavior)
        note_urls = set(all_urls)
        timestamped_file, timestamped_filename = create_timestamped_file(note_urls, URLS_DIR)
        if timestamped_file:
            timestamped_files['combined'] = timestamped_file
            print(f"\n📄 Created timestamped file: {timestamped_filename}")
            print(f"OUTPUT_FILE:{timestamped_file}")
    
    # Step 6: Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"✅ Added: {added_count} new URL(s)")
    if skipped_urls:
        print(f"⏭️  Skipped: {len(skipped_urls)} duplicate(s)")
    print(f"📊 Total URLs in Note: {len(all_urls)}")
    print(f"   • MP3 URLs: {len(mp3_urls)}")
    print(f"   • MP4 URLs: {len(mp4_urls)}")
    print(f"📊 Total URLs in history file: {len(existing_urls)}")
    
    if timestamped_files:
        print(f"\n📁 Created timestamped files:")
        for file_type, file_path in timestamped_files.items():
            print(f"   • {file_type}: {os.path.basename(file_path)}")
    
    if added_urls:
        print("\n📝 Added URLs:")
        for url in added_urls:
            print(f"   • {url}")
    
    if skipped_urls and len(skipped_urls) <= 10:
        print("\n⏭️  Skipped (duplicates):")
        for url in skipped_urls:
            print(f"   • {url}")
    elif skipped_urls:
        print(f"\n⏭️  Skipped {len(skipped_urls)} duplicate(s)")

if __name__ == "__main__":
    main()
