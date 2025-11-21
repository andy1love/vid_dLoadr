#!/usr/bin/env python3
"""
Video Downloader Script - Fixed for 403 Errors
Downloads videos from YouTube or Instagram into dated folders
Supports single URLs, batch processing from files, and interactive mode
"""

import os
import sys
import argparse
import csv
import json
from datetime import datetime
import subprocess

def check_yt_dlp():
    """Check if yt-dlp is installed"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                      capture_output=True, 
                      check=True,
                      text=True)
        version = result.stdout.strip()
        print(f"✅ yt-dlp version: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_yt_dlp():
    """Provide instructions for installing yt-dlp"""
    print("\n⚠️  yt-dlp is not installed!")
    print("\nTo install yt-dlp, run one of these commands:")
    print("  pip install yt-dlp")
    print("  or")
    print("  brew install yt-dlp  (if you have Homebrew)")
    print("\nThen run this script again.")
    sys.exit(1)

def read_urls_from_file(file_path):
    """Read URLs from a text file or CSV file"""
    urls = []
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return urls
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Check if it's a CSV file
            if file_path.lower().endswith('.csv'):
                reader = csv.reader(file)
                for row in reader:
                    if row and row[0].strip():  # Skip empty rows
                        urls.append(row[0].strip())
            else:
                # Treat as text file
                for line in file:
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip empty lines and comments
                        urls.append(line)
        
        print(f"📄 Found {len(urls)} URLs in {file_path}")
        return urls
    
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        return []

def create_download_folder(base_path):
    """Create a dated folder for today's downloads"""
    today = datetime.now().strftime('%Y%m%d')
    folder_path = os.path.join(base_path, today)
    
    # Create folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    
    return folder_path

