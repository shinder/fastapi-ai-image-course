"""Pydantic 範例 02：使用 Field 設定欄位限制與預設值

本範例示範如何用 Field() 為欄位加上更細緻的驗證規則：
- 字串長度限制（min_length / max_length）
- 數值範圍限制（ge / le）
- 串列的預設值與長度限制
Field 讓我們在「型別」之外，再加上「值的限制條件」。
"""

from pydantic import BaseModel, Field


class ImageUpload(BaseModel):
    # Field 的第一個參數是預設值，「...」（Ellipsis）代表「必填、沒有預設值」。
    # min_length / max_length 限制字串長度需介於 1~100 之間。
    title: str = Field(..., min_length=1, max_length=100)

    # 預設值為 None（選填）；若有提供值，長度不可超過 500。
    description: str | None = Field(None, max_length=500)

    # default_factory：用一個函式產生預設值，這裡是空串列 list()。
    # 串列預設值務必用 default_factory，避免所有實例共用同一個可變物件。
    # max_length 限制串列最多 10 個元素。
    tags: list[str] = Field(default_factory=list, max_length=10)

    # 預設值 0.5；ge=大於等於 0.0，le=小於等於 1.0（信心門檻通常落在 0~1）。
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)


# 建立實例時，Pydantic 會檢查每個欄位是否符合 Field 設定的限制。
# 例如 title 長度、confidence_threshold 範圍等，違反就會丟出 ValidationError。
data = ImageUpload(
    title="Cat Image",
    description="A picture of a cat",
    tags=["animal", "cat"],
    confidence_threshold=0.8,
)

# model_dump()：轉成 dict。
print(data.model_dump())
# model_dump_json()：轉成格式化的 JSON 字串。
print(data.model_dump_json(indent=2))
