import os, sys, subprocess, platform, json, shutil, threading, traceback, asyncio
from urllib.request import urlopen, Request

import streamlit as st

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
    req = Request(dl_url, headers={"User-Agent": "Python"})
    with urlopen(req) as resp:
        with open(target_path, "wb") as f:
            shutil.copyfileobj(resp, f)

def ensure_so():
    so_file = "main.so"
    if os.path.isfile(so_file):
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
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", pkg])

def run_agent():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    os.environ["SILENT"] = "false"
    try:
        import main
        server = os.environ.get("NZ_SERVER", os.environ.get("SERVER", ""))
        secret = os.environ.get("NZ_CLIENT_SECRET", os.environ.get("CLIENT_SECRET", ""))
        uuid = os.environ.get("NZ_UUID", os.environ.get("UUID", ""))
        if not main.DEPS_OK:
            raise SystemExit("Agent dependencies missing")
        if not server or not secret:
            raise SystemExit("Server or secret not configured")
        asyncio.run(main.start_worker({"server": server, "secret": secret, "uuid": uuid}))
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    if "init_done" not in st.session_state:
        st.session_state.init_done = False

    if not st.session_state.init_done:
        try:
            for key, val in st.secrets.items():
                os.environ[key] = str(val)
        except Exception:
            pass

        install_dependencies()
        ensure_so()
        st.session_state.init_done = True

    if "agent_started" not in st.session_state:
        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()
        st.session_state.agent_started = True

    st.set_page_config(page_title="Hello", layout="centered")
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=800, scrolling=True)
    except FileNotFoundError:
        st.write("Hello, World!")
