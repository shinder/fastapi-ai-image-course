#!/usr/bin/env bash
# stop-containers.sh — 一鍵移除 start.sh 啟動的三個依賴服務容器
#   （PostgreSQL / Redis / MongoDB）
#
# 註：用 docker rm -fv 把容器「刪掉」（正在跑的會先 kill 再移除）。
#     start-*.sh 已從源頭杜絕匿名資料卷——redis 的 /data、mongo 的 /data/configdb 都改掛
#     tmpfs（記憶體），其餘要保留的路徑掛具名資料卷——所以正常情況根本不會產生匿名資料卷。
#     這裡仍保留 -v 當「收工防呆」：萬一日後新增的服務漏處理了某個 VOLUME，收工時會把那個
#     匿名資料卷一起帶走、不留垃圾。-v「只刪匿名資料卷、不碰具名資料卷」，故具名的
#     pg-data / mongo-data 一律保留，資料仍在；下次 start.sh 會重新 docker run 並接回。
set -euo pipefail

# 採「盡力而為」：某個容器不存在（沒起過、已移除）只印警告、不中斷，
# 與 start.sh 的優雅降級精神一致。
echo "==> 移除依賴服務容器"
for c in pg-ai-image redis-ai-image mongo-ai-image; do
  echo "--> $c"
  docker rm -fv "$c" >/dev/null 2>&1 \
    && echo "已移除 $c" \
    || echo "警告：找不到容器 $c，略過（可能尚未啟動）"
done
