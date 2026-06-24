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
    """真正的資料表（table=True）。

    table=True 會讓 SQLModel 的 metaclass 在「這個 class 定義被執行時」（也就是本模組
    被 import 時）自動把對應的 Table 註冊進 SQLModel.metadata——沒有明確的註冊呼叫，
    「定義 class」本身就是註冊。init_db() 的 create_all() 之後才據此建表。
    反之，本檔其他 table=False 的純 schema（ImageBase / ImageCreate / ImagePublic /
    ImageUpdate）不會註冊、也不會建表，只負責驗證與序列化。
    """

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
