#!/usr/bin/env python3
"""
iMessage to Apple Notes Sync Script
Reads URLs from iMessage and appends them to an iCloud Note, skipping duplicates.
"""

import subprocess
import os
import re
import sys
import tempfile
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

def extract_urls(text_or_html):
    """Extract URLs from text (handles both plain text and HTML)"""
    urls = []
    
    if not text_or_html:
        return urls
    
    # First, strip HTML to get plain text
    text = strip_html(text_or_html)
    
    # Also extract URLs directly from HTML/raw content (in case they're in attributes)
    url_pattern = r'https?://[^\s<>"\']+'
    all_found_urls = re.findall(url_pattern, text_or_html)
    
    # Add URLs found in raw content
    for url in all_found_urls:
        url = url.rstrip('.,;!?)')
        try:
            parsed = urlparse(url)
            if parsed.netloc and url not in urls:
                urls.append(url)
        except:
            pass
    
    # Also check the plain text extracted from HTML
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if entire line is a URL
        if line.startswith('http://') or line.startswith('https://'):
            # Validate URL
            try:
                parsed = urlparse(line)
                if parsed.netloc and line not in urls:  # Avoid duplicates
                    urls.append(line)
            except:
                pass
        else:
            # Try to find URLs embedded in the line
            found_urls = re.findall(url_pattern, line)
            for url in found_urls:
                url = url.rstrip('.,;!?)')
                try:
                    parsed = urlparse(url)
                    if parsed.netloc and url not in urls:
                        urls.append(url)
                except:
                    pass
    
    return urls

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

