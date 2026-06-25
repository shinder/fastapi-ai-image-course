"""requests 範例 16：自動重試機制

對應教材 5.3（單元五 API 串接）
示範對「暫時性失敗」自動重試（不限定特定端點）。

重點：
- 伺服器偶發 5xx、網路抖動時，自動重試常能救回請求。
- 用 urllib3 的 Retry 設定重試策略，掛到 Session 的 HTTPAdapter：
  - total：最多重試次數
  - backoff_factor：指數退避，每次失敗等待 0.5、1、2… 秒再試
  - status_forcelist：哪些狀態碼才觸發重試
- 掛上 adapter 後，之後用這個 session 發的請求都會自動套用重試。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session_with_retry() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,  # 最多重試 3 次
        backoff_factor=0.5,  # 0.5、1、2 秒（指數退避）
        status_forcelist=[500, 502, 503, 504],  # 這些狀態碼才重試
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)  # 掛到兩種協定
    session.mount("http://", adapter)
    return session


if __name__ == "__main__":
    session = build_session_with_retry()
    r = session.get("http://localhost:8000/api/v1/images", timeout=10)
    print("狀態碼：", r.status_code)
