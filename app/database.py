"""資料庫連線與 Session 依賴注入（教材 4.3、4.5）"""
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# echo=True 會印出所有 SQL（開發階段除錯用）
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)


def init_db() -> None:
    """應用啟動時呼叫，自動建立資料表"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依賴注入用"""
    with Session(engine) as session:
        yield session


# 為了方便重用，建立型別別名（教材 4.5）
SessionDep = Annotated[Session, Depends(get_session)]
