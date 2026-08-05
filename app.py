import os, sys, subprocess, platform, json, shutil, threading, traceback
from urllib.request import urlopen, Request

import streamlit as st

# ================== 工具函数 ==================
def get_python_version():
    return f"{sys.version_info.major}.{sys.version_info.minor}"

def get_arch():
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "amd64"
    if machine in ("aarch64", "arm64"):
        return "arm64"
    raise RuntimeError(f"不支持的架构: {machine}")

def get_latest_tag(python_version: str) -> str:
    url = "https://api.github.com/repos/oyz8/agent-v1-so/tags?per_page=100"
    req = Request(url, headers={"User-Agent": "Python"})
    with urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    prefix = f"main.so-py{python_version}-"
    candidates = []
    for item in data:
        tag = item["name"]
        if tag.startswith(prefix):
            try:
                num = int(tag[len(prefix):])
                candidates.append((num, tag))
            except ValueError:
                pass
    if not candidates:
        raise RuntimeError(f"未找到 Python {python_version} 的编译版本")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

def download_so(target_path: str):
    py_ver = get_python_version()
    arch = get_arch()
    tag = get_latest_tag(py_ver)
    dl_url = f"https://github.com/oyz8/agent-v1-so/releases/download/{tag}/main-{arch}.so"
    print(f"[INFO] 下载 {dl_url}")
    req = Request(dl_url, headers={"User-Agent": "Python"})
    with urlopen(req) as resp:
        with open(target_path, "wb") as f:
            shutil.copyfileobj(resp, f)
    print(f"[INFO] 已保存到 {target_path}")

def ensure_so():
    so_file = "main.so"
    if not os.path.isfile(so_file):
        print("[INFO] main.so 不存在，开始下载...")
        download_so(so_file)
    else:
        print("[INFO] 检查并更新 main.so ...")
        try:
            os.remove(so_file)
        except Exception:
            pass
        download_so(so_file)

def install_dependencies():
    required = ["grpcio", "grpcio-tools", "protobuf", "pyyaml", "psutil", "aiohttp"]
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            print(f"[INFO] 安装依赖 {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", pkg])

# ================== Agent 启动函数 ==================
def run_agent():
    import logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s: %(message)s")
    os.environ["SILENT"] = "false"          # 强制输出日志
    os.environ["DEBUG"] = "true"            # 可选，开启更详细日志

    try:
        from main import WorkerApp
        print("[Agent] WorkerApp imported", flush=True)
    except Exception:
        traceback.print_exc()
        print("[FATAL] Failed to import WorkerApp from main.so", flush=True)
        return

    try:
        app = WorkerApp(config_path=None)   # 完全依赖环境变量
        print("[Agent] WorkerApp created, starting run...", flush=True)
        app.run()
    except Exception:
        traceback.print_exc()
        print("[FATAL] Agent.run() failed", flush=True)

# ================== 主流程 ==================
if __name__ == "__main__":
    # ---- 一次性初始化 ----
    if "init_done" not in st.session_state:
        st.session_state.init_done = False

    if not st.session_state.init_done:
        # 1. 注入 Secrets 到环境变量
        try:
            for key, val in st.secrets.items():
                os.environ[key] = str(val)
            print(f"[INIT] Loaded secrets: {list(st.secrets.keys())}", flush=True)
        except Exception as e:
            print(f"[INIT] No secrets found or error: {e}", flush=True)

        # 2. 安装依赖（仅一次）
        install_dependencies()

        # 3. 下载 main.so（仅一次）
        ensure_so()

        # 4. 验证导入
        try:
            from main import WorkerApp
            print("[INIT] main.so import test OK", flush=True)
        except Exception:
            traceback.print_exc()
            print("[FATAL] main.so import test FAILED", flush=True)

        st.session_state.init_done = True

    # ---- 启动 Agent 线程（仅一次） ----
    if "agent_started" not in st.session_state:
        print("[INIT] Starting agent thread...", flush=True)
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
        st.session_state.agent_started = True

    # ---- Streamlit 界面 ----
    st.set_page_config(page_title="Hello", layout="centered")
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=800, scrolling=True)
    except FileNotFoundError:
        st.write("Hello, World!")
