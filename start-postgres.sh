#!/usr/bin/env bash
# start-postgres.sh — 單獨啟動 PostgreSQL 容器（不需 docker compose）
set -euo pipefail

# 同名容器已存在就先移除，讓這支 script 可重複執行
docker rm -f pg-ai-image 2>/dev/null || true

docker run -d \
  --name pg-ai-image \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=ai_image_db \
  -p 5432:5432 \
  -v pg-data:/var/lib/postgresql/data \
  postgres:17

echo "PostgreSQL 17 已啟動：localhost:5432（資料庫：ai_image_db）"
