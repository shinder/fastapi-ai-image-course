@echo off
rem start-redis.bat — 單獨啟動 Redis 容器（Windows CMD 版，對應 start-redis.sh）
rem
rem 編碼：本檔以 UTF-8「無 BOM」儲存，chcp 65001 把主控台切成 UTF-8，中文才不會變亂碼。
chcp 65001 >nul
setlocal

rem 同名容器已存在就先移除，讓這支腳本可重複執行
docker rm -f redis-ai-image >nul 2>&1

rem redis 在本專案是「可丟的快取」（cache / rate-limit / lock / 任務狀態，全採盡力而為，
rem 清空也不影響正確性），不需要持久化。用 redis-server 的 --save "" --appendonly no 關掉
rem RDB / AOF 兩種持久化：純記憶體快取、不寫硬碟，也省下 fork 存檔的開銷。
rem （順帶避開一個坑：下面的 tmpfs 預設以 mode=755、root 擁有掛載，而 redis 是以非 root 的
rem  redis 使用者執行；若留著預設持久化，稍後 BGSAVE 會因無法寫入 /data 而失敗。）
rem
rem 另外，redis image 宣告了 VOLUME /data，只要不掛東西蓋過去，docker 每次啟動就會為它生一個
rem hash 名稱的匿名資料卷。這裡用 tmpfs（記憶體檔案系統）把 /data 蓋掉：既擋掉匿名資料卷，
rem 容器一停 /data 也隨之消失，完全不落地——比給它具名資料卷更貼合「快取」語意。
rem
rem 註：--save "" 的空字串在 cmd 要寫成一對雙引號（bash 版寫的是 ''，cmd 不認單引號）。
docker run -d ^
  --name redis-ai-image ^
  -p 6379:6379 ^
  --mount type=tmpfs,destination=/data ^
  redis:7-alpine ^
  redis-server --save "" --appendonly no

rem cmd 沒有 set -e，失敗要自己查 errorlevel（語義是 errorlevel >= 1，也就是「失敗」）
if errorlevel 1 (
  echo 錯誤：Redis 容器啟動失敗，請確認 Docker Desktop 已啟動且為 Linux 容器模式 1>&2
  exit /b 1
)

echo Redis 已啟動：localhost:6379（純記憶體快取，重啟即清）
endlocal
