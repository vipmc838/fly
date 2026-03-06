#!/bin/bash
set -e

# ===========================================
#  青龙面板 - Fly.io 启动脚本
# ===========================================

log_info()  { echo "[INFO] $*"; }
log_ok()    { echo "[SUCCESS] $*"; }
log_warn()  { echo "[WARN] $*"; }
log_error() { echo "[ERROR] $*"; }

# 配置
BACKUP_SCRIPT="/ql/backup.sh"
RESTORE_SCRIPT="/ql/restore.sh"
DATA_DIR="${DATA_DIR:-/ql/data}"
PORT="${PORT:-5700}"

# 防止重复启动
LOCK_FILE=/tmp/qinglong_start.lock
if [ -f "$LOCK_FILE" ]; then
    log_warn "已检测到启动锁文件，退出"
    exit 0
fi
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

# ===========================================
# 保活函数（Fly.io 有持久化卷，保活非必须）
# ===========================================
add_visit_task() {
    if [ -z "${PROJECT_URL:-}" ]; then
        log_info "未设置 PROJECT_URL，跳过自动保活"
        return 0
    fi

    log_info "添加自动保活任务: $PROJECT_URL"
    if curl -s -X POST "https://trans.ct8.pl/add-url" \
        -H "Content-Type: application/json" \
        -d "{\"url\":\"$PROJECT_URL\"}" >/dev/null 2>&1; then
        log_ok "自动保活任务添加成功"
    else
        log_warn "添加自动保活任务失败（服务可能不可用）"
    fi
}

# ===========================================
# 配置 Git
# ===========================================
setup_git() {
    log_info "配置 Git..."
    git config --global user.email "${GH_EMAIL:-qinglong@fly.io}"
    git config --global user.name "${GH_USER:-QingLong-Backup}"
    git config --global init.defaultBranch main
}

# ===========================================
# 恢复数据（仅在持久化卷为空时恢复）
# ===========================================
restore_on_startup() {
    # Fly.io 有持久化卷，只在数据目录为空时才恢复
    if [ -d "$DATA_DIR/config" ] && [ "$(ls -A $DATA_DIR/config 2>/dev/null)" ]; then
        log_info "检测到已有数据（持久化卷），跳过恢复"
        return 0
    fi

    if [ -z "${GH_BACKUP_REPO:-}" ] || [ -z "${GH_TOKEN:-}" ]; then
        log_info "未配置 GitHub 备份，跳过恢复"
        return 0
    fi

    log_info "持久化卷为空，尝试从 GitHub 恢复数据..."

    if [ ! -f "$RESTORE_SCRIPT" ]; then
        log_warn "恢复脚本不存在: $RESTORE_SCRIPT"
        return 0
    fi

    if bash "$RESTORE_SCRIPT"; then
        log_ok "数据恢复成功"
    else
        log_warn "恢复失败或无备份，使用全新安装"
    fi
}

# ===========================================
# 写入管理员账户
# ===========================================
write_auth_json() {
    if [ -z "${ADMIN_USERNAME:-}" ] || [ -z "${ADMIN_PASSWORD:-}" ]; then
        log_info "未设置管理员账户，跳过"
        return 0
    fi

    local auth_file="$DATA_DIR/config/auth.json"
    if [ -f "$auth_file" ]; then
        log_info "auth.json 已存在，跳过"
        return 0
    fi

    log_info "写入管理员账户..."
    mkdir -p "$(dirname "$auth_file")"
    cat > "$auth_file" <<EOF
{"username":"$ADMIN_USERNAME","password":"$ADMIN_PASSWORD","salt":"","hash":""}
EOF
    log_ok "auth.json 已生成"
}

# ===========================================
# 启动青龙面板
# ===========================================
start_qinglong() {
    log_info "启动青龙面板 (端口: $PORT)..."

    # 确保数据目录结构存在
    mkdir -p "$DATA_DIR/config" "$DATA_DIR/db" "$DATA_DIR/scripts" "$DATA_DIR/log"

    /ql/docker/docker-entrypoint.sh &
    QL_PID=$!
    log_info "青龙面板 PID: $QL_PID"

    local count=0 max_wait=120
    while [ $count -lt $max_wait ]; do
        if curl -s "http://0.0.0.0:${PORT}/api/system" >/dev/null 2>&1; then
            log_ok "API 服务已就绪"
            return 0
        fi
        sleep 2
        count=$((count + 2))
        echo "  等待 API... ($count/$max_wait)"
    done

    log_warn "API 启动超时，继续运行"
}

# ===========================================
# 显示配置
# ===========================================
show_config() {
    echo "=========================================="
    echo "  青龙面板 - Fly.io 部署"
    echo "=========================================="
    echo "  端口: $PORT"
    echo "  数据目录: $DATA_DIR"
    echo "  GitHub 仓库: ${GH_BACKUP_REPO:-未配置}"
    echo "  GitHub 分支: ${GH_BACKUP_BRANCH:-main}"
    echo "  保留备份数: ${KEEP_BACKUPS:-5}"
    echo "  加密备份: $([ -n "${BACKUP_PASS:-}" ] && echo '是' || echo '否')"
    echo "  自动保活: $([ -n "${PROJECT_URL:-}" ] && echo '是' || echo '否')"
    echo "  备份命令: task /ql/backup.sh"
    echo "=========================================="
}

# ===========================================
# 主函数
# ===========================================
main() {
    show_config
    setup_git
    restore_on_startup
    write_auth_json
    start_qinglong
    add_visit_task

    echo "=========================================="
    log_ok "初始化完成"
    echo "  - 面板地址: https://$(cat /etc/hostname 2>/dev/null || echo 'your-app').fly.dev"
    echo "=========================================="

    wait
}

main "$@"
