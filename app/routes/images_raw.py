"""對照範例：不使用 SQLModel／不經任何 ORM，用 psycopg3 原生驅動直接下 SQL（教材 4.x 對照）

這個檔案是「同一組影像 CRUD，改用原生 PostgreSQL 驅動程式重寫」的對照版，
拿來跟既有的 SQLModel 版三件套並排閱讀：
    - app/database.py        →（連線層）engine + Session 依賴
    - app/models/image.py    →（資料表）Image(table=True) 由 metadata 自動建表
    - app/routes/images.py   →（路由層）session.exec(select(...))、session.add/commit/refresh

本檔把上面三層「刻意合在同一個檔」方便對照（正式專案仍應比照原版分層拆開）。
核心差異一句話：**ORM 幫你把 Python 物件 ↔ SQL 來回翻譯；原生驅動則由你自己寫 SQL、
自己把 row 對應成資料**。少了一層抽象，最透明、最快，但所有 SQL、參數化、建表、
型別轉換都得親手處理。

為什麼仍然 import Pydantic？因為「不用 ORM」不等於「不用 Pydantic」。
請求主體驗證（422）與回應欄位過濾（response_model）是 FastAPI／Pydantic 的職責，
跟「用什麼方式存取資料庫」是兩件事。SQLModel 的賣點只是把「資料表模型」與
「Pydantic 模型」合而為一；拆開後，這裡就是一邊手寫 SQL、一邊用純 Pydantic 驗證。

------------------------------------------------------------------------------
驅動選擇：本檔用 psycopg3（套件名 psycopg，專案已內建依賴）的「非同步」介面
（AsyncConnection），以搭配 FastAPI 的 async 路由。另一個常見選擇是 asyncpg
（純非同步、效能更好，但 placeholder 用 $1/$2 而非 %s，API 也不同）。

預設不掛進 app（比照 models/user.py，是純示範、不影響既有 app 啟動）。要啟用：
    1. 確認 docker compose 的 postgres 有在跑（本檔連的是 PostgreSQL，不是預設的 sqlite）。
    2. 設環境變數 PG_DSN（見下方），或直接用預設值（對到 docker-compose.yml）。
    3. 在 app/main.py：
            from app.routes import images_raw
            await images_raw.init_images_raw_table()   # 放進 lifespan 啟動段
            app.include_router(images_raw.router)
------------------------------------------------------------------------------
"""

import os
from typing import Annotated, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

# psycopg 用的是 libpq 的 DSN，前綴是 postgresql://（注意：**不能**帶 +psycopg，
# 那個 postgresql+psycopg:// 是 SQLAlchemy/SQLModel 專用的方言標記，原生驅動看不懂）。
# 預設值對到 docker-compose.yml 的 postgres 服務；本檔刻意不共用 settings.DATABASE_URL，
# 因為那條預設是 sqlite，psycopg 連不了。
PG_DSN = os.getenv("PG_DSN", "postgresql://postgres:secret@localhost:5432/ai_image_db")


# ============================================================================
# 連線層（對照 app/database.py）
# ============================================================================
#
# SQLModel 版：建立一個全域 engine（內含連線池），用 get_session() 依賴每次借出 Session。
# 原生版：這裡示範「每個請求開一條連線、用完就關」，最簡單、零額外依賴即可跑。
#   缺點是每個請求都付出建立連線的成本。正式環境應改用連線池：
#       # uv add psycopg-pool
#       from psycopg_pool import AsyncConnectionPool
#       pool = AsyncConnectionPool(PG_DSN, kwargs={"row_factory": dict_row}, open=False)
#       # lifespan 啟動段 await pool.open()、關閉段 await pool.close()
#       async def get_conn():
#           async with pool.connection() as conn:   # 從池中借、離開區塊自動歸還
#               yield conn
#
# row_factory=dict_row：讓 cursor 的 fetch 回傳「欄位名 → 值」的 dict，
# 而不是預設的 tuple，這樣才能直接餵給 Pydantic / 當作 JSON 回傳。
# 沒有它的話，fetchone() 會回 (1, 'cat.jpg', ...) 這種要靠位置取值的元組。


async def get_conn():
    """FastAPI 依賴注入：開一條非同步連線，請求結束後關閉。

    優雅降級（本專案貫穿全域的原則）：連不到 PostgreSQL 時不讓整個 app 崩潰，
    而是回 503，讓沒用到這組路由的其他端點仍能正常運作。
    """
    try:
        conn = await psycopg.AsyncConnection.connect(PG_DSN, row_factory=dict_row)
    except psycopg.OperationalError as exc:
        # 連線本身失敗（DB 沒開、DSN 錯、網路不通）→ 對外回 503
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"資料庫連線失敗，請確認 PostgreSQL 是否啟動：{exc}",
        )
    try:
        yield conn
    finally:
        await conn.close()


# 重用型別別名（對照 database.py 的 SessionDep）。路由參數直接標 ConnDep 即可。
ConnDep = Annotated[psycopg.AsyncConnection, Depends(get_conn)]


