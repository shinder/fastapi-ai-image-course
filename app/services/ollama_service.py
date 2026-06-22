"""Ollama 本地視覺模型整合（教材 5.5）"""
import json

from ollama import Client, ResponseError

from app.config import settings

# 全域 Client（會重用底層 HTTP 連線）
client = Client(host=settings.OLLAMA_HOST)


def _chat(**kwargs):
    """呼叫 Ollama chat，把連線／回應錯誤轉成清楚的 RuntimeError（教材 5.5）

    Ollama 沒啟動時，套件會丟內建的 ConnectionError；模型不存在等問題則是
    ollama.ResponseError。統一在此攔截，避免路由層出現難以理解的 500。
    """
    try:
        return client.chat(**kwargs)
    except ConnectionError as exc:
        raise RuntimeError(
            f"無法連線到 Ollama 服務（{settings.OLLAMA_HOST}），請確認 ollama 是否已啟動"
        ) from exc
    except ResponseError as exc:
        raise RuntimeError(f"Ollama 回應錯誤：{exc}") from exc


def describe_image(content: bytes, prompt: str = "請以繁體中文描述這張圖片") -> str:
    """請 Ollama 視覺模型描述圖片內容"""
    response = _chat(
        model=settings.OLLAMA_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": [content],  # 直接傳 bytes，套件會自動處理
            }
        ],
        options={
            "temperature": 0.3,  # 描述任務不需太發散
            "num_predict": 500,  # 對應 max_tokens
        },
    )
    return response["message"]["content"]


def extract_invoice_info(content: bytes) -> dict:
    """從發票圖片抽取結構化資訊（教材 5.5 結構化抽取）"""
    response = _chat(
        model=settings.OLLAMA_VISION_MODEL,
        format="json",  # 強制 JSON 輸出
        messages=[
            {
                "role": "user",
                "content": (
                    "請從這張發票圖片擷取資訊，回傳 JSON 格式："
                    '{"vendor": 商家, "date": 日期, "total_amount": 總金額, '
                    '"items": [{"name": 品項, "price": 價格}]}'
                ),
                "images": [content],
            }
        ],
        options={"temperature": 0.0},  # 結構化任務用 0 確保穩定
    )
    raw = response["message"]["content"]
    # 即使指定 format="json"，模型仍可能因輸出被截斷等回傳非合法 JSON，需兜底
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"模型未回傳合法 JSON：{raw[:200]}") from exc


def describe_image_via_openai_compat(encoded_b64: str) -> str:
    """進階：透過 Ollama 的 OpenAI 相容介面（教材 5.5 進階）

    需安裝可選依賴：uv sync --extra openai
    """
    from openai import OpenAI  # lazy import

    oa_client = OpenAI(
        base_url=f"{settings.OLLAMA_HOST}/v1",
        api_key="ollama",  # 任意字串即可，Ollama 不驗證
    )

    response = oa_client.chat.completions.create(
        model=settings.OLLAMA_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "請以繁體中文描述這張圖片"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_b64}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content or ""
