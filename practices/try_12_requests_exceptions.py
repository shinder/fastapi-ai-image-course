"""requests 範例 12：例外處理

對應教材 5.2（單元五 API 串接）
對應後端：GET /api/v1/images/{id}（教材 4.6）

重點：
- 網路請求隨時可能失敗，務必處理例外，否則程式會直接崩潰。
- requests 的例外有繼承關係，except 要由「具體」到「一般」排列：
  - Timeout：逾時（一定要設 timeout，否則對方卡住會一直等）
  - ConnectionError：連不上（DNS 失敗、伺服器沒啟動…）
  - HTTPError：r.raise_for_status() 在 4xx / 5xx 時主動丟出
  - RequestException：以上全部的基底類別，放最後當後援
- 想觀察 HTTPError，可把 URL 的 id 改成不存在的（例如 /images/999999）會回 404。

執行前請先啟動後端：
    uvicorn app.main:app --reload
"""

import requests
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)

URL = "http://localhost:8000/api/v1/images/1"


def with_exceptions():
    try:
        r = requests.get(URL, timeout=5)  # timeout 防止無限等待
        r.raise_for_status()  # 4xx / 5xx 會丟 HTTPError
        return r.json()
    except Timeout:
        print("請求逾時")
    except ConnectionError:
        print("連線失敗（後端沒啟動？）")
    except HTTPError as e:
        print(f"HTTP 錯誤：{e.response.status_code}")
    except RequestException as e:  # 基底類別，放最後當後援
        print(f"其他錯誤：{e}")


if __name__ == "__main__":
    print(with_exceptions())
