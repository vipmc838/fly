import modal
from modal import web_server

app = modal.App("test-web-server")

@web_server(port=8000)
def simple_server():
    print("✅ simple_server started")  # 希望能在日志中看到
    import http.server
    import socketserver
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), Handler) as httpd:
        print("🌐 Serving on port 8000")
        httpd.serve_forever()
