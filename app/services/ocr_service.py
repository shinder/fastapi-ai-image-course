"""OCR 文字辨識（教材 6.4）

需安裝可選依賴：
    uv sync --extra ocr
"""

from io import BytesIO

from PIL import Image

_reader = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr  # lazy import

        # 支援繁中、英文
        _reader = easyocr.Reader(["ch_tra", "en"], gpu=False)
    return _reader


def extract_text(content: bytes) -> list[dict]:
    import numpy as np  # lazy import

    img = Image.open(BytesIO(content)).convert("RGB")
    arr = np.array(img)
    reader = get_reader()
    results = reader.readtext(arr)
    # results 例：[(bbox, text, confidence), ...]
    return [
        {
            "text": text,
            "confidence": float(conf),
            "bbox": [[float(x), float(y)] for x, y in bbox],
        }
        for bbox, text, conf in results
    ]
