@echo off
rem start-postgres.bat — 單獨啟動 PostgreSQL 容器（Windows CMD 版，對應 start-postgres.sh）
rem
rem 編碼：本檔以 UTF-8「無 BOM」儲存，下面的 chcp 65001 把主控台切成 UTF-8，中文才不會變亂碼
rem （繁中 Windows 的 cmd 預設是 cp950）。千萬別存成「UTF-8 with BOM」：cmd 不認 BOM，
rem 會把它當成第一行指令的一部分。
chcp 65001 >nul

rem setlocal：本檔設定的環境變數（DB_NAME）離開時自動還原，不會污染呼叫端的 cmd 視窗
setlocal

rem 註：.sh 版開頭那兩行 MSYS_NO_PATHCONV / MSYS2_ARG_CONV_EXCL 這裡不需要——
rem 把 /var/lib/... 改寫成 Windows 路徑是 Git Bash（MSYS）特有的行為，CMD 不會動 -v 的參數。

rem 資料庫名可用環境變數覆寫（例：先 set DB_NAME=my_db 再執行本檔），預設 ai_image_db。
rem 記得同步改 .env 的 DATABASE_URL，兩邊名字要一致。
if "%DB_NAME%"=="" set DB_NAME=ai_image_db

rem 同名容器已存在就先移除，讓這支腳本可重複執行
docker rm -f pg-ai-image >nul 2>&1

rem cmd 的續行字元是 ^（相當於 bash 的 \）。^ 後面不能有空白，否則接不起來。
docker run -d ^
  --name pg-ai-image ^
  -e POSTGRES_USER=postgres ^
  -e POSTGRES_PASSWORD=secret ^
  -e POSTGRES_DB=%DB_NAME% ^
  -p 5432:5432 ^
  -v pg-data:/var/lib/postgresql/data ^
  postgres:17

rem cmd 沒有 bash 的 set -e，指令失敗不會自動中斷，得自己查 errorlevel。
rem 注意「if errorlevel N」的語義是「errorlevel >= N」，所以 if errorlevel 1 就是「失敗」。
if errorlevel 1 (
  echo 錯誤：PostgreSQL 容器啟動失敗，請確認 Docker Desktop 已啟動且為 Linux 容器模式 1>&2
  exit /b 1
)

rem ---- 等到資料庫「真的」可用 ----
rem docker run -d 一返回只代表容器建起來了，不代表 PostgreSQL 已能接受連線。實測：
rem docker run 約 0.2 秒返回、TCP 5432 約 0.3 秒就通，但真正能查詢要約 1.5 秒
rem （資料卷全新時還得先跑 initdb，更久）。start.bat 起完容器隨即啟動 uvicorn，
rem 這段空窗會讓 init_db() 撲空，印出「無法連線到資料庫」而且沒建表——所以這裡等到真的就緒才返回。
rem
rem 就緒判準要選對：只看 TCP 埠通不通會誤判（埠會先通，此時連線拿到 the database system is
rem starting up）；只靠 pg_isready 也會誤判（initdb 階段容器內有個只收本機連線的臨時 server）。
rem 最可靠的是直接下一句 SQL，跑得動才算數。
rem
rem 註：echo 的內容含 > 一定要寫成 ^>，否則 cmd 會當成「把輸出導向到某個檔案」。
echo ==^> 等待 PostgreSQL 就緒
set /a TRIES=0

:waitloop
docker exec pg-ai-image psql -U postgres -c "SELECT 1" >nul 2>&1
if not errorlevel 1 goto ready
set /a TRIES+=1
if %TRIES% geq 30 goto notready
rem 印一個點當進度、且不換行。cmd 沒有 echo -n，慣用寫法是借用 set /p 的提示字：
rem 開頭的 <nul 讓它立刻讀到 EOF 結束，不會真的停下來等使用者輸入。
<nul set /p "=."
rem cmd 也沒有 sleep。ping 自己 2 次、間隔 1 秒 → 約等 1 秒。
rem （不用 timeout /t 1：標準輸入被重導向時它會直接報錯，在被其他腳本呼叫的情境下不可靠。）
ping -n 2 127.0.0.1 >nul
goto waitloop

:notready
echo.
echo 錯誤：等待 30 秒仍無法連線，請查看 docker logs pg-ai-image 1>&2
exit /b 1

:ready
echo.

rem ---- 確保資料庫存在（冪等）----
rem POSTGRES_DB 只在「資料卷首次初始化」時生效。pg-data 這個具名資料卷一旦建立過，
rem 之後改資料庫名、或沿用舊卷重建容器，PostgreSQL 都不會再幫你建那個資料庫
rem （docker logs 會看到 "Skipping initialization"），app 連線就會失敗、端點回 503。
rem 這裡補一次「沒有才建」，讓換名字 / 沿用舊卷的情況都能直接開工。
rem （findstr 是 cmd 版的 grep；/b 只比對行首、/c: 指定要找的字串。）
docker exec pg-ai-image psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" | findstr /b /c:"1" >nul
if not errorlevel 1 (
  echo ==^> 資料庫 %DB_NAME% 已存在
) else (
  docker exec pg-ai-image psql -U postgres -c "CREATE DATABASE %DB_NAME%" >nul
  echo ==^> 已建立資料庫 %DB_NAME%（資料卷先前已初始化，POSTGRES_DB 不會再生效）
)

echo PostgreSQL 17 已啟動：localhost:5432（資料庫：%DB_NAME%）
endlocal
