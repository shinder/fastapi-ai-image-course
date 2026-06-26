#!/usr/bin/env bash
# start-redis.sh — 單獨啟動 Redis 容器（不需 docker compose）
set -euo pipefail

# 同名容器已存在就先移除，讓這支 script 可重複執行
docker rm -f redis-ai-image 2>/dev/null || true

# redis 在本專案是「可丟的快取」（cache / rate-limit / lock / 任務狀態，全採盡力而為，
# 清空也不影響正確性），不需要持久化。用 redis-server 的 --save '' --appendonly no 關掉
# RDB / AOF 兩種持久化：純記憶體快取、不寫硬碟，也省下 fork 存檔的開銷。
# （順帶避開一個坑：下面的 tmpfs 預設以 mode=755、root 擁有掛載，而 redis 是以非 root 的
#  redis 使用者執行；若留著預設持久化，稍後 BGSAVE 會因無法寫入 /data 而失敗，甚至連帶
#  拒絕寫入。關掉持久化就根本不碰 /data，從源頭免除這個問題。）
#
# 另外，redis image 宣告了 VOLUME /data，只要不掛東西蓋過去，docker 每次啟動就會為它生一個
# hash 名稱的匿名資料卷。這裡用 tmpfs（記憶體檔案系統）把 /data 蓋掉：既擋掉匿名資料卷，
# 容器一停 /data 也隨之消失，完全不落地——比給它具名資料卷更貼合「快取」語意。
docker run -d \
  --name redis-ai-image \
  -p 6379:6379 \
  --mount type=tmpfs,destination=/data \
  redis:7-alpine \
  redis-server --save '' --appendonly no

echo "Redis 已啟動：localhost:6379（純記憶體快取，重啟即清）"
