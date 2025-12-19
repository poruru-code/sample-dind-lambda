#!/bin/sh
set -e

# 環境変数のデフォルト値設定
export UVICORN_BIND_ADDR=${UVICORN_BIND_ADDR:-0.0.0.0:443}
export UVICORN_WORKERS=${UVICORN_WORKERS:-4}
export ENABLE_SSL=${ENABLE_SSL:-true}
export SSL_CERT_PATH=${SSL_CERT_PATH:-/app/config/ssl/server.crt}
export SSL_KEY_PATH=${SSL_KEY_PATH:-/app/config/ssl/server.key}

# Uvicorn起動オプション構築
host=$(echo $UVICORN_BIND_ADDR | cut -d: -f1)
port=$(echo $UVICORN_BIND_ADDR | cut -d: -f2)

UVICORN_ARGS="--host $host --port $port --workers $UVICORN_WORKERS"

if [ "$ENABLE_SSL" = "true" ]; then
    if [ -f "$SSL_CERT_PATH" ] && [ -f "$SSL_KEY_PATH" ]; then
        UVICORN_ARGS="$UVICORN_ARGS --ssl-keyfile $SSL_KEY_PATH --ssl-certfile $SSL_CERT_PATH"
        echo "Starting Gateway Application (HTTPS) on $host:$port..."
    else
        echo "Warning: SSL certificates not found. Falling back to HTTP..."
        echo "  Looking for: $SSL_CERT_PATH, $SSL_KEY_PATH"
        echo "Starting Gateway Application (HTTP) on $host:$port..."
    fi
else
    echo "Starting Gateway Application (HTTP) on $host:$port..."
fi

# アプリケーション起動
# Docker操作は /var/run/docker.sock マウント経由で行う
exec python3 -m uvicorn gateway.app.main:app $UVICORN_ARGS

