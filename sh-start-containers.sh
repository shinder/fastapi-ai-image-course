#!/usr/bin/env bash
# sh-start-containers.sh — 只啟動三個依賴服務的容器（PostgreSQL / Redis / MongoDB）
#   不啟動 FastAPI 開發伺服器——伺服器另開終端機自己跑：
#       uv run fastapi dev app/main.py
#   想「容器 + 伺服器」一鍵全起的，用 sh-start.sh。
set -euo pipefail

# 切換到本 script 所在目錄，確保不論從哪裡呼叫，相對路徑都正確
cd "$(dirname "$0")"

# 採「盡力而為」：某支起不來（連接埠被占、Docker 沒開…）只印警告、不中斷，
# 繼續啟動其餘容器——app 對外部依賴都有優雅降級，少一個服務也能開發。
echo "==> 啟動依賴服務容器"
for s in sh-start-postgres.sh sh-start-redis.sh sh-start-mongodb.sh; do
  echo "--> $s"
  bash "$s" || echo "警告：$s 啟動失敗，繼續啟動其餘容器"
done

echo "==> 容器啟動完成。開發伺服器請另行執行：uv run fastapi dev app/main.py"
