"""httpx 範例 26：自動重試機制（非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_16 的 requests 重試版。

重點（與 requests 的重要差異）：
- httpx 內建的重試在「傳輸層」設定：httpx.AsyncHTTPTransport(retries=N)，
  但它**只重試連線層錯誤**（連不上、DNS 失敗…），**不會重試 5xx 狀態碼**。
- requests + urllib3 的 Retry 則可用 status_forcelist 對 5xx 重試（見 try_16）。
- 若 httpx 也想對 5xx 重試，要自己包重試迴圈，或用 tenacity 這類套件。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import asyncio

import httpx


def build_client_with_retry() -> httpx.AsyncClient:
    # retries=3：連線層錯誤最多重試 3 次（不含 5xx 狀態碼）
    transport = httpx.AsyncHTTPTransport(retries=3)
    return httpx.AsyncClient(transport=transport)


async def main():
    async with build_client_with_retry() as client:
        r = await client.get("http://localhost:8000/api/v1/images", timeout=10)
        print("狀態碼：", r.status_code)


if __name__ == "__main__":
    asyncio.run(main())
