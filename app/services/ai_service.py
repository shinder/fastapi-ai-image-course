"""本機 Hugging Face 影像分類（教材 6.3、6.7）

需安裝可選依賴：
    uv sync --extra ml

若未安裝 transformers/torch，import 時會 raise ImportError；
路由層會在實際呼叫時才觸發（lazy load）。
"""

from io import BytesIO

from PIL import Image

# 模組級單例（教材 6.7）
_classifier = None


def get_classifier():
    """啟動時載入一次（避免每個請求都載）"""
    global _classifier
    if _classifier is None:
        from transformers import pipeline  # lazy import

        _classifier = pipeline(
            "image-classification",
            model="google/vit-base-patch16-224",
        )
    return _classifier


def classify_image_bytes(content: bytes, top_k: int = 3) -> list[dict]:
    """傳入圖片 bytes，回傳前 top_k 個分類結果"""
    img = Image.open(BytesIO(content)).convert("RGB")
    classifier = get_classifier()
    results = classifier(img, top_k=top_k)
    # results 例：[{"label": "tabby cat", "score": 0.78}, ...]
    return [{"label": r["label"], "score": float(r["score"])} for r in results]
