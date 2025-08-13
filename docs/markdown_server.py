#!/usr/bin/env python3
"""
Simple Markdown Server
Renders markdown files as readable HTML
"""

import http.server
import socketserver
import os
import markdown
from urllib.parse import urlparse, unquote

class MarkdownHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse the URL
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)
        
        # If it's a markdown file, render it
        if path.endswith('.md'):
            file_path = os.path.join(os.getcwd(), path.lstrip('/'))
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Convert markdown to HTML
                html_content = markdown.markdown(
                    md_content,
                    extensions=['tables', 'fenced_code', 'codehilite', 'toc']
                )
                
                # Create full HTML page
                full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{os.path.basename(file_path)}</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 10px;
        }}
        h1 {{
            color: #e74c3c;
            border-bottom: 3px solid #e74c3c;
        }}
        h2 {{
            color: #3498db;
        }}
        h3 {{
            color: #9b59b6;
        }}
        code {{
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            color: inherit;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 0;
            padding-left: 20px;
            color: #7f8c8d;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .nav {{
            background: #34495e;
            padding: 15px;
            margin-bottom: 30px;
            border-radius: 8px;
        }}
        .nav a {{
            color: white;
            text-decoration: none;
            margin-right: 20px;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.3s;
        }}
        .nav a:hover {{
            background-color: #2c3e50;
        }}
        .file-info {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 0.9em;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">📁 All Files</a>
        <a href="/SECTOR_TRACKING_IMPLEMENTATION_PLAN.md">📋 Sector Tracking</a>
        <a href="/DATA_FLOW_ARCHITECTURE.md">📊 Data Flow</a>
        <a href="/COMPONENT_INTERACTION_ARCHITECTURE.md">🔗 Components</a>
    </div>
    
    <div class="container">
        <div class="file-info">
            📄 <strong>{os.path.basename(file_path)}</strong> | 
            📁 {os.path.dirname(file_path)} | 
            📏 {len(md_content)} characters
        </div>
        
        {html_content}
    </div>
</body>
</html>
"""
                
                # Send the HTML response
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(full_html.encode('utf-8'))
                return
        
        # For non-markdown files, use default handler
        super().do_GET()

if __name__ == "__main__":
    PORT = 8080
    
    with socketserver.TCPServer(("", PORT), MarkdownHandler) as httpd:
        print(f"🚀 Markdown Server running on http://localhost:{PORT}")
        print(f"📁 Serving from: {os.getcwd()}")
        print(f"📋 Try: http://localhost:{PORT}/SECTOR_TRACKING_IMPLEMENTATION_PLAN.md")
        print("Press Ctrl+C to stop")
        httpd.serve_forever()
