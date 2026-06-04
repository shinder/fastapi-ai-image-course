"""Pydantic 範例 01：定義基本資料模型

本範例示範 Pydantic 最基礎的用法：
- 繼承 BaseModel 來定義一個有型別標註的資料模型
- 建立實例時 Pydantic 會自動依照型別標註做驗證與轉換
- 將模型實例輸出成 dict 或 JSON 字串
"""

from pydantic import BaseModel
from datetime import datetime


# 繼承 BaseModel 即可建立一個資料模型，類別屬性就是欄位定義。
# 每個欄位都用「型別標註」描述它應該是什麼型別，Pydantic 會據此驗證。
class ImageInfo(BaseModel):
    id: int                  # 必填，必須是整數（字串 "1" 也會自動轉成 int 1）
    filename: str            # 必填，字串
    size: int                # 必填，整數（檔案大小，單位 byte）
    uploaded_at: datetime    # 必填，日期時間；可接受 datetime 物件或 ISO 格式字串
    description: str | None = None  # 選填欄位：型別為 str 或 None，並給定預設值 None


# 建立實例時，Pydantic 會自動驗證每個欄位的型別是否正確。
# 若型別不符且無法自動轉換，會丟出 ValidationError。
data = ImageInfo(
    id=1,
    filename="cat.jpg",
    size=102400,
    uploaded_at=datetime.now(),
    # 沒有提供 description，會使用預設值 None
)

# model_dump()：將模型轉成 Python 的 dict，方便程式內部處理。
print(data.model_dump())
# model_dump_json()：將模型轉成 JSON 字串，indent=2 表示縮排 2 個空格美化輸出。
print(data.model_dump_json(indent=2))
