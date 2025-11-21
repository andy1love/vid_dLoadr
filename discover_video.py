#!/usr/bin/env python3
"""
Video Discovery Script - Hybrid Configuration
Finds great dance and music performance videos with customizable filters
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import re

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("⚠️  Google API client not installed. Run: pip install google-api-python-client")
    sys.exit(1)

# ============================================================================
# DEFAULT CONFIGURATION
# ============================================================================

DEFAULT_CONFIG = {
    'defaults': {
        'duration_min': 180,
        'duration_max': 900,
        'min_views': 5000,
        'days_back': 7,
        'max_results_per_query': 10
    },
    'queries': [
        "professional ballet performance",
        "orchestra concert hall",
        "cultural dance performance"
    ],
    'channels': [],
    'filters': {
        'required_keywords': [],
        'excluded_keywords': ['compilation', 'tutorial', 'reaction', 'behind the scenes'],
        'excluded_channels': []
    },
    'quality': {
        'min_like_ratio': 0.02,
        'verified_only': False,
        'min_channel_subscribers': 0
    },
    'output': {
        'report_format': 'html',
        'thumbnail_size': 'medium',
        'sort_by': 'views',
        'output_dir': './video_reports'
    }
}

# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

class ConfigManager:
    """Manages configuration from multiple sources with priority"""
    
    def __init__(self, config_file=None, cli_args=None, profile=None):
        self.config = DEFAULT_CONFIG.copy()
        
        # Load config file if provided
        if config_file and os.path.exists(config_file):
            self.load_config_file(config_file)
        
        # Load profile if specified
        if profile:
            self.load_profile(profile)
        
        # Apply CLI overrides
        if cli_args:
            self.apply_cli_overrides(cli_args)
    
    def load_config_file(self, filepath):
        """Load configuration from JSON file"""
        try:
            with open(filepath, 'r') as f:
                file_config = json.load(f)
                self.merge_config(file_config)
            print(f"✅ Loaded config from: {filepath}")
        except Exception as e:
            print(f"⚠️  Error loading config file: {e}")
    
    def load_profile(self, profile_name):
        """Load a preset profile"""
        profiles_file = os.path.join(os.path.dirname(__file__), 'profiles.json')
        if os.path.exists(profiles_file):
            try:
                with open(profiles_file, 'r') as f:
                    profiles = json.load(f)
                    if profile_name in profiles.get('profiles', {}):
                        profile_config = profiles['profiles'][profile_name]
                        self.merge_config(profile_config)
                        print(f"✅ Loaded profile: {profile_name}")
                    else:
                        print(f"⚠️  Profile '{profile_name}' not found")
            except Exception as e:
                print(f"⚠️  Error loading profile: {e}")
    
    def merge_config(self, new_config):
        """Recursively merge new config into existing"""
        def deep_merge(base, update):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
        
        deep_merge(self.config, new_config)
    
    def apply_cli_overrides(self, args):
        """Apply command-line argument overrides"""
        if args.min_duration:
            self.config['defaults']['duration_min'] = args.min_duration
        if args.max_duration:
            self.config['defaults']['duration_max'] = args.max_duration
        if args.min_views:
            self.config['defaults']['min_views'] = args.min_views
        if args.days_back:
            self.config['defaults']['days_back'] = args.days_back
        if args.exclude:
            self.config['filters']['excluded_keywords'].extend(args.exclude.split(','))
        if args.queries:
            self.config['queries'] = args.queries.split(',')
    
    def get(self, key_path, default=None):
        """Get config value using dot notation (e.g., 'defaults.duration_min')"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def save_config(self, filepath='config.json'):
        """Save current configuration to file"""
        with open(filepath, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"✅ Configuration saved to: {filepath}")

# ============================================================================
# VIDEO DISCOVERY ENGINE
# ============================================================================

