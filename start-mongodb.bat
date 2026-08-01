@echo off
rem start-mongodb.bat — 單獨啟動 MongoDB 容器（Windows 版，對應 start-mongodb.sh）
rem 教材 單元十 補充教材
rem
rem mongo image 宣告了兩個 VOLUME：
rem   /data/db       真正存資料的地方 → 掛具名資料卷 mongo-data，持久保留
rem   /data/configdb 分片叢集才用得到，單機永遠是空的 → 掛 tmpfs，不落地也不生匿名資料卷

docker rm -f mongo-ai-image >nul 2>&1

docker run -d ^
  --name mongo-ai-image ^
  -p 27017:27017 ^
  -v mongo-data:/data/db ^
  --mount type=tmpfs,destination=/data/configdb ^
  mongo:8

echo MongoDB 已啟動：localhost:27017（資料庫：ai_image_db）
