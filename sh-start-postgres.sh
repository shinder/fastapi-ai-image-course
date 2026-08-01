#!/usr/bin/env bash
# sh-start-postgres.sh — 單獨啟動 PostgreSQL 容器（不需 docker compose）
set -euo pipefail

# 關掉 Git Bash（MSYS）的路徑自動轉換：它會把參數中看起來像 POSIX 絕對路徑的字串改寫成
# Windows 路徑（/var/lib/postgresql/data → C:/Program Files/Git/var/lib/postgresql/data），
# 下面 -v 的掛載點就會掛錯地方。兩個變數分別是 Git for Windows 專有與 MSYS2 原生，
# 都設比較保險；macOS / Linux 只是多兩個沒人讀的環境變數，不影響。
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

# 資料庫名可用環境變數覆寫（例：DB_NAME=my_db ./sh-start-postgres.sh），預設 ai_image_db。
# 記得同步改 .env 的 DATABASE_URL，兩邊名字要一致。
DB_NAME=${DB_NAME:-ai_image_db}

# 同名容器已存在就先移除，讓這支 script 可重複執行
docker rm -f pg-ai-image 2>/dev/null || true

docker run -d \
  --name pg-ai-image \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB="${DB_NAME}" \
  -p 5432:5432 \
  -v pg-data:/var/lib/postgresql/data \
  postgres:17

# ---- 等到資料庫「真的」可用 ----
# docker run -d 一返回只代表容器建起來了，不代表 PostgreSQL 已能接受連線。實測：
# docker run 約 0.2 秒返回、TCP 5432 約 0.3 秒就通，但真正能查詢要約 1.5 秒
# （資料卷全新時還得先跑 initdb，更久）。sh-start.sh 起完容器隨即啟動 uvicorn，
# 這段空窗會讓 init_db() 撲空，印出「無法連線到資料庫」而且沒建表，
# 得再重啟一次伺服器才正常——所以這裡等到真的就緒才返回。
#
# 就緒判準要選對，有兩個看似可行其實會誤判的做法：
#   - 只看 TCP 埠通不通（nc -z 之類）：埠會先通，此時連線會拿到
#     FATAL: the database system is starting up。
#   - 只靠 pg_isready：initdb 階段容器內會先跑一個「只收本機連線」的臨時 server，
#     pg_isready 會提早回報就緒（實測踩過）。
# 最可靠的是直接下一句 SQL，跑得動才算數。
echo -n "==> 等待 PostgreSQL 就緒"
for _ in $(seq 1 60); do  # 0.5 秒一次，最多等 30 秒
  if docker exec pg-ai-image psql -U postgres -c 'SELECT 1' >/dev/null 2>&1; then
    ready=1
    break
  fi
  echo -n "."
  sleep 0.5
done
echo
if [ "${ready:-0}" != 1 ]; then
  echo "錯誤：等待 30 秒仍無法連線，請查看 docker logs pg-ai-image" >&2
  exit 1
fi

# ---- 確保資料庫存在（冪等）----
# POSTGRES_DB 只在「資料卷首次初始化」時生效。pg-data 這個具名資料卷一旦建立過，
# 之後改資料庫名、或沿用舊卷重建容器，PostgreSQL 都不會再幫你建那個資料庫
# （docker logs 會看到 "Skipping initialization"），app 連線就會失敗、端點回 503，
# 而且訊息只說 database does not exist，很難聯想到是資料卷已初始化過。
# 這裡補一次「沒有才建」，讓換名字 / 沿用舊卷的情況都能直接開工。
if docker exec pg-ai-image psql -U postgres -tAc \
     "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  echo "==> 資料庫 ${DB_NAME} 已存在"
else
  docker exec pg-ai-image psql -U postgres -c "CREATE DATABASE ${DB_NAME}" >/dev/null
  echo "==> 已建立資料庫 ${DB_NAME}（資料卷先前已初始化，POSTGRES_DB 不會再生效）"
fi

echo "PostgreSQL 17 已啟動：localhost:5432（資料庫：${DB_NAME}）"
