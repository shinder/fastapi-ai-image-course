"""Requests 套件用法示範（教材 5.2、5.3、5.4）

範例打的是本專案在單元三、四寫好的 API，執行前請先啟動開發伺服器：
    uv run fastapi dev app/main.py
再執行：
    uv run python scripts/requests_demo.py
"""

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)
from urllib3.util.retry import Retry


def basic_get():
    """教材 5.2 基本 GET"""
    r = requests.get("http://localhost:8000/api/v1/images/1")  # 單元四 4.6 取得單一圖片
    print(r.status_code)
    print(r.headers["Content-Type"])
    print(r.json())


def basic_post():
    """教材 5.2 基本 POST"""
    # 對應單元四 4.6 建立端點，欄位是 title / description
    data = {"title": "我的圖片", "description": "一張示範圖片"}
    r = requests.post("http://localhost:8000/api/v1/images", json=data)
    print(r.status_code)
    print(r.json())


def with_exceptions():
    """教材 5.2 例外處理"""
    try:
        r = requests.get("http://localhost:8000/api/v1/images/1", timeout=5)
        r.raise_for_status()
        return r.json()
    except Timeout:
        print("請求逾時")
    except ConnectionError:
        print("連線失敗")
    except HTTPError as e:
        print(f"HTTP 錯誤：{e.response.status_code}")
    except RequestException as e:
        print(f"其他錯誤：{e}")


def with_query_headers_cookies():
    """教材 5.3 Query / Headers / Cookies / Timeout"""
    return requests.get(
        "http://localhost:8000/api/v1/images",  # 單元四列表端點，支援 keyword/limit
        params={"keyword": "cat", "limit": 10},
        headers={"Authorization": "Bearer abc123", "User-Agent": "MyApp/1.0"},
        cookies={"session": "xyz"},
        timeout=10,
    )


def upload_file():
    """教材 5.3 上傳檔案"""
    with open("test_images/cat.jpg", "rb") as f:
        files = {"file": ("cat.jpg", f, "image/jpeg")}
        r = requests.post(
            "http://localhost:8000/api/v1/images/upload",
            files=files,
            data={"title": "我的貓"},
        )
        print(r.json())


def session_demo():
    """教材 5.3 Session 連線重用"""
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer abc123"})
    r1 = session.get("http://localhost:8000/users/me")  # 單元二 2.4 範例路由
    r2 = session.get("http://localhost:8000/api/v1/images")  # 單元四圖片列表
    return r1, r2


def session_with_retry():
    """教材 5.3 重試機制"""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


def auth_examples():
    """教材 5.4 認證機制（本服務未啟用認證，以下用示意 URL 示範認證標頭怎麼帶）"""
    api_key = "MY_KEY"
    token = "MY_TOKEN"

    # API Key 在 Header
    requests.get("https://api.example.com", headers={"X-API-Key": api_key})

    # API Key 在 Query
    requests.get("https://api.example.com", params={"api_key": api_key})

    # Bearer Token
    requests.get(
        "https://api.example.com",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Basic Auth
    requests.get("https://api.example.com", auth=HTTPBasicAuth("user", "password"))
    requests.get("https://api.example.com", auth=("user", "password"))


if __name__ == "__main__":
    print("=== basic GET ===")
    basic_get()
    print("\n=== basic POST ===")
    basic_post()
