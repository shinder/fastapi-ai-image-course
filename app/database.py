"""資料庫連線與 Session 依賴注入（教材 4.3、4.5）"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# echo=True 會印出所有 SQL（開發階段除錯用）
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)


def init_db() -> bool:
    """應用啟動時呼叫，自動建立資料表。

    create_all() 只會建立「啟動時已被 import、註冊到 SQLModel.metadata」的
    table=True 模型對應的資料表，且只建「還不存在」的表（冪等，每次啟動呼叫都安全）。
    本專案的 import 鏈（main → routes.images → models.image）讓 Image 被註冊，
    所以實際只建 Image 那張表；models/user.py 沒被任何地方 import，其關聯示範表不會建出。
    注意：create_all 不做 migration——改了既有模型（加欄位、改型別）不會 ALTER 既有表，
    需改用 Alembic 這類遷移工具（或開發階段砍表重建）。

    連不到資料庫（例如 PostgreSQL 沒啟動）時，不讓整個應用崩潰：
    只在終端機印出清楚的警告，並回傳 False。如此沒用到資料庫的路由
    仍可正常運作；回傳 True 代表資料表已成功建立。
    """
    try:
        # 依已註冊到 metadata 的 table=True 模型建表；已存在則略過、不會 ALTER
        SQLModel.metadata.create_all(engine)
        return True
    except OperationalError as exc:
        print("=" * 70)
        print("無法連線到資料庫，已略過資料表建立。")
        print(f"   DATABASE_URL：{settings.DATABASE_URL}")
        print(f"   錯誤訊息：{exc.orig}")
        print("   → 沒有用到資料庫的功能仍可正常使用；")
        print("     若需資料庫功能，請確認 PostgreSQL 是否已啟動、連線設定是否正確。")
        print("=" * 70)
        return False


def get_session():
    """FastAPI 依賴注入用。

    優雅降級（教材 4.5）：連不到 PostgreSQL 時，讓端點回 503（服務暫時不可用）
    而不是預設的 500（伺服器內部錯誤）——「資料庫沒開」是外部依賴缺席，
    不是程式寫錯，503 才是正確語意，也讓學生一眼看出該去啟動資料庫。

    攔截時機要注意：SQLModel 的 Session 是「惰性連線」，建立時不會真的連上去，
    所以錯誤不會發生在 with 這一行，而是等路由執行查詢（session.exec(...)）時
    才拋 OperationalError。依賴用 yield 借出 session 後，路由裡拋出的例外會沿著
    yield 傳回這裡，因此用 try/except 包住 yield 就攔得到。
    對照 routes/images_raw.py 的 get_conn()：原生驅動在 connect() 當下就知道連不上，
    可以在借出連線前就回 503，不必等到查詢。
    """
    with Session(engine) as session:
        try:
            yield session
        except OperationalError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                f"資料庫連線失敗，請確認 PostgreSQL 是否啟動：{exc.orig}",
            )


# 為了方便重用，建立型別別名（教材 4.5）
SessionDep = Annotated[Session, Depends(get_session)]