def get_urls_from_clipboard():
    """Extract URLs from clipboard as fallback method"""
    try:
        result = subprocess.run(
            ['osascript', '-e', 'get the clipboard as string'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            clipboard_text = result.stdout.strip()
            if clipboard_text:
                return extract_urls(clipboard_text)
    except:
        pass
    
    return []

def get_messages_urls(conversation_name=None, limit=50):
    """Extract URLs from iMessage conversations using AppleScript
    
    Args:
        conversation_name: Name of specific conversation (optional)
        limit: Maximum number of recent messages to check
    
    Returns:
        List of URLs found in messages
    """
    if conversation_name:
        # Get URLs from specific conversation
        apple_script = f'''
        tell application "Messages"
            set foundMessages to ""
            repeat with aChat in chats
                try
                    set chatName to name of aChat
                    if chatName is not missing value and chatName contains "{conversation_name}" then
                        try
                            set msgList to messages of aChat
                            set msgCount to count of msgList
                            repeat with i from 1 to msgCount
                                try
                                    set aMessage to item i of msgList
                                    set msgText to text of aMessage
                                    if msgText is not missing value and msgText contains "http" then
                                        set foundMessages to foundMessages & msgText & "\\n"
                                    end if
                                end try
                            end repeat
                        end try
                        exit repeat
                    end if
                end try
            end repeat
            return foundMessages
        end tell
        '''
    else:
        # Get URLs from all recent messages
        apple_script = f'''
        tell application "Messages"
            set foundMessages to ""
            set totalMsgCount to 0
            repeat with aChat in chats
                try
                    try
                        set msgList to messages of aChat
                        set msgCount to count of msgList
                        repeat with i from 1 to msgCount
                            try
                                set aMessage to item i of msgList
                                set msgText to text of aMessage
                                if msgText is not missing value and msgText contains "http" then
                                    set foundMessages to foundMessages & msgText & "\\n"
                                end if
                                set totalMsgCount to totalMsgCount + 1
                                if totalMsgCount > {limit} then exit repeat
                            end try
                        end repeat
                    end try
                    if totalMsgCount > {limit} then exit repeat
                end try
            end repeat
            return foundMessages
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
            print(f"⚠️  Warning: Could not read Messages: {result.stderr}")
            print("   Make sure Messages app has necessary permissions")
            return []
        
        # Parse the output
        messages_text = result.stdout.strip()
        if not messages_text:
            if conversation_name:
                print(f"   Debug: No messages found in conversation '{conversation_name}'")
                print("   Try checking conversation name spelling or use --limit to check more messages")
            return []
        
        # Extract URLs from all messages
        all_urls = []
        url_pattern = r'https?://[^\s<>"\']+'
        
        # Extract URLs from the combined text
        found_urls = re.findall(url_pattern, messages_text)
        for url in found_urls:
            url = url.rstrip('.,;!?)')
            try:
                parsed = urlparse(url)
                if parsed.netloc and url not in all_urls:
                    all_urls.append(url)
            except:
                pass
        
        return all_urls
        
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout: Messages app took too long to respond")
        return []
    except Exception as e:
        print(f"⚠️  Error accessing Messages: {e}")
        print("   Make sure Messages app has necessary permissions")
        return []

def update_note_content(note_title, new_content):
    """Update iCloud Note content using AppleScript"""
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

def update_note_with_urls(note_title, new_urls):
    """Append new URLs to an iCloud Note, skipping duplicates from both Note and history file"""
    # Get current note content
    print("📖 Reading current note content...")
    note_content = get_note_content(note_title)
    
    if note_content is None:
        print(f"❌ Note '{note_title}' not found or could not be read.")
        print("\n💡 Make sure:")
        print("   1. The note exists in Notes app")
        print("   2. The note title matches exactly (case-sensitive)")
        print("   3. The note is synced to iCloud")
        return False
    
    # Extract existing URLs from note
    existing_in_note = set(extract_urls(note_content))
    print(f"📊 Found {len(existing_in_note)} existing URL(s) in note")
    
    # ALSO check the permanent history file (urls.txt)
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    WORKAREA_DIR = os.path.join(SCRIPT_DIR, "_workarea")
    URLS_DIR = os.path.join(WORKAREA_DIR, "urls")
    URLS_FILE = os.path.join(URLS_DIR, "urls.txt")
    
    existing_in_history = set()
    if os.path.exists(URLS_FILE):
        existing_in_history = read_existing_urls(URLS_FILE)
        print(f"📊 Found {len(existing_in_history)} URL(s) in history file")
    
    # Combine both sets - URL is duplicate if it's in EITHER place
    all_existing_urls = existing_in_note | existing_in_history
    
    # Filter out duplicates
    urls_to_add = []
    skipped_in_note = []
    skipped_in_history = []
    
    for url in new_urls:
        if url not in all_existing_urls:
            urls_to_add.append(url)
        else:
            if url in existing_in_note:
                skipped_in_note.append(url)
            else:
                skipped_in_history.append(url)
    
    # Report skipped URLs
    if skipped_in_note:
        print(f"\n⏭️  Skipping {len(skipped_in_note)} URL(s) already in note:")
        for url in skipped_in_note[:5]:  # Show first 5
            print(f"   • {url[:60]}...")
        if len(skipped_in_note) > 5:
            print(f"   ... and {len(skipped_in_note) - 5} more")
    
    if skipped_in_history:
        print(f"\n⏭️  Skipping {len(skipped_in_history)} URL(s) already processed:")
        for url in skipped_in_history[:5]:  # Show first 5
            print(f"   • {url[:60]}...")
        if len(skipped_in_history) > 5:
            print(f"   ... and {len(skipped_in_history) - 5} more")
    
    if not urls_to_add:
        print("\n✅ No new URLs to add (all are duplicates or already processed)")
        return True
    
    print(f"\n➕ Adding {len(urls_to_add)} new URL(s) to note...")
    
    # Append new URLs to note content
    # Add each URL as a new line/div
    urls_html = '<div><br></div>'.join([f'<div>{url}</div>' for url in urls_to_add])
    
    # Append to existing content
    new_content = f"{note_content}<div><br></div>{urls_html}"
    
    # Clean up excessive empty divs
    new_content = re.sub(r'(<div><br></div>){3,}', '<div><br></div><div><br></div>', new_content)
    
    # Update the note
    success = update_note_content(note_title, new_content)
    
    if success:
        print(f"✅ Successfully added {len(urls_to_add)} URL(s) to note")
        if urls_to_add:
            print("\n📝 Added URLs:")
            for url in urls_to_add:
                print(f"   • {url}")
    
    return success

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync URLs from iMessage to Apple Notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python sync_messages_to_notes.py                    # Check all recent messages
  python sync_messages_to_notes.py --conversation "John"  # Check specific conversation
  python sync_messages_to_notes.py --note "MyNote"    # Use different note name
  python sync_messages_to_notes.py --limit 100         # Check more messages
        """
    )
    
    parser.add_argument(
        '--conversation',
        type=str,
        help='Name of specific iMessage conversation to check (optional)'
    )
    
    parser.add_argument(
        '--note',
        type=str,
        default="Download_URLs",
        help='iCloud Note title (default: Download_URLs)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=50,
        help='Maximum number of recent messages to check (default: 50)'
    )
    
    parser.add_argument(
        '--clipboard',
        action='store_true',
        help='Read URLs from clipboard instead of Messages (useful if Messages API is restricted)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("   iMESSAGE TO APPLE NOTES SYNC")
    print("=" * 60)
    
    # Step 1: Get URLs from Messages or Clipboard
    if args.clipboard:
        print(f"\n📋 Reading URLs from clipboard...")
        print(f"📝 Target note: '{args.note}'\n")
        message_urls = get_urls_from_clipboard()
    else:
        print(f"\n📱 Reading URLs from iMessage...")
        if args.conversation:
            print(f"   Conversation: {args.conversation}")
        else:
            print(f"   Checking all recent messages (limit: {args.limit})")
        print(f"📝 Target note: '{args.note}'\n")
        message_urls = get_messages_urls(
            conversation_name=args.conversation,
            limit=args.limit
        )
        
        # If no URLs found and user specified a conversation, suggest clipboard method
        if not message_urls and args.conversation:
            print("💡 Tip: If Messages API is restricted, try:")
            print(f"   1. Open Messages and select/copy messages from '{args.conversation}'")
            print(f"   2. Run: python3 sync_messages_to_notes.py --clipboard")
    
    if not message_urls:
        print("❌ No URLs found in iMessage")
        print("\n💡 Make sure:")
        print("   1. Messages app has necessary permissions")
        print("   2. You have messages with URLs")
        if args.conversation:
            print(f"   3. Conversation name '{args.conversation}' is correct")
        return
    
    print(f"✅ Found {len(message_urls)} URL(s) in iMessage")
    
    # Step 2: Add to Note (with duplicate checking)
    print("\n" + "=" * 60)
    print("   SYNCING TO APPLE NOTES")
    print("=" * 60)
    
    success = update_note_with_urls(args.note, message_urls)
    
    if success:
        print("\n" + "=" * 60)
        print("   ✅ SYNC COMPLETE")
        print("=" * 60)
        print("\n💡 Next step: Run 'python trigger_download.py' to download videos")
    else:
        print("\n" + "=" * 60)
        print("   ❌ SYNC FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()