async def init_images_raw_table() -> bool:
    """建立資料表（對照 SQLModel 的 init_db()）。

    關鍵差異：SQLModel 靠 metadata.create_all() 從「table=True 模型」自動推導出 DDL；
    原生驅動沒有 metadata，**整段 CREATE TABLE 都得自己手寫**。
    表名刻意用 images_raw，與 SQLModel 版的 images 區隔，避免兩套 schema 打架。

    同樣做優雅降級：連不到就印警告、回 False，不中斷 app 啟動。
    """
    ddl = """
        CREATE TABLE IF NOT EXISTS images_raw (
            id          BIGSERIAL PRIMARY KEY,
            title       VARCHAR(200)  NOT NULL,
            description VARCHAR(1000),
            filename    VARCHAR(255)  NOT NULL,
            file_path   TEXT          NOT NULL,
            file_size   BIGINT        NOT NULL,
            mime_type   VARCHAR(100)  NOT NULL,
            ai_result   JSONB,
            uploaded_at TIMESTAMPTZ   NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_images_raw_filename ON images_raw (filename);
    """
    try:
        async with await psycopg.AsyncConnection.connect(PG_DSN) as conn:
            await conn.execute(ddl)
            await conn.commit()  # DDL 也要 commit（autocommit 預設為關）
        return True
    except psycopg.OperationalError as exc:
        print("=" * 70)
        print("無法連線到資料庫（images_raw 對照範例），已略過建表。")
        print(f"   PG_DSN：{PG_DSN}")
        print(f"   錯誤訊息：{exc}")
        print("=" * 70)
        return False


# ============================================================================
# Pydantic Schema（對照 app/models/image.py 裡 table=False 的那幾個分層模型）
# ============================================================================
#
# SQLModel 版：ImageBase/ImageCreate/ImagePublic/ImageUpdate 全繼承 SQLModel，
# 跟 table=True 的 Image 共用同一套欄位定義。
# 原生版：這裡是「純 Pydantic BaseModel」，跟資料表定義（上面的手寫 DDL）完全脫鉤——
# 兩邊欄位若不一致，不會有人幫你檢查，這正是少了 ORM 後要自己扛的責任。


