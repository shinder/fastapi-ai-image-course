@echo off
rem cmd-start-containers.bat — 只啟動三個依賴服務的容器（Windows CMD 版，對應 sh-start-containers.sh）
rem   PostgreSQL / Redis / MongoDB 三個容器起完就結束，不啟動 FastAPI 開發伺服器——
rem   伺服器另開視窗自己跑：uv run fastapi dev app/main.py
rem   或直接執行專案根目錄的 start.bat（單行腳本，CMD / PowerShell 皆可）。
rem
rem 編碼：本檔以 UTF-8「無 BOM」儲存，chcp 65001 把主控台切成 UTF-8，中文才不會變亂碼。
chcp 65001 >nul
setlocal

rem 切換到本檔所在的資料夾（%~dp0 是本檔所在路徑，/d 允許連磁碟機一起換），
rem 確保不論從哪裡呼叫，相對路徑都正確
cd /d "%~dp0"

rem 採「盡力而為」：某支起不來（連接埠被占、Docker 沒開…）只印警告、不中斷，
rem 繼續啟動其餘容器——app 對外部依賴都有優雅降級，少一個服務也能開發。
rem
rem 注意兩個 cmd 慣例：
rem   - 呼叫另一支 .bat 一定要加 call，否則控制權一去不回（跳過去執行完就結束，不會回來跑下面幾行）。
rem   - echo 的內容含 > 要寫成 ^>，否則會被當成「把輸出導向到某個檔案」。
echo ==^> 啟動依賴服務容器
for %%s in (cmd-start-postgres.bat cmd-start-redis.bat cmd-start-mongodb.bat) do (
  echo --^> %%s
  call "%%s" || echo 警告：%%s 啟動失敗，繼續啟動其餘容器
)

echo ==^> 容器啟動完成。開發伺服器請另行執行：uv run fastapi dev app/main.py
endlocal
