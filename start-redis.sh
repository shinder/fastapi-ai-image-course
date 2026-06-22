#!/usr/bin/env bash
# start-redis.sh — 單獨啟動 Redis 容器（不需 docker compose）
set -euo pipefail

# 同名容器已存在就先移除，讓這支 script 可重複執行
docker rm -f redis-ai-image 2>/dev/null || true

docker run -d \
  --name redis-ai-image \
  -p 6379:6379 \
  redis:7-alpine

echo "Redis 已啟動：localhost:6379"
