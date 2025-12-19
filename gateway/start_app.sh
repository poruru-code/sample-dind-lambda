#!/bin/sh
set -e

# 環境変数のデフォルト値設定
export UVICORN_BIND_ADDR=${UVICORN_BIND_ADDR:-0.0.0.0:8000}
export UVICORN_WORKERS=${UVICORN_WORKERS:-4}

# Uvicorn起動オプション構築
host=$(echo $UVICORN_BIND_ADDR | cut -d: -f1)
port=$(echo $UVICORN_BIND_ADDR | cut -d: -f2)

echo "Starting Gateway Application on $host:$port..."

# アプリケーション起動
# Docker操作は /var/run/docker.sock マウント経由で行う
exec python3 -m uvicorn gateway.app.main:app --host $host --port $port --workers $UVICORN_WORKERS
