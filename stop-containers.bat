@echo off
rem stop-containers.bat — 一鍵移除 start.bat 啟動的三個依賴服務容器
rem   （PostgreSQL / Redis / MongoDB）；Windows CMD 版，對應 stop-containers.sh
rem
rem 註：用 docker rm -fv 把容器「刪掉」（正在跑的會先 kill 再移除）。
rem     start-*.bat 已從源頭杜絕匿名資料卷——redis 的 /data、mongo 的 /data/configdb 都改掛
rem     tmpfs（記憶體），其餘要保留的路徑掛具名資料卷——所以正常情況根本不會產生匿名資料卷。
rem     這裡仍保留 -v 當「收工防呆」：萬一日後新增的服務漏處理了某個 VOLUME，收工時會把那個
rem     匿名資料卷一起帶走、不留垃圾。-v「只刪匿名資料卷、不碰具名資料卷」，故具名的
rem     pg-data / mongo-data 一律保留，資料仍在；下次 start.bat 會重新 docker run 並接回。
rem
rem 編碼：本檔以 UTF-8「無 BOM」儲存，chcp 65001 把主控台切成 UTF-8，中文才不會變亂碼。
chcp 65001 >nul
setlocal

rem 採「盡力而為」：某個容器不存在（沒起過、已移除）只印警告、不中斷，
rem 與 start.bat 的優雅降級精神一致。
rem （echo 的內容含 > 要寫成 ^>，否則會被當成輸出重導向。）
echo ==^> 移除依賴服務容器
for %%c in (pg-ai-image redis-ai-image mongo-ai-image) do (
  echo --^> %%c
  docker rm -fv %%c >nul 2>&1 && echo 已移除 %%c || echo 警告：找不到容器 %%c，略過（可能尚未啟動）
)
endlocal
