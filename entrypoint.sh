#!/bin/bash
set -e

echo "Starting Docker daemon..."
# Docker daemonをバックグラウンドで起動
dockerd-entrypoint.sh &

# Docker daemonの起動を待機
timeout=30
while ! docker info > /dev/null 2>&1; do
    if [ $timeout -le 0 ]; then
        echo "ERROR: Docker daemon failed to start"
        exit 1
    fi
    echo "Waiting for Docker daemon to start... ($timeout seconds remaining)"
    sleep 1
    timeout=$((timeout - 1))
done

echo "Docker daemon started successfully"

# Gatewayイメージのビルド (内部で実行)
echo "Building Gateway image..."
docker build -t my-gateway-api:latest -f gateway/Dockerfile.app .

# Lambda関数イメージをロード
echo "Loading Lambda function images..."
for tarfile in /app/build/lambda-images/*.tar; do
    if [ -f "$tarfile" ]; then
        echo "Loading $tarfile..."
        docker load -i "$tarfile"
    fi
done

echo "Image loading/building completed"
docker images

# 内部用Composeで全コンテナを起動
echo "Starting internal services..."
cd /app
docker compose -f docker-compose.yml up -d

# ログを表示して待機（コンテナ終了を防ぐ）
echo "All services started. Tailing logs..."
docker compose -f docker-compose.yml logs -f
