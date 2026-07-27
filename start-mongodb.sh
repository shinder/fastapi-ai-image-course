#!/usr/bin/env bash
# start-mongodb.sh — 單獨啟動 MongoDB 容器（不需 docker compose；單元九補充教材）
set -euo pipefail

# 關掉 Git Bash（MSYS）的路徑自動轉換：它會把參數中看起來像 POSIX 絕對路徑的字串改寫成
# Windows 路徑（/data/db → C:/Program Files/Git/data/db），下面 -v 與 --mount 的掛載點
# 就會掛錯地方。兩個變數分別是 Git for Windows 專有與 MSYS2 原生，都設比較保險；
# macOS / Linux 只是多兩個沒人讀的環境變數，不影響。
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

# 同名容器已存在就先移除，讓這支 script 可重複執行
docker rm -f mongo-ai-image 2>/dev/null || true

# mongo image 宣告了「兩個」VOLUME：/data/db 與 /data/configdb。
#   - /data/db：真正存資料的地方 → 掛具名資料卷 mongo-data，持久保留。
#   - /data/configdb：分片叢集（sharded cluster）的 config server 才會用到，單機跑根本用不到
#     （永遠是空的）。放著不管，每次啟動會為它生一個 hash 名稱的空匿名資料卷；這裡用 tmpfs
#     掛成記憶體檔案系統，容器一停就消失——不落地、也不產生匿名資料卷。
docker run -d \
  --name mongo-ai-image \
  -p 27017:27017 \
  -v mongo-data:/data/db \
  --mount type=tmpfs,destination=/data/configdb \
  mongo:8

echo "MongoDB 已啟動：localhost:27017（資料庫：ai_image_db）"
