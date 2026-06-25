#!/usr/bin/env bash
# start.sh — 一鍵啟動本機開發環境
#   1. 先啟動三個依賴服務的容器（PostgreSQL / Redis / MongoDB）
#   2. 最後在前景啟動 FastAPI 開發伺服器（uvicorn）
#
# 註：刻意把資料庫放前面、uvicorn 放最後。uvicorn 會「常駐前景」直到
#     Ctrl-C，所以必須是最後一步；三支 db script 都是 docker run -d
#     （detached），起完馬上返回，不會卡住流程。
set -euo pipefail

# 切換到本 script 所在目錄，確保不論從哪裡呼叫，相對路徑都正確
cd "$(dirname "$0")"

# 1. 啟動三個依賴服務 —— 採「盡力而為」：某支起不來（連接埠被占、Docker
#    沒開…）只印警告、不中斷，因為 app 對外部依賴都有優雅降級。
echo "==> 啟動依賴服務容器"
for s in start-postgres.sh start-redis.sh start-mongodb.sh; do
  echo "--> $s"
  bash "$s" || echo "警告：$s 啟動失敗，伺服器仍會以優雅降級方式繼續啟動"
done

# 2. 在前景啟動 uvicorn（--reload 開發用熱重載；Ctrl-C 結束）
echo "==> 啟動 FastAPI 伺服器：http://localhost:8000（/docs 看 Swagger）"
uv run uvicorn app.main:app --reload
