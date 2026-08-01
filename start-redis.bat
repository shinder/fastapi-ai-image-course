@echo off
rem start-redis.bat — 單獨啟動 Redis 容器（Windows 版，對應 start-redis.sh）
rem 教材 單元九 補充教材
rem
rem --save "" --appendonly no：關掉 RDB / AOF 兩種持久化。本專案的 Redis 是「可丟的快取」，
rem 清空不影響正確性，不寫硬碟還省下 fork 存檔的開銷。
rem --mount type=tmpfs,destination=/data：用記憶體檔案系統蓋掉 redis image 宣告的 VOLUME，
rem 既擋掉匿名資料卷，容器一停 /data 也隨之消失。

docker rm -f redis-ai-image >nul 2>&1

docker run -d ^
  --name redis-ai-image ^
  -p 6379:6379 ^
  --mount type=tmpfs,destination=/data ^
  redis:7-alpine ^
  redis-server --save "" --appendonly no

echo Redis 已啟動：localhost:6379（純記憶體快取，重啟即清）
