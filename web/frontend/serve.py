#!/usr/bin/env python3
"""
Simple HTTP server for TrailBlazer frontend
Serves the frontend on port 3000 with CORS enabled
"""
import http.server
import socketserver
from pathlib import Path

PORT = 3000
DIRECTORY = Path(__file__).parent

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)
    
    def end_headers(self):
        """Add CORS headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.end_headers()


def main():
    """Start the HTTP server"""
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print("=" * 60)
        print("TrailBlazer Frontend Server")
        print("=" * 60)
        print(f"Serving: {DIRECTORY}")
        print(f"URL: http://localhost:{PORT}")
        print(f"Open: http://localhost:{PORT}/index.html")
        print("=" * 60)
        print("Server is running. Press Ctrl+C to stop.")
        print()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped")


if __name__ == "__main__":
    main()
