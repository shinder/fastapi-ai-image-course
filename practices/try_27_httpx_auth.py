"""httpx 範例 27：三種認證機制的帶法（非同步）

對應教材 5.6（httpx 非同步寫法）；對應 try_17 的 requests 版。

注意：本專案的端點未啟用認證，以下用示意 URL（api.example.com）
單純示範認證資訊放在請求的哪裡；帶法和 requests 幾乎一樣，只是改成 AsyncClient。

三種常見方式：
- API Key：放在 Header（X-API-Key）或 Query（?api_key=）
- Bearer Token：放在 Authorization: Bearer <token>
- Basic Auth：用 auth=httpx.BasicAuth(帳, 密) 或 auth=(帳, 密)

本檔不會真的連線成功（示意 URL），重點在看程式碼怎麼帶認證。
"""

import httpx

URL = "https://api.example.com"  # 示意：代表「需要認證的目標 API」
API_KEY = "MY_KEY"
TOKEN = "MY_TOKEN"


async def api_key_in_header():
    async with httpx.AsyncClient() as client:
        return await client.get(URL, headers={"X-API-Key": API_KEY})


async def api_key_in_query():
    async with httpx.AsyncClient() as client:
        return await client.get(URL, params={"api_key": API_KEY})


async def bearer_token():
    async with httpx.AsyncClient() as client:
        return await client.get(URL, headers={"Authorization": f"Bearer {TOKEN}"})


async def basic_auth():
    async with httpx.AsyncClient() as client:
        # httpx.BasicAuth，或直接 auth=("user", "password")
        return await client.get(URL, auth=httpx.BasicAuth("user", "password"))


if __name__ == "__main__":
    print("本範例僅示範認證標頭的帶法，不會真的連線成功（示意 URL）。")
