"""httpx 範例 23：查詢參數、自訂標頭、Cookie、逾時（非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_13 的 requests 同步版。
對應後端：GET /api/v1/images（列表，支援 keyword / limit，教材 4.6）

重點：
- params / headers / cookies / timeout 的用法和 requests 完全一致，
  只是改成 await client.get(...)。
- 可印 r.url 觀察 params 實際組成的查詢字串。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import asyncio

import httpx

URL = "http://localhost:8000/api/v1/images"


async def with_query_headers_cookies():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            URL,
            params={"keyword": "cat", "limit": 10},  # 會組成 ?keyword=cat&limit=10
            headers={"User-Agent": "MyApp/1.0"},  # 自訂標頭
            cookies={"session": "xyz"},  # 帶 cookie
            timeout=10,  # 逾時秒數
        )
    print("實際請求的 URL：", r.url)  # 觀察 params 組成的查詢字串
    print("結果筆數：", len(r.json()))
    return r


if __name__ == "__main__":
    asyncio.run(with_query_headers_cookies())