class VideoDiscovery:
    """Discovers videos using YouTube Data API"""
    
    def __init__(self, api_key, config_manager):
        self.api_key = api_key
        self.config = config_manager
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.videos = []
    
    def search_videos(self):
        """Search for videos based on queries"""
        queries = self.config.get('queries', [])
        days_back = self.config.get('defaults.days_back', 7)
        max_results = self.config.get('defaults.max_results_per_query', 10)
        
        published_after = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
        
        print(f"\n🔍 Searching for videos from the last {days_back} days...")
        
        for query in queries:
            print(f"   Searching: '{query}'")
            try:
                request = self.youtube.search().list(
                    part='snippet',
                    q=query,
                    type='video',
                    maxResults=max_results,
                    publishedAfter=published_after,
                    videoDuration='medium',  # 4-20 minutes
                    order='viewCount'
                )
                response = request.execute()
                
                # Extract video IDs
                video_ids = [item['id']['videoId'] for item in response.get('items', [])]
                
                # Get detailed video info
                if video_ids:
                    self.get_video_details(video_ids)
                    
            except HttpError as e:
                print(f"   ❌ API Error: {e}")
        
        print(f"✅ Found {len(self.videos)} videos before filtering")
    
    def get_video_details(self, video_ids):
        """Get detailed information for videos"""
        try:
            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(video_ids)
            )
            response = request.execute()
            
            for item in response.get('items', []):
                video = self.parse_video_data(item)
                self.videos.append(video)
                
        except HttpError as e:
            print(f"   ❌ Error fetching video details: {e}")
    
    def parse_video_data(self, item):
        """Parse YouTube API response into clean video object"""
        snippet = item['snippet']
        stats = item.get('statistics', {})
        duration_str = item['contentDetails']['duration']
        
        return {
            'id': item['id'],
            'title': snippet['title'],
            'channel': snippet['channelTitle'],
            'channel_id': snippet['channelId'],
            'description': snippet.get('description', ''),
            'thumbnail': snippet['thumbnails']['high']['url'],
            'duration_seconds': self.parse_duration(duration_str),
            'view_count': int(stats.get('viewCount', 0)),
            'like_count': int(stats.get('likeCount', 0)),
            'upload_date': snippet['publishedAt'][:10],
            'url': f"https://www.youtube.com/watch?v={item['id']}"
        }
    
    def parse_duration(self, duration_str):
        """Parse ISO 8601 duration (PT1H2M3S) to seconds"""
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    def filter_videos(self):
        """Apply all configured filters to videos"""
        print(f"\n🔧 Applying filters...")
        
        filtered = self.videos
        
        # Duration filter
        min_dur = self.config.get('defaults.duration_min', 0)
        max_dur = self.config.get('defaults.duration_max', 999999)
        filtered = [v for v in filtered if min_dur <= v['duration_seconds'] <= max_dur]
        print(f"   Duration ({min_dur}-{max_dur}s): {len(filtered)} videos")
        
        # View count filter
        min_views = self.config.get('defaults.min_views', 0)
        filtered = [v for v in filtered if v['view_count'] >= min_views]
        print(f"   Min views ({min_views}): {len(filtered)} videos")
        
        # Like ratio filter
        min_ratio = self.config.get('quality.min_like_ratio', 0)
        if min_ratio > 0:
            filtered = [v for v in filtered 
                       if v['view_count'] > 0 and 
                       (v['like_count'] / v['view_count']) >= min_ratio]
            print(f"   Like ratio (>{min_ratio}): {len(filtered)} videos")
        
        # Keyword filters
        excluded = self.config.get('filters.excluded_keywords', [])
        if excluded:
            filtered = [v for v in filtered 
                       if not any(kw.lower() in v['title'].lower() for kw in excluded)]
            print(f"   Excluded keywords: {len(filtered)} videos")
        
        self.videos = filtered
        print(f"✅ {len(self.videos)} videos after filtering")
    
    def sort_videos(self):
        """Sort videos based on config"""
        sort_by = self.config.get('output.sort_by', 'views')
        
        if sort_by == 'views':
            self.videos.sort(key=lambda x: x['view_count'], reverse=True)
        elif sort_by == 'date':
            self.videos.sort(key=lambda x: x['upload_date'], reverse=True)
        elif sort_by == 'duration':
            self.videos.sort(key=lambda x: x['duration_seconds'])

# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """Generates HTML reports of discovered videos"""
    
    def __init__(self, config_manager):
        self.config = config_manager
    
    def generate_html_report(self, videos):
        """Generate HTML report with thumbnails and video info"""
        output_dir = Path(self.config.get('output.output_dir', './video_reports'))
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = output_dir / f'video_report_{timestamp}.html'
        
        html = self.build_html(videos)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n📄 Report generated: {filepath}")
        return filepath
    
    def build_html(self, videos):
        """Build HTML content"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Video Discovery Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .stats {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .video-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .video-card {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .video-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}
        .thumbnail {{
            width: 100%;
            height: 200px;
            object-fit: cover;
        }}
        .video-info {{
            padding: 15px;
        }}
        .title {{
            font-weight: 600;
            font-size: 16px;
            margin: 0 0 8px 0;
            color: #333;
        }}
        .channel {{
            color: #666;
            font-size: 14px;
            margin-bottom: 8px;
        }}
        .stats-row {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            color: #888;
            margin-bottom: 10px;
        }}
        .btn-approve {{
            display: block;
            width: 100%;
            padding: 10px;
            background: #4CAF50;
            color: white;
            text-align: center;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
        }}
        .btn-approve:hover {{
            background: #45a049;
        }}
    </style>
</head>
<body>
    <h1>🎭 Video Discovery Report</h1>
    <div class="stats">
        <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        <strong>Videos Found:</strong> {len(videos)}<br>
        <strong>Total Views:</strong> {sum(v['view_count'] for v in videos):,}
    </div>
    
    <div class="video-grid">
"""
        
        for video in videos:
            duration_min = video['duration_seconds'] // 60
            duration_sec = video['duration_seconds'] % 60
            
            html += f"""
        <div class="video-card">
            <img src="{video['thumbnail']}" alt="{video['title']}" class="thumbnail">
            <div class="video-info">
                <div class="title">{video['title']}</div>
                <div class="channel">{video['channel']}</div>
                <div class="stats-row">
                    <span>👁️ {video['view_count']:,} views</span>
                    <span>⏱️ {duration_min}:{duration_sec:02d}</span>
                </div>
                <div class="stats-row">
                    <span>👍 {video['like_count']:,} likes</span>
                    <span>📅 {video['upload_date']}</span>
                </div>
                <a href="{video['url']}" target="_blank" class="btn-approve">
                    ▶️ Watch & Approve
                </a>
            </div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html

# ============================================================================
# INTERACTIVE SETUP
# ============================================================================

def interactive_setup():
    """Guide user through creating a config file"""
    print("\n" + "="*50)
    print("  VIDEO DISCOVERY - INTERACTIVE SETUP")
    print("="*50)
    
    config = DEFAULT_CONFIG.copy()
    
    # Duration
    print("\n1️⃣  Video Duration")
    print("   1) Short (1-4 min)")
    print("   2) Medium (4-15 min) [Recommended for kids]")
    print("   3) Long (15+ min)")
    print("   4) Custom")
    choice = input("   Choice [2]: ").strip() or "2"
    
    if choice == "1":
        config['defaults']['duration_min'] = 60
        config['defaults']['duration_max'] = 240
    elif choice == "2":
        config['defaults']['duration_min'] = 240
        config['defaults']['duration_max'] = 900
    elif choice == "3":
        config['defaults']['duration_min'] = 900
        config['defaults']['duration_max'] = 9999
    elif choice == "4":
        min_dur = int(input("   Min duration (seconds): "))
        max_dur = int(input("   Max duration (seconds): "))
        config['defaults']['duration_min'] = min_dur
        config['defaults']['duration_max'] = max_dur
    
    # Views
    print("\n2️⃣  Minimum View Count")
    min_views = input("   Min views [5000]: ").strip()
    config['defaults']['min_views'] = int(min_views) if min_views else 5000
    
    # Days back
    print("\n3️⃣  Search Window")
    days = input("   Days back to search [7]: ").strip()
    config['defaults']['days_back'] = int(days) if days else 7
    
    # Search queries
    print("\n4️⃣  Search Queries")
    print("   Enter search terms (one per line, empty line to finish):")
    queries = []
    while True:
        query = input("   > ").strip()
        if not query:
            break
        queries.append(query)
    if queries:
        config['queries'] = queries
    
    # Excluded keywords
    print("\n5️⃣  Excluded Keywords")
    exclude = input("   Keywords to exclude (comma-separated): ").strip()
    if exclude:
        config['filters']['excluded_keywords'] = [k.strip() for k in exclude.split(',')]
    
    # Save
    print("\n✅ Setup complete!")
    save = input("   Save configuration? [Y/n]: ").strip().lower()
    if save != 'n':
        filepath = input("   Filename [config.json]: ").strip() or "config.json"
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"   💾 Saved to {filepath}")
    
    return config

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Discover great videos with customizable filters')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--profile', type=str, help='Profile name to load')
    parser.add_argument('--setup', action='store_true', help='Run interactive setup')
    parser.add_argument('--min-duration', type=int, help='Minimum duration (seconds)')
    parser.add_argument('--max-duration', type=int, help='Maximum duration (seconds)')
    parser.add_argument('--min-views', type=int, help='Minimum view count')
    parser.add_argument('--days-back', type=int, help='Days back to search')
    parser.add_argument('--exclude', type=str, help='Excluded keywords (comma-separated)')
    parser.add_argument('--queries', type=str, help='Search queries (comma-separated)')
    parser.add_argument('--api-key', type=str, help='YouTube API key')
    
    args = parser.parse_args()
    
    # Interactive setup
    if args.setup:
        interactive_setup()
        return
    
    print("\n" + "="*60)
    print("  🎭 VIDEO DISCOVERY ENGINE")
    print("="*60)
    
    # Get API key
    api_key = args.api_key or os.environ.get('YOUTUBE_API_KEY')
    if not api_key:
        print("\n❌ YouTube API key required!")
        print("   Set via: --api-key YOUR_KEY")
        print("   Or: export YOUTUBE_API_KEY=YOUR_KEY")
        print("\n   Get a key at: https://console.cloud.google.com")
        sys.exit(1)
    
    # Load configuration
    config_manager = ConfigManager(
        config_file=args.config or os.path.join(os.path.dirname(__file__), 'config.json'),
        cli_args=args,
        profile=args.profile
    )
    
    print("\n📋 Active Configuration:")
    print(f"   Duration: {config_manager.get('defaults.duration_min')}-{config_manager.get('defaults.duration_max')}s")
    print(f"   Min Views: {config_manager.get('defaults.min_views'):,}")
    print(f"   Days Back: {config_manager.get('defaults.days_back')}")
    print(f"   Queries: {len(config_manager.get('queries', []))}")
    
    # Discover videos
    discovery = VideoDiscovery(api_key, config_manager)
    discovery.search_videos()
    discovery.filter_videos()
    discovery.sort_videos()
    
    # Generate report
    if discovery.videos:
        generator = ReportGenerator(config_manager)
        report_path = generator.generate_html_report(discovery.videos)
        
        print("\n🎉 Done! Open the report to review videos.")
        print(f"   {report_path}")
    else:
        print("\n😕 No videos found matching your criteria.")
        print("   Try adjusting your filters or search queries.")

if __name__ == "__main__":
    main()