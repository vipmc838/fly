FROM node:20-alpine

WORKDIR /app

RUN apk add --no-cache \
    bash \
    git \
    curl \
    tar \
    openssl \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    python3 \
    py3-pip \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev

COPY install.sh backup.sh restore.sh entrypoint.sh /app/
RUN chmod +x /app/*.sh

ENV DATA_DIR=/ql/data \
    PORT=8080 \
    NODE_ENV=production \
    CHROME_BIN=/usr/bin/chromium-browser \
    CHROME_PATH=/usr/lib/chromium/ \
    CHROMIUM_FLAGS="--disable-software-rasterizer --disable-dev-shm-usage --no-sandbox"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/system || exit 1

CMD ["/app/entrypoint.sh"]
