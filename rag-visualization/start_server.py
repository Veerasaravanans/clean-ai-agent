#!/usr/bin/env python3
"""
Simple HTTP server for viewing the 3D visualization
Run this script, then open http://localhost:8000 in your browser
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Check if required files exist
    required_files = ['embedding-viewer.html', 'embedding-engine.js', 'embedding-data.json']
    missing = [f for f in required_files if not Path(f).exists()]
    
    if missing:
        print("⚠️ Missing files:")
        for f in missing:
            print(f"   ❌ {f}")
        if 'embedding-data.json' in missing:
            print("\n💡 Run: python extract_embeddings.py")
        return
    
    print("=" * 60)
    print("🌐 Starting local web server...")
    print("=" * 60)
    print(f"📂 Serving from: {os.getcwd()}")
    print(f"🔗 URL: http://localhost:{PORT}")
    print("\n✅ Server running - opening browser...")
    print("   Press Ctrl+C to stop\n")
    print("=" * 60)
    
    # Start server
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        # Open browser
        webbrowser.open(f'http://localhost:{PORT}/embedding-viewer.html')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped")

if __name__ == "__main__":
    main()
    