@echo off
rem start-postgres.bat — 單獨啟動 PostgreSQL 容器（Windows 版，對應 start-postgres.sh）
rem 教材 5.3 資料庫環境準備

rem 同名容器已存在就先移除，讓這支批次檔可重複執行
docker rm -f pg-ai-image >nul 2>&1

rem ^ 是 cmd 的續行符號（等同 sh 的 \）
docker run -d ^
  --name pg-ai-image ^
  -e POSTGRES_USER=postgres ^
  -e POSTGRES_PASSWORD=secret ^
  -e POSTGRES_DB=ai_image_db ^
  -p 5432:5432 ^
  -v pg-data:/var/lib/postgresql/data ^
  postgres:17

echo PostgreSQL 17 已啟動：localhost:5432（資料庫：ai_image_db）
