@echo off
rem stop-containers.bat — 一鍵移除三個依賴服務容器（Windows 版，對應 stop-containers.sh）
rem
rem -fv：正在跑的先 kill 再移除，並帶走匿名資料卷（具名的 pg-data / mongo-data 一律保留，
rem 資料仍在，下次 start-*.bat 會重新 docker run 並接回）。
rem 採「盡力而為」：容器不存在只印訊息、不中斷。

echo ==^> 移除依賴服務容器

for %%c in (pg-ai-image redis-ai-image mongo-ai-image) do (
  docker rm -fv %%c >nul 2>&1 && echo 已移除 %%c || echo 警告：找不到容器 %%c，略過（可能尚未啟動）
)
