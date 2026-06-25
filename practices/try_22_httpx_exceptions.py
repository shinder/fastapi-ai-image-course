"""httpx 範例 22：例外處理（非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_12 的 requests 同步版。
對應後端：GET /api/v1/images/{id}（教材 4.6）

重點：httpx 的例外名稱和 requests 不同，但對應關係很直接：
  - httpx.TimeoutException ↔ requests.Timeout
  - httpx.HTTPStatusError  ↔ requests.HTTPError（raise_for_status 時丟）
  - httpx.RequestError     ↔ requests.RequestException（連線層錯誤的基類，放最後）
  - httpx.ConnectError 屬於 RequestError，連不上後端時會丟。
except 同樣由「具體」到「一般」排列；timeout 設在 AsyncClient(timeout=...)。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import asyncio

import httpx

URL = "http://localhost:8000/api/v1/images/1"


async def with_exceptions():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(URL)
            r.raise_for_status()  # 4xx / 5xx 會丟 HTTPStatusError
            return r.json()
    except httpx.TimeoutException:
        print("請求逾時")
    except httpx.HTTPStatusError as e:
        print(f"HTTP 錯誤：{e.response.status_code}")
    except httpx.RequestError as e:  # 連線層錯誤的基類，放最後當後援
        print(f"連線錯誤：{e}")


if __name__ == "__main__":
    print(asyncio.run(with_exceptions()))
