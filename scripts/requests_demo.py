"""Requests 套件用法示範（教材 5.2、5.3、5.4）

執行：
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
    r = requests.get("https://jsonplaceholder.typicode.com/photos/1")
    print(r.status_code)
    print(r.headers["Content-Type"])
    print(r.json())


def basic_post():
    """教材 5.2 基本 POST"""
    data = {"title": "我的圖片", "url": "https://example.com/img.jpg"}
    r = requests.post("https://jsonplaceholder.typicode.com/photos", json=data)
    print(r.status_code)
    print(r.json())


def with_exceptions():
    """教材 5.2 例外處理"""
    try:
        r = requests.get("https://api.example.com/data", timeout=5)
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
        "https://api.example.com/images",
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
    r1 = session.get("https://api.example.com/users/me")
    r2 = session.get("https://api.example.com/images")
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
    """教材 5.4 認證機制"""
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