class ImageCreateRaw(BaseModel):
    """POST 請求主體（對照 ImageCreate）"""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class ImageUpdateRaw(BaseModel):
    """PATCH 請求主體，欄位全選填（對照 ImageUpdate）"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class ImagePublicRaw(BaseModel):
    """回應模型（對照 ImagePublic）：列出對外公開的欄位。

    路由回傳 dict_row 給來的 dict，FastAPI 會依本模型驗證並「只留下這些欄位」，
    例如 file_path 這種內部路徑不在此列，就不會外洩到回應。
    """

    id: int
    title: str
    description: Optional[str] = None
    filename: str
    file_size: int
    uploaded_at: object  # 直接收 driver 回來的 datetime，序列化交給 FastAPI
    ai_result: Optional[dict] = None


# ============================================================================
# 路由層（對照 app/routes/images.py 的 4.6 CRUD 段）
# ============================================================================
#
# 用 /api/v2/images 區隔，避免和 SQLModel 版的 /api/v1/images 撞路徑。
#
# 全檔最重要的資安鐵則：**SQL 參數一律走 %s 佔位字元交給驅動程式跳脫，
# 永遠不要用 f-string／字串相加把使用者輸入拼進 SQL**（那就是 SQL injection）。
# ORM 會自動參數化，原生驅動則靠你自律。注意 %s 是 psycopg 的佔位字元，
# 跟 Python 的 % 字串格式化無關，值請放在 execute 的第二個參數（一個序列）裡。

router = APIRouter(prefix="/api/v2/images", tags=["images-raw"])


@router.post("", response_model=ImagePublicRaw, status_code=status.HTTP_201_CREATED)
async def create_image(payload: ImageCreateRaw, conn: ConnDep):
    """建立一筆（純 JSON）。檔案類欄位用佔位值補上，對照原版 create_image。

    對照重點：
    - SQLModel：session.add(obj) → commit → refresh 把 DB 產生的 id/時間補回物件。
    - 原生版：用 INSERT ... RETURNING * 在同一句 SQL 直接拿回「資料庫填好的整列」，
      省掉一次 refresh round-trip。
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """
            INSERT INTO images_raw
                (title, description, filename, file_path, file_size, mime_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            # ↓ 這個 tuple 就是要綁進上面六個 %s 的值，順序一一對應
            (
                payload.title,
                payload.description,
                "placeholder.jpg",
                "/tmp/placeholder.jpg",
                0,
                "image/jpeg",
            ),
        )
        row = await cur.fetchone()
    await conn.commit()  # 寫入操作必須 commit，否則離開連線時會被 rollback
    return row


@router.get("", response_model=list[ImagePublicRaw])
async def list_images(
    conn: ConnDep,
    skip: int = 0,
    limit: int = 20,
    keyword: Optional[str] = None,
):
    """列表查詢，支援關鍵字、分頁（對照原版 list_images）。

    對照重點：SQLModel 用 select(Image).where(Image.title.icontains(kw)) 這種
    Python 運算式組查詢；原生版直接寫 SQL，連 ILIKE（PostgreSQL 不分大小寫的 LIKE）、
    LIMIT/OFFSET 都明寫出來。即使是動態條件，值仍一律走 %s，不拼字串。
    """
    # 用 list 累積 SQL 片段與參數，最後再組起來——值永遠進 params，不進 SQL 字串
    clauses = ["SELECT * FROM images_raw"]
    params: list = []
    if keyword:
        clauses.append("WHERE title ILIKE %s")
        params.append(f"%{keyword}%")  # 前後加 % 是 SQL LIKE 的萬用字元，仍由 %s 安全綁入
    clauses.append("ORDER BY uploaded_at DESC LIMIT %s OFFSET %s")
    params.extend([limit, skip])

    async with conn.cursor() as cur:
        await cur.execute(" ".join(clauses), params)
        rows = await cur.fetchall()
    return rows  # list[dict]，response_model 會逐筆過濾欄位


@router.get("/stats/total")
async def total_images(conn: ConnDep):
    """計數查詢（對照原版 total_images 的 select(func.count(...))）"""
    async with conn.cursor() as cur:
        await cur.execute("SELECT count(*) AS total FROM images_raw")
        row = await cur.fetchone()
    return {"total": row["total"]}  # dict_row 讓我們能用欄位別名 total 取值


@router.get("/{image_id}", response_model=ImagePublicRaw)
async def get_image(image_id: int, conn: ConnDep):
    """單筆查詢（對照原版 session.get(Image, id)）"""
    async with conn.cursor() as cur:
        await cur.execute("SELECT * FROM images_raw WHERE id = %s", (image_id,))
        row = await cur.fetchone()  # 查無資料回 None
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到圖片")
    return row


@router.patch("/{image_id}", response_model=ImagePublicRaw)
async def update_image(image_id: int, payload: ImageUpdateRaw, conn: ConnDep):
    """部分更新（對照原版 exclude_unset + setattr 迴圈）。

    動態 SQL 的安全示範：要更新哪些「欄位」是動態的，但**欄位名不能用 %s**
    （%s 只能綁「值」）。所以欄位名走白名單，再用 psycopg.sql.Identifier 安全地
    組進語句；欄位的「值」仍一律走 %s。這是原生驅動寫動態 SQL 最關鍵的一課。
    """
    # exclude_unset：只取用戶端「有送的」欄位，沒送的不動（對照原版同名做法）
    fields = payload.model_dump(exclude_unset=True)
    # 白名單再過濾一次，杜絕意外把不該改的欄位名帶進 SQL
    allowed = {"title", "description"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "沒有可更新的欄位")

    # 用 sql.Identifier 包欄位名（識別字），sql.SQL("{} = %s") 讓「值」維持參數化
    assignments = sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(k)) for k in fields)
    query = sql.SQL("UPDATE images_raw SET {} WHERE id = %s RETURNING *").format(assignments)
    params = list(fields.values()) + [image_id]  # 值的順序要跟 assignments 一致，id 殿後

    async with conn.cursor() as cur:
        await cur.execute(query, params)
        row = await cur.fetchone()
    if row is None:  # RETURNING 沒回任何列 → 該 id 不存在
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到圖片")
    await conn.commit()
    return row


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: int, conn: ConnDep):
    """刪除（對照原版 session.delete + commit）。

    原生版用 cursor.rowcount 判斷實際刪了幾列：0 代表該 id 根本不存在 → 回 404。
    """
    async with conn.cursor() as cur:
        await cur.execute("DELETE FROM images_raw WHERE id = %s", (image_id,))
        affected = cur.rowcount  # 受影響列數
    if affected == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到圖片")
    await conn.commit()


# ============================================================================
# 附帶示範：寫入 JSONB（對照 Image.ai_result）
# ============================================================================


@router.patch("/{image_id}/ai-result", response_model=ImagePublicRaw)
async def set_ai_result(image_id: int, ai_result: dict, conn: ConnDep):
    """把一包 AI 結果寫進 JSONB 欄位。

    對照重點：SQLModel 用 sa_column=Column(JSON)，存取就像一般 dict 屬性，
    序列化由 ORM 代勞。原生驅動寫 dict 進 JSONB 欄位時，要用 psycopg 的 Jsonb()
    把 Python dict 包成 jsonb 參數（讀回來時 psycopg 會自動還原成 dict，不用特別處理）。
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE images_raw SET ai_result = %s WHERE id = %s RETURNING *",
            (Jsonb(ai_result), image_id),  # ← Jsonb() 是關鍵：dict → jsonb 參數
        )
        row = await cur.fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到圖片")
    await conn.commit()
    return row
