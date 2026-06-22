"""資料庫連線與 Session 依賴注入（教材 4.3、4.5）"""

from typing import Annotated

from fastapi import Depends
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

    連不到資料庫（例如 PostgreSQL 沒啟動）時，不讓整個應用崩潰：
    只在終端機印出清楚的警告，並回傳 False。如此沒用到資料庫的路由
    仍可正常運作；回傳 True 代表資料表已成功建立。
    """
    try:
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
    """FastAPI 依賴注入用"""
    with Session(engine) as session:
        yield session


# 為了方便重用，建立型別別名（教材 4.5）
SessionDep = Annotated[Session, Depends(get_session)]
