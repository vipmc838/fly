#!/bin/bash
set -e

log_info() { echo "[$(date '+%H:%M:%S')] [INFO] $*"; }
log_ok() { echo "[$(date '+%H:%M:%S')] [OK] $*"; }
log_error() { echo "[$(date '+%H:%M:%S')] [ERROR] $*"; }
log_warn() { echo "[$(date '+%H:%M:%S')] [WARN] $*"; }

# 配置（Fly.io 使用 8080 端口）
DATA_DIR="${DATA_DIR:-/ql/data}"
PORT="${PORT:-8080}"
INSTALL_DIR="/ql"

# 防止重复启动
LOCK_FILE=/tmp/start.lock
if [ -f "$LOCK_FILE" ]; then
    log_error "检测到锁文件，可能已在运行"
    exit 1
fi
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

echo "=========================================="
echo "  青龙面板启动 (Fly.io)"
echo "=========================================="
echo "  端口: $PORT"
echo "  数据目录: $DATA_DIR"
echo "  GitHub 备份: ${GH_BACKUP_REPO:-未配置}"
echo "=========================================="

# 1. 运行时安装青龙
if [ ! -d "$INSTALL_DIR" ]; then
    log_info "首次启动，开始安装青龙..."
    if ! bash /app/install.sh; then
        log_error "安装失败"
        exit 1
    fi
    log_ok "安装完成"
else
    log_info "青龙已安装，跳过安装步骤"
fi

# 2. 配置 Git
log_info "配置 Git..."
git config --global user.email "${GH_EMAIL:-qinglong@bot.com}"
git config --global user.name "${GH_USER:-QingLong-Bot}"
git config --global init.defaultBranch main
git config --global --add safe.directory '*'

# 3. 恢复数据
if [ -n "${GH_BACKUP_REPO:-}" ] && [ -n "${GH_TOKEN:-}" ]; then
    log_info "尝试恢复备份数据..."
    if bash /app/restore.sh; then
        log_ok "数据恢复成功"
    else
        log_warn "恢复失败或无备份，使用全新安装"
    fi
else
    log_info "未配置 GitHub 备份，跳过恢复"
fi

# 4. 写入管理员账户
if [ -n "${ADMIN_USERNAME:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
    AUTH_FILE="$DATA_DIR/config/auth.json"
    if [ ! -f "$AUTH_FILE" ]; then
        log_info "创建管理员账户..."
        mkdir -p "$(dirname "$AUTH_FILE")"
        cat > "$AUTH_FILE" <<EOF
{
  "username": "$ADMIN_USERNAME",
  "password": "$ADMIN_PASSWORD",
  "salt": "",
  "hash": ""
}
EOF
        log_ok "管理员账户已设置"
    else
        log_info "管理员账户已存在，跳过"
    fi
else
    log_warn "未设置 ADMIN_USERNAME 或 ADMIN_PASSWORD"
fi

# 5. 设置环境变量
export CHROME_BIN=/usr/bin/chromium-browser
export CHROME_PATH=/usr/lib/chromium/
export CHROMIUM_FLAGS="--disable-software-rasterizer --disable-dev-shm-usage --no-sandbox"
export NODE_ENV=production
export HOST=0.0.0.0

cd "$INSTALL_DIR"

# 6. 创建 .env 文件
log_info "创建 .env 配置..."
cat > "$INSTALL_DIR/.env" <<EOF
# 青龙面板配置
NODE_ENV=production
PORT=${PORT}
DATA_DIR=${DATA_DIR}
HOST=0.0.0.0
EOF
log_ok ".env 文件已创建"

# 7. 编译 TypeScript（如果需要）
if [ -f "back/app.ts" ] && [ ! -f "static/build/app.js" ]; then
    log_info "检测到 TypeScript 源码，开始编译..."
    if npm run build:back -- --skipLibCheck 2>&1 | tee /tmp/build.log; then
        log_ok "编译完成"
    else
        log_warn "编译有警告，但继续启动"
    fi
fi

# 8. 检测启动文件
START_FILE=""
log_info "检测启动文件..."

if [ -f "static/build/app.js" ]; then
    START_FILE="static/build/app.js"
    log_info "找到: static/build/app.js"
elif [ -f "build/app.js" ]; then
    START_FILE="build/app.js"
    log_info "找到: build/app.js"
elif [ -f "server.js" ]; then
    START_FILE="server.js"
    log_info "找到: server.js"
else
    log_error "找不到启动文件"
    exit 1
fi

log_info "使用启动文件: $START_FILE"

# 9. 启动青龙
log_info "启动青龙面板..."
node "$START_FILE" &
QL_PID=$!
log_info "进程 PID: $QL_PID"

# 10. 等待服务就绪
log_info "等待服务启动..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s "http://0.0.0.0:${PORT}/api/system" >/dev/null 2>&1; then
        log_ok "API 服务已就绪"
        break
    fi
    
    if ! kill -0 $QL_PID 2>/dev/null; then
        log_error "进程已退出，查看最后的日志："
        tail -50 "$DATA_DIR/log/system.log" 2>/dev/null || echo "无日志文件"
        exit 1
    fi
    
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $((WAITED % 10)) -eq 0 ]; then
        echo "  等待中... ($WAITED/$MAX_WAIT 秒)"
    fi
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log_warn "服务启动超时"
    if kill -0 $QL_PID 2>/dev/null; then
        log_info "进程仍在运行，继续..."
    else
        log_error "进程已退出"
        exit 1
    fi
fi

# 11. 显示访问信息
echo "=========================================="
log_ok "启动完成"
echo "  内部端口: $PORT"
echo "  管理员: ${ADMIN_USERNAME:-未设置}"
echo "  备份命令: fly ssh console -C '/app/backup.sh'"
echo "=========================================="

# 12. 保持运行并转发信号
trap "kill $QL_PID 2>/dev/null" SIGTERM SIGINT
wait $QL_PID
