#!/usr/bin/env python3
"""
Remote Trigger Server
HTTP server that allows triggering downloads from iPhone/iOS Shortcuts
"""

import subprocess
import sys
import os
import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import argparse

# Global state
download_status = {
    'running': False,
    'started_at': None,
    'completed_at': None,
    'success': None,
    'output': []
}

def run_trigger_download(args_dict=None):
    """Run trigger_download.py as a subprocess
    args_dict: dict of arguments to pass (e.g., {'skip_sync': True, 'cookies': 'chrome'})
    Returns: (success: bool, output: list of lines)
    """
    global download_status
    
    if download_status['running']:
        return False, ["Another download is already running"]
    
    download_status['running'] = True
    download_status['started_at'] = time.time()
    download_status['completed_at'] = None
    download_status['success'] = None
    download_status['output'] = []
    
    script_path = os.path.join(os.path.dirname(__file__), 'trigger_download.py')
    
    # Build command
    cmd = [sys.executable, script_path]
    
    if args_dict:
        if args_dict.get('skip_sync'):
            cmd.append('--skip-sync')
        if args_dict.get('skip_cleanup'):
            cmd.append('--skip-cleanup')
        if args_dict.get('skip_import_imac'):
            cmd.append('--skip-import-imac')
        if args_dict.get('cookies'):
            cmd.extend(['--cookies', args_dict['cookies']])
        if args_dict.get('ssh_mode'):
            cmd.extend(['--ssh', args_dict['ssh_mode']])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        output_lines = result.stdout.split('\n') + result.stderr.split('\n')
        download_status['output'] = output_lines[-50:]  # Keep last 50 lines
        download_status['success'] = (result.returncode == 0)
        download_status['completed_at'] = time.time()
        download_status['running'] = False
        
        return download_status['success'], output_lines
        
    except subprocess.TimeoutExpired:
        download_status['output'] = ["Download timed out after 1 hour"]
        download_status['success'] = False
        download_status['completed_at'] = time.time()
        download_status['running'] = False
        return False, ["Download timed out"]
    except Exception as e:
        download_status['output'] = [f"Error: {str(e)}"]
        download_status['success'] = False
        download_status['completed_at'] = time.time()
        download_status['running'] = False
        return False, [f"Error: {str(e)}"]


class TriggerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for trigger endpoints"""
    
    def do_GET(self):
        """Handle GET requests - status endpoint"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            status = {
                'running': download_status['running'],
                'started_at': download_status['started_at'],
                'completed_at': download_status['completed_at'],
                'success': download_status['success'],
                'output': download_status['output'][-10:]  # Last 10 lines
            }
            
            self.wfile.write(json.dumps(status, indent=2).encode())
            
        elif parsed_path.path == '/':
            # Simple HTML status page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            status_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Download Trigger Server</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: -apple-system, sans-serif; padding: 20px; }}
                    .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                    .running {{ background: #fff3cd; }}
                    .success {{ background: #d4edda; }}
                    .failed {{ background: #f8d7da; }}
                    .idle {{ background: #e2e3e5; }}
                    button {{ padding: 10px 20px; font-size: 16px; margin: 5px; }}
                    pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
                </style>
            </head>
            <body>
                <h1>Download Trigger Server</h1>
                <div class="status {'running' if download_status['running'] else ('success' if download_status['success'] else ('failed' if download_status['success'] is False else 'idle'))}">
                    <strong>Status:</strong> {'Running' if download_status['running'] else ('Completed Successfully' if download_status['success'] else ('Failed' if download_status['success'] is False else 'Idle'))}
                    {f'<br><strong>Started:</strong> {time.ctime(download_status["started_at"])}' if download_status['started_at'] else ''}
                    {f'<br><strong>Completed:</strong> {time.ctime(download_status["completed_at"])}' if download_status['completed_at'] else ''}
                </div>
                <button onclick="triggerDownload()">Trigger Download</button>
                <button onclick="location.reload()">Refresh Status</button>
                <h2>Recent Output</h2>
                <pre>{chr(10).join(download_status['output'][-20:])}</pre>
                <script>
                    function triggerDownload() {{
                        fetch('/trigger', {{method: 'POST'}})
                            .then(() => {{ setTimeout(() => location.reload(), 1000); }})
                            .catch(err => alert('Error: ' + err));
                    }}
                </script>
            </body>
            </html>
            """
            self.wfile.write(status_html.encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """Handle POST requests - trigger endpoint"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/trigger':
            # Parse query parameters
            query_params = parse_qs(parsed_path.query)
            
            # Build args dict from query params
            args_dict = {}
            if 'skip_sync' in query_params:
                args_dict['skip_sync'] = True
            if 'skip_cleanup' in query_params:
                args_dict['skip_cleanup'] = True
            if 'skip_import_imac' in query_params:
                args_dict['skip_import_imac'] = True
            if 'cookies' in query_params:
                args_dict['cookies'] = query_params['cookies'][0]
            if 'ssh_mode' in query_params:
                args_dict['ssh_mode'] = query_params['ssh_mode'][0]
            
            # Run in background thread
            def run_in_background():
                run_trigger_download(args_dict)
            
            thread = threading.Thread(target=run_in_background)
            thread.daemon = True
            thread.start()
            
            self.send_response(202)  # Accepted
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'accepted',
                'message': 'Download triggered',
                'running': True
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        # Only log errors
        if '404' not in str(args):
            super().log_message(format, *args)


def main():
    """Main function to start the HTTP server"""
    parser = argparse.ArgumentParser(
        description="HTTP server for remote triggering of downloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python remote_trigger_server.py                    # Start server on port 8080
  python remote_trigger_server.py --port 9000       # Start server on custom port
  
From iOS Shortcuts or curl:
  curl -X POST http://<your-mac-ip>:8080/trigger
  curl http://<your-mac-ip>:8080/status
        """
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to listen on (default: 8080)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 for all interfaces)'
    )
    
    args = parser.parse_args()
    
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, TriggerHandler)
    
    print("=" * 60)
    print("   REMOTE TRIGGER SERVER")
    print("=" * 60)
    print(f"\n🌐 Server running on http://{args.host}:{args.port}")
    print(f"   Status page: http://localhost:{args.port}/")
    print(f"   Trigger endpoint: POST http://localhost:{args.port}/trigger")
    print(f"   Status endpoint: GET http://localhost:{args.port}/status")
    print("\n📱 To trigger from iPhone:")
    print(f"   POST to http://<your-mac-ip>:{args.port}/trigger")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        httpd.shutdown()
        print("✅ Server stopped")


if __name__ == "__main__":
    main()

