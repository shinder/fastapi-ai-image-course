@echo off
rem start.bat — 一鍵啟動本機開發環境（Windows CMD 版，對應 start.sh）
rem   1. 先啟動三個依賴服務的容器（PostgreSQL / Redis / MongoDB）
rem   2. 最後在前景啟動 FastAPI 開發伺服器（uvicorn）
rem
rem 註：刻意把資料庫放前面、uvicorn 放最後。uvicorn 會「常駐前景」直到 Ctrl-C，
rem     所以必須是最後一步；三支 db 腳本都是 docker run -d（detached），起完馬上返回。
rem
rem 編碼：本檔以 UTF-8「無 BOM」儲存，chcp 65001 把主控台切成 UTF-8，中文才不會變亂碼。
chcp 65001 >nul
setlocal

rem 切換到本檔所在的資料夾（%~dp0 是本檔所在路徑，/d 允許連磁碟機一起換），
rem 確保不論從哪裡呼叫，相對路徑都正確
cd /d "%~dp0"

rem 1. 啟動三個依賴服務 —— 採「盡力而為」：某支起不來（連接埠被占、Docker 沒開…）
rem    只印警告、不中斷，因為 app 對外部依賴都有優雅降級。
rem
rem 注意兩個 cmd 慣例：
rem   - 呼叫另一支 .bat 一定要加 call，否則控制權一去不回（跳過去執行完就結束，不會回來跑下面幾行）。
rem   - echo 的內容含 > 要寫成 ^>，否則會被當成「把輸出導向到某個檔案」。
echo ==^> 啟動依賴服務容器
for %%s in (start-postgres.bat start-redis.bat start-mongodb.bat) do (
  echo --^> %%s
  call "%%s" || echo 警告：%%s 啟動失敗，伺服器仍會以優雅降級方式繼續啟動
)

rem 2. 在前景啟動 uvicorn（--reload 開發用熱重載；Ctrl-C 結束）
echo ==^> 啟動 FastAPI 伺服器：http://localhost:8000（/docs 看 Swagger）
uv run uvicorn app.main:app --reload
endlocal
