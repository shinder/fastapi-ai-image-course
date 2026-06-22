"""純 Pydantic Schema 範例（教材 3.1、3.2、3.3）

這些 schema 不入庫，純粹示範 Pydantic 驗證能力。
實際 API 主要使用 app/models/image.py 中的 SQLModel。
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ImageInfo(BaseModel):
    """教材 3.1 基本範例"""

    id: int
    filename: str
    size: int
    uploaded_at: datetime
    description: str | None = None  # 選填欄位


class ImageUpload(BaseModel):
    """教材 3.1 進階驗證：Field"""

    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=10)
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)


class ImageQuery(BaseModel):
    """教材 3.1 自訂驗證"""

    keyword: str

    @field_validator("keyword")
    @classmethod
    def keyword_no_space(cls, v: str) -> str:
        if " " in v:
            raise ValueError("關鍵字不可包含空格")
        return v.lower()


class ImageCreateRequest(BaseModel):
    """教材 3.2 接收 JSON 請求主體的 schema。

    當路由參數型別標成這個類別時，FastAPI 會把進來的 JSON 依下列規則驗證，
    驗證失敗自動回 422，不會進到路由函式。
    """

    title: str = Field(..., min_length=1)  # 必填（...），至少 1 個字元，空字串會被拒絕
    url: str  # 必填字串
    tags: list[str] = []  # 選填字串陣列，未提供時預設為空串列


class ImageResponse(BaseModel):
    """教材 3.3 回應模型，用來「過濾」對外輸出的欄位。

    搭配路由的 response_model=ImageResponse 使用：函式即使回傳了額外欄位
    （例如內部檔案路徑 file_path），只要不在這裡列出，就不會出現在回應 JSON，
    可避免內部資訊外洩。
    """

    id: int
    title: str
    url: str
    uploaded_at: datetime  # 只公開這四個欄位