def get_video_info(url, use_cookies=False, cookies_browser=None):
    """Get video metadata using yt-dlp JSON output"""
    command = [
        'yt-dlp',
        '--dump-json',
        '--no-check-certificate',
        '--user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    ]
    
    if use_cookies and cookies_browser:
        command.extend(['--cookies-from-browser', cookies_browser])
    
    command.append(url)
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return None

def download_video(url, download_path, use_cookies=False, cookies_browser=None):
    """Download video using yt-dlp with enhanced options to avoid 403 errors
    Returns: (success: bool, title: str, video_id: str, error: str)"""
    print(f"\n📥 Downloading video to: {download_path}")
    print(f"🔗 URL: {url}\n")
    
    # Try to get video info first
    video_info = get_video_info(url, use_cookies, cookies_browser)
    title = video_info.get('title', 'Unknown') if video_info else 'Unknown'
    video_id = video_info.get('id', '') if video_info else ''
    duration = video_info.get('duration', 0) if video_info else 0
    
    # Enhanced yt-dlp command with anti-403 measures
    command = [
        'yt-dlp',
        # Format selection - try multiple fallbacks
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        # Output format
        '--merge-output-format', 'mp4',
        '--recode-video', 'mp4',
        # Post-processing (highest quality - no preset for maximum quality)
        '--postprocessor-args', 'ffmpeg:-c:v libx264 -c:a aac -movflags +faststart',
        # Anti-bot measures
        '--user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '--sleep-requests', '1',
        '--sleep-interval', '3',
        '--max-sleep-interval', '6',
        # Retries
        '--retries', '10',
        '--fragment-retries', '10',
        # Additional options
        '--no-check-certificate',
        '--prefer-free-formats',
        # Output template with ID for unique filenames
        '-o', os.path.join(download_path, '%(title)s_%(id)s.%(ext)s'),
    ]
    
    # Add cookies if requested
    if use_cookies and cookies_browser:
        command.extend(['--cookies-from-browser', cookies_browser])
        print(f"🍪 Using cookies from {cookies_browser}")
    
    # Add URL
    command.append(url)
    
    try:
        # Run yt-dlp with real-time progress output
        # Add timeout for very long downloads (2 hours max)
        print("⏳ Processing (this may take a few minutes for large files)...")
        print("   Watch for progress updates below:\n")
        
        # Run without capturing output - let yt-dlp print directly
        # This ensures all progress messages are visible in real-time
        result = subprocess.run(command, check=True, timeout=7200)
        
        print("\n✅ Download complete!")
        return True, title, video_id, duration, ""
    except subprocess.TimeoutExpired:
        print(f"\n⏱️  Download timed out after 2 hours")
        return False, title, video_id, duration, "Timeout after 2 hours"
    except subprocess.CalledProcessError as e:
        error_msg = str(e)[:100]
        print(f"\n❌ Error downloading video: {e}")
        return False, title, video_id, duration, error_msg

def generate_log_filename(input_file):
    """Generate matching log CSV filename from input URLs file"""
    if not input_file:
        return None
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Create logs directory in workarea (parent of urls directory)
    # If input_file is in workarea/urls/, log goes to workarea/logs/
    input_dir = os.path.dirname(input_file)
    if os.path.basename(input_dir) == 'urls':
        # We're in workarea/urls/, so logs go to workarea/logs/
        workarea_dir = os.path.dirname(input_dir)
        logs_dir = os.path.join(workarea_dir, 'logs')
    else:
        # Fallback: create logs directory next to input file
        logs_dir = os.path.join(os.path.dirname(input_file), 'logs')
    
    # Ensure logs directory exists
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create matching log filename: <original>_log.csv
    log_filename = f"{base_name}_log.csv"
    return os.path.join(logs_dir, log_filename)

def format_duration(seconds):
    """Format duration in seconds to readable format"""
    if not seconds or seconds == 0:
        return ""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

def format_download_time(seconds):
    """Format download time duration to readable format"""
    if not seconds or seconds < 1:
        return "<1s"
    if seconds < 60:
        return f"{int(seconds)}s"
    mins, secs = divmod(int(seconds), 60)
    if mins < 60:
        return f"{mins}m {secs}s"
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s"

def write_log_csv(log_file, download_logs):
    """Write download log to CSV file (optimized for 13" monitor readability)"""
    if not download_logs:
        return
    
    try:
        with open(log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Headers optimized for readability on 13" screen
            writer.writerow([
                'Status',
                'Title',
                'Duration',
                'Download Time',
                'Video ID',
                'URL',
                'Timestamp',
                'Error'
            ])
            
            for log_entry in download_logs:
                status = "✅ Success" if log_entry['success'] else "❌ Failed"
                title = log_entry['title'][:50] + "..." if len(log_entry['title']) > 50 else log_entry['title']
                duration = format_duration(log_entry['duration'])
                download_time = format_download_time(log_entry.get('download_time', 0))
                video_id = log_entry['video_id']
                url = log_entry['url']  # Full URL, no truncation
                timestamp = log_entry['timestamp']
                error = log_entry['error'][:80] if log_entry['error'] else ""
                
                writer.writerow([
                    status,
                    title,
                    duration,
                    download_time,
                    video_id,
                    url,
                    timestamp,
                    error
                ])
        
        print(f"\n📊 Download log saved to: {log_file}")
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not write log file: {e}")
        return False

def download_multiple_videos(urls, download_path, use_cookies=False, cookies_browser=None, input_file=None):
    """Download multiple videos from a list of URLs"""
    total_urls = len(urls)
    successful_downloads = 0
    failed_downloads = 0
    failed_urls = []
    download_logs = []
    
    print(f"\n🚀 Starting batch download of {total_urls} videos...")
    print("=" * 60)
    
    start_time = datetime.now()
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{total_urls}] Processing URL...")
        
        # Validate URL
        if not (url.startswith('http://') or url.startswith('https://')):
            print(f"❌ Invalid URL (skipping): {url}")
            failed_downloads += 1
            failed_urls.append(url)
            download_logs.append({
                'success': False,
                'title': 'Invalid URL',
                'video_id': '',
                'duration': 0,
                'download_time': 0,
                'url': url,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': 'Invalid URL format'
            })
            continue
        
        # Track download time
        download_start = datetime.now()
        success, title, video_id, duration, error = download_video(
            url, download_path, use_cookies, cookies_browser
        )
        download_end = datetime.now()
        download_time = (download_end - download_start).total_seconds()
        
        # Log this download
        download_logs.append({
            'success': success,
            'title': title,
            'video_id': video_id,
            'duration': duration,
            'download_time': download_time,
            'url': url,
            'timestamp': download_end.strftime('%Y-%m-%d %H:%M:%S'),
            'error': error
        })
        
        if success:
            successful_downloads += 1
        else:
            failed_downloads += 1
            failed_urls.append(url)
    
    print("\n" + "=" * 60)
    print(f"📊 Batch download complete!")
    print(f"✅ Successful: {successful_downloads}")
    print(f"❌ Failed: {failed_downloads}")
    print(f"📂 All downloads saved in: {download_path}")
    
    # Save failed URLs to a file
    if failed_urls:
        failed_file = os.path.join(download_path, 'failed_urls.txt')
        with open(failed_file, 'w') as f:
            for url in failed_urls:
                f.write(f"{url}\n")
        print(f"\n📝 Failed URLs saved to: {failed_file}")
    
    # Write CSV log file matching input filename
    if input_file:
        log_file = generate_log_filename(input_file)
        if log_file:
            write_log_csv(log_file, download_logs)
    
    return successful_downloads, failed_downloads

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Download videos from YouTube and Instagram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_video.py                           # Interactive mode
  python download_video.py --url "https://youtube.com/watch?v=..."  # Single URL
  python download_video.py --file urls.txt          # Batch from file
  python download_video.py --file urls.csv          # Batch from CSV
  python download_video.py --cookies chrome --file urls.txt  # Use Chrome cookies
        """
    )
    
    parser.add_argument(
        '--url', 
        type=str, 
        help='Single video URL to download'
    )
    
    parser.add_argument(
        '--file', 
        type=str, 
        help='Path to text or CSV file containing URLs (one per line)'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default=os.path.join(os.path.expanduser("~"), "Downloads", "Videos"),
        help='Base output directory (default: ~/Downloads/Videos)'
    )
    
    parser.add_argument(
        '--cookies',
        type=str,
        choices=['chrome', 'firefox', 'safari', 'edge'],
        help='Browser to extract cookies from (helps avoid 403 errors)'
    )
    
    return parser.parse_args()

def interactive_mode(download_folder):
    """Interactive mode - prompt user for input"""
    print("\n" + "=" * 50)
    print("   INTERACTIVE MODE")
    print("=" * 50)
    
    # Ask about cookies once
    use_cookies = False
    cookies_browser = None
    print("\n💡 TIP: Using browser cookies can help avoid 403 errors")
    print("Do you want to use cookies from your browser? (y/n): ", end="")
    cookies_choice = input().strip().lower()
    if cookies_choice in ['y', 'yes']:
        print("\nWhich browser?")
        print("1. Chrome")
        print("2. Firefox")
        print("3. Safari")
        print("4. Edge")
        browser_choice = input("Enter choice (1-4): ").strip()
        browsers = {'1': 'chrome', '2': 'firefox', '3': 'safari', '4': 'edge'}
        cookies_browser = browsers.get(browser_choice)
        if cookies_browser:
            use_cookies = True
            print(f"✅ Will use cookies from {cookies_browser}")
    
    while True:
        print("\n" + "=" * 50)
        print("Choose an option:")
        print("1. Enter a single URL")
        print("2. Load URLs from a file")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            # Single URL mode
            url = input("\nPaste the video URL: ").strip()
            if not url:
                print("❌ No URL provided.")
                continue
            
            if not (url.startswith('http://') or url.startswith('https://')):
                print("❌ Invalid URL. Must start with http:// or https://")
                continue
            
            success, title, video_id, duration, error = download_video(url, download_folder, use_cookies, cookies_browser)
            if success:
                print(f"\n📂 Video saved in folder: {download_folder}")
            else:
                print("\n❌ Download failed. Please check the URL and try again.")
        
        elif choice == '2':
            # File mode
            file_path = input("\nEnter path to file (.txt or .csv): ").strip()
            if not file_path:
                print("❌ No file path provided.")
                continue
            
            urls = read_urls_from_file(file_path)
            if not urls:
                print("❌ No valid URLs found in file.")
                continue
            
            # Confirm before downloading
            print(f"\nFound {len(urls)} URLs. Proceed with download? (y/n): ", end="")
            confirm = input().strip().lower()
            if confirm in ['y', 'yes']:
                download_multiple_videos(urls, download_folder, use_cookies, cookies_browser, input_file=file_path)
            else:
                print("Download cancelled.")
        
        elif choice == '3':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Base download path
    base_path = args.output
    
    print("=" * 50)
    print("   VIDEO DOWNLOADER (403 Error Fixed)")
    print("   Supports: YouTube & Instagram")
    print("=" * 50)
    
    # Check if yt-dlp is installed
    if not check_yt_dlp():
        install_yt_dlp()
    
    # Remind user to update yt-dlp
    print("\n💡 TIP: If you're getting 403 errors, update yt-dlp:")
    print("   pip install --upgrade yt-dlp")
    
    # Create today's folder
    download_folder = create_download_folder(base_path)
    print(f"\n📁 Downloads will be saved to: {download_folder}")
    
    # Determine mode based on arguments
    if args.url:
        # Single URL mode
        print(f"\n🔗 Downloading single URL: {args.url}")
        
        if not (args.url.startswith('http://') or args.url.startswith('https://')):
            print("❌ Invalid URL. Must start with http:// or https://")
            sys.exit(1)
        
        success, title, video_id, duration, error = download_video(args.url, download_folder, 
                                use_cookies=bool(args.cookies), 
                                cookies_browser=args.cookies)
        if success:
            print(f"\n📂 Video saved in folder: {download_folder}")
        else:
            print("\n❌ Download failed. Please check the URL and try again.")
    
    elif args.file:
        # File mode
        print(f"\n📄 Loading URLs from file: {args.file}")
        urls = read_urls_from_file(args.file)
        
        if not urls:
            print("❌ No valid URLs found in file. Exiting.")
            sys.exit(1)
        
        download_multiple_videos(urls, download_folder,
                                use_cookies=bool(args.cookies),
                                cookies_browser=args.cookies,
                                input_file=args.file)
    
    else:
        # Interactive mode
        interactive_mode(download_folder)

if __name__ == "__main__":
    main()