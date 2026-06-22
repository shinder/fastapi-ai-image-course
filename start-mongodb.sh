#!/usr/bin/env bash
# start-mongodb.sh — 單獨啟動 MongoDB 容器（不需 docker compose；單元九補充教材）
set -euo pipefail

# 同名容器已存在就先移除，讓這支 script 可重複執行
docker rm -f mongo-ai-image 2>/dev/null || true

docker run -d \
  --name mongo-ai-image \
  -p 27017:27017 \
  mongo:8

echo "MongoDB 已啟動：localhost:27017（資料庫：ai_image_db）"
