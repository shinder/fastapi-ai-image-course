"""requests 範例 17：三種認證機制的帶法

對應教材 5.4（單元五 API 串接）

注意：本專案的端點未啟用認證，以下用示意 URL（api.example.com）
單純示範「認證資訊放在請求的哪裡」；串接需要認證的第三方 API 時照樣套用。

三種常見方式：
- API Key：放在 Header（X-API-Key）或 Query（?api_key=）
- Bearer Token：放在 Authorization: Bearer <token>
- Basic Auth：帳號 / 密碼，用 auth= 帶

本檔不會真的連線成功（示意 URL），重點在看程式碼怎麼帶認證。
"""

import requests
from requests.auth import HTTPBasicAuth

URL = "https://api.example.com"  # 示意：代表「需要認證的目標 API」
API_KEY = "MY_KEY"
TOKEN = "MY_TOKEN"


def api_key_in_header():
    return requests.get(URL, headers={"X-API-Key": API_KEY})


def api_key_in_query():
    return requests.get(URL, params={"api_key": API_KEY})


def bearer_token():
    return requests.get(URL, headers={"Authorization": f"Bearer {TOKEN}"})


def basic_auth():
    requests.get(URL, auth=HTTPBasicAuth("user", "password"))  # 完整寫法
    return requests.get(URL, auth=("user", "password"))  # 簡寫，等價


if __name__ == "__main__":
    print("本範例僅示範認證標頭的帶法，不會真的連線成功（示意 URL）。")
