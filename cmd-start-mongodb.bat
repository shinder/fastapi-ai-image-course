@echo off
rem cmd-start-mongodb.bat — 單獨啟動 MongoDB 容器（Windows CMD 版，對應 sh-start-mongodb.sh；單元九補充教材）
rem
rem 編碼：本檔以 UTF-8「無 BOM」儲存，chcp 65001 把主控台切成 UTF-8，中文才不會變亂碼。
chcp 65001 >nul
setlocal

rem 同名容器已存在就先移除，讓這支腳本可重複執行
docker rm -f mongo-ai-image >nul 2>&1

rem mongo image 宣告了「兩個」VOLUME：/data/db 與 /data/configdb。
rem   - /data/db：真正存資料的地方 → 掛具名資料卷 mongo-data，持久保留。
rem   - /data/configdb：分片叢集（sharded cluster）的 config server 才會用到，單機跑根本用不到
rem     （永遠是空的）。放著不管，每次啟動會為它生一個 hash 名稱的空匿名資料卷；這裡用 tmpfs
rem     掛成記憶體檔案系統，容器一停就消失——不落地、也不產生匿名資料卷。
docker run -d ^
  --name mongo-ai-image ^
  -p 27017:27017 ^
  -v mongo-data:/data/db ^
  --mount type=tmpfs,destination=/data/configdb ^
  mongo:8

rem cmd 沒有 set -e，失敗要自己查 errorlevel（語義是 errorlevel >= 1，也就是「失敗」）
if errorlevel 1 (
  echo 錯誤：MongoDB 容器啟動失敗，請確認 Docker Desktop 已啟動且為 Linux 容器模式 1>&2
  exit /b 1
)

echo MongoDB 已啟動：localhost:27017（資料庫：ai_image_db）
endlocal
