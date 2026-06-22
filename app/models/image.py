"""SQLModel 影像資料表（教材 4.4）

模型分層：
- ImageBase     : 共用欄位（非 table）
- Image         : 真正的資料表（table=True）
- ImageCreate   : POST 請求主體
- ImagePublic   : API 回應（過濾內部欄位）
- ImageUpdate   : PATCH 請求主體（全部選填）
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import JSON, Column, Field, SQLModel


class ImageBase(SQLModel):
    """純 schema，當作其他 model 的基底"""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class Image(ImageBase, table=True):
    """資料表定義（table=True）"""

    __tablename__ = "images"

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(..., index=True)
    file_path: str
    file_size: int
    mime_type: str
    ai_result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    # 用 timezone-aware 的 UTC 時間；datetime.utcnow 在 Python 3.12 已棄用
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImageCreate(ImageBase):
    """接收 API 請求用，不含 id 與系統欄位"""

    pass


class ImagePublic(ImageBase):
    """回應給用戶端用"""

    id: int
    filename: str
    file_size: int
    uploaded_at: datetime
    ai_result: Optional[dict] = None


class ImageUpdate(SQLModel):
    """部分更新用，所有欄位都選填"""

    title: Optional[str] = None
    description: Optional[str] = None
