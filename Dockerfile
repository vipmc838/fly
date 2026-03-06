# Dockerfile
FROM whyour/qinglong:latest

WORKDIR /ql

# 安装依赖
RUN set -x \
    && apk update \
    && apk add --no-cache \
        jq \
        gcc \
        musl-dev \
        python3-dev \
        libffi \
        libffi-dev \
        openssl \
        openssl-dev \
        g++ \
        py-pip \
        mysql-dev \
        linux-headers \
        pixman \
        build-base \
        cairo-dev \
        jpeg-dev \
        pango-dev \
        giflib-dev \
        rust \
        cargo \
        alpine-sdk \
        autoconf \
        automake \
        libtool \
        git \
        tzdata \
        curl \
        coreutils \
        chromium \
        chromium-chromedriver \
        nss \
        freetype \
        harfbuzz \
        ca-certificates \
        ttf-freefont \
        font-noto-cjk \
        udev \
        xvfb \
        dbus \
    && pip install --no-cache-dir --break-system-packages \
        user-agent aiohttp jieba ping3 requests selenium \
    && npm install -g \
        axios js-base64 typescript crypto-js jsdom tough-cookie

# 环境变量
ENV TZ=Asia/Shanghai \
    CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_PATH=/usr/lib/chromium/ \
    CHROMIUM_FLAGS="--disable-software-rasterizer --disable-dev-shm-usage --no-sandbox"

# 复制脚本
COPY entrypoint.sh /entrypoint.sh
COPY backup.sh /ql/backup.sh
COPY restore.sh /ql/restore.sh

# 设置执行权限 + 修复换行符
RUN chmod +x /entrypoint.sh /ql/backup.sh /ql/restore.sh \
    && sed -i 's/\r$//' /entrypoint.sh /ql/backup.sh /ql/restore.sh

EXPOSE 5700

ENTRYPOINT ["/entrypoint.sh"]
