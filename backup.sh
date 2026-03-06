#!/bin/bash
set -u

###########################################
#  青龙面板备份脚本
###########################################

log_info()  { echo "[INFO] $*"; }
log_ok()    { echo "[SUCCESS] $*"; }
log_error() { echo "[ERROR] $*"; }

# 检查配置
if [ -z "${GH_BACKUP_REPO:-}" ] || [ -z "${GH_TOKEN:-}" ]; then
    log_info "未配置 GH_BACKUP_REPO 或 GH_TOKEN，跳过备份"
    exit 0
fi

# 配置
DATA_DIR="${DATA_DIR:-/ql/data}"
GH_BACKUP_BRANCH="${GH_BACKUP_BRANCH:-main}"
KEEP="${KEEP_BACKUPS:-5}"
API_BASE="https://api.github.com/repos/$GH_BACKUP_REPO"
TIMESTAMP=$(TZ='Asia/Shanghai' date +"%Y%m%d_%H%M%S")
BACKUP_FILE="ql_backup_${TIMESTAMP}.tar.gz"
BACKUP_DIRS="config db scripts"
TEMP_DIR="/tmp/ql-backup-$$"

log_info "开始备份: $BACKUP_FILE"

# 创建临时目录
mkdir -p "$TEMP_DIR/data"
cd "$TEMP_DIR" || exit 1

# 复制数据
log_info "复制数据..."
for dir in $BACKUP_DIRS; do
    [ -d "$DATA_DIR/$dir" ] && cp -R "$DATA_DIR/$dir" "$TEMP_DIR/data/" && echo "  ✓ $dir"
done

# 压缩
log_info "压缩数据..."
if [ -n "${BACKUP_PASS:-}" ]; then
    tar czf - -C "$TEMP_DIR" data/ | openssl enc -aes-256-cbc -salt -pbkdf2 \
        -pass pass:"$BACKUP_PASS" -out "$BACKUP_FILE"
else
    tar czf "$BACKUP_FILE" -C "$TEMP_DIR" data/
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_info "文件大小: $BACKUP_SIZE"

# Base64 编码
base64 -w 0 "$BACKUP_FILE" > content.b64 2>/dev/null || base64 "$BACKUP_FILE" > content.b64

B64_SIZE=$(wc -c < content.b64)
if [ "$B64_SIZE" -gt 100000000 ]; then
    log_error "文件太大（>100MB）"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 上传备份
log_info "上传备份..."
EXISTING_SHA=$(curl -s -H "Authorization: token $GH_TOKEN" \
    "$API_BASE/contents/$BACKUP_FILE?ref=$GH_BACKUP_BRANCH" 2>/dev/null \
    | jq -r '.sha // empty')

if [ -n "$EXISTING_SHA" ]; then
    jq -n --rawfile content content.b64 \
          --arg msg "更新: $BACKUP_FILE" \
          --arg sha "$EXISTING_SHA" \
          --arg branch "$GH_BACKUP_BRANCH" \
          '{message:$msg,content:$content,sha:$sha,branch:$branch}' > payload.json
else
    jq -n --rawfile content content.b64 \
          --arg msg "备份: $BACKUP_FILE ($BACKUP_SIZE)" \
          --arg branch "$GH_BACKUP_BRANCH" \
          '{message:$msg,content:$content,branch:$branch}' > payload.json
fi

RESPONSE=$(curl -s -X PUT \
    -H "Authorization: token $GH_TOKEN" \
    -H "Content-Type: application/json" \
    -d @payload.json \
    "$API_BASE/contents/$BACKUP_FILE")

rm -f payload.json content.b64

if ! echo "$RESPONSE" | jq -e '.content.sha' >/dev/null 2>&1; then
    log_error "上传失败: $(echo "$RESPONSE" | jq -r '.message // "未知错误"')"
    rm -rf "$TEMP_DIR"
    exit 1
fi
log_ok "备份上传成功"

# 更新 README
log_info "更新 README..."
README_SHA=$(curl -s -H "Authorization: token $GH_TOKEN" \
    "$API_BASE/contents/README.md?ref=$GH_BACKUP_BRANCH" | jq -r '.sha // empty')

README_TEXT="# 青龙面板备份

**最新:** \`$BACKUP_FILE\`  
**时间:** $(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')  
**大小:** $BACKUP_SIZE  
**平台:** Fly.io"

README_B64=$(echo -n "$README_TEXT" | base64 -w 0 2>/dev/null || echo -n "$README_TEXT" | base64)

if [ -n "$README_SHA" ]; then
    PAYLOAD="{\"message\":\"更新README\",\"content\":\"$README_B64\",\"sha\":\"$README_SHA\",\"branch\":\"$GH_BACKUP_BRANCH\"}"
else
    PAYLOAD="{\"message\":\"创建README\",\"content\":\"$README_B64\",\"branch\":\"$GH_BACKUP_BRANCH\"}"
fi

curl -s -X PUT -H "Authorization: token $GH_TOKEN" \
    -H "Content-Type: application/json" -d "$PAYLOAD" \
    "$API_BASE/contents/README.md" >/dev/null

# 清理旧备份
log_info "清理旧备份（保留 $KEEP 个）..."
OLD_BACKUPS=$(curl -s -H "Authorization: token $GH_TOKEN" \
    "$API_BASE/contents?ref=$GH_BACKUP_BRANCH" \
    | jq -r '.[].name' | grep '^ql_backup_.*\.tar\.gz$' | sort -r \
    | tail -n +$((KEEP + 1)))

for old_file in $OLD_BACKUPS; do
    OLD_SHA=$(curl -s -H "Authorization: token $GH_TOKEN" \
        "$API_BASE/contents/$old_file?ref=$GH_BACKUP_BRANCH" | jq -r '.sha')
    curl -s -X DELETE -H "Authorization: token $GH_TOKEN" \
        -d "{\"message\":\"删除旧备份\",\"sha\":\"$OLD_SHA\",\"branch\":\"$GH_BACKUP_BRANCH\"}" \
        "$API_BASE/contents/$old_file" >/dev/null
    echo "  已删除: $old_file"
done

rm -rf "$TEMP_DIR"
log_ok "备份完成: $BACKUP_FILE 🎉"
