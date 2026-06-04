"""Pydantic 範例 03：使用 field_validator 自訂欄位驗證邏輯

當內建的型別與 Field 限制不夠用時，可用 @field_validator 撰寫自訂驗證函式：
- 可在驗證過程中檢查值是否合法（不合法就 raise ValueError）
- 也可以「轉換」值後回傳（例如統一轉成小寫）
本範例的關鍵字欄位：不允許空格，並自動轉成小寫。
"""

from pydantic import BaseModel, Field, field_validator


class ImageQuery(BaseModel):
    keyword: str

    # @field_validator("keyword") 指定這個函式負責驗證 keyword 欄位。
    # @classmethod 是必要的：驗證器是類別方法，cls 為類別本身、v 為待驗證的值。
    @field_validator("keyword")
    @classmethod
    def keyword_no_space(cls, v: str) -> str:
        if " " in v:
            # raise ValueError 會被 Pydantic 攔截並包裝成 ValidationError。
            raise ValueError("關鍵字不可包含空格")
        # 回傳的值會成為欄位的最終值，這裡把關鍵字統一轉成小寫。
        return v.lower()


# 自動驗證：建立實例時就會執行上面的 field_validator。
data = ImageQuery(
    keyword="small cat"  # 含有空格，會直接丟出 ValidationError（驗證失敗）
)

# 註：因為上面建立實例時就會出錯，下面兩行其實不會被執行到。
# 若把 keyword 改成不含空格（例如 "cat"），才會順利印出結果。
print(data.model_dump())            # 轉成 dict
print(data.model_dump_json(indent=2))  # 轉成 JSON 字串
