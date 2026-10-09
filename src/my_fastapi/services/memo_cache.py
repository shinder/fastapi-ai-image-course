"""以檔案雜湊為 key 的記憶體快取（教材 8.5）

AI 推論很貴——一張圖跑視覺模型動輒數秒。但同一張圖跑兩次，答案是一樣的，
沒有理由算第二次。用圖片內容的 SHA-256 當 key（教材 3.7），就能認出「這張圖
我算過了」——**不管它叫什麼檔名**。

這裡刻意先用最陽春的 dict，把「快取」這個觀念單獨講清楚，不必先裝 Redis。
它的三個限制也正好帶出附錄 E 為什麼要換成 Redis：

  1. 存在行程的記憶體裡 → 伺服器一重啟就全沒了
  2. 多個 worker 各有各的 dict → 彼此不共用，命中率大打折扣
  3. 沒有容量上限、沒有過期機制 → 跑久了會一直吃記憶體

附錄 E 會把同一組介面換成 Redis，上面三點就都解決了。
"""

import hashlib
from typing import Any

# key: 圖片內容的 sha256；value: 推論結果
_store: dict[str, Any] = {}

# 命中率統計，用來驗證快取確實有作用
_stats = {"hit": 0, "miss": 0}


def image_key(content: bytes, prefix: str) -> str:
    """以圖片內容算出快取 key（教材 3.7）。

    prefix 用來區隔不同用途——同一張圖的「分類結果」與「描述文字」是兩件事，
    不能共用同一個 key。
    """
    return f"{prefix}:{hashlib.sha256(content).hexdigest()}"


def get(key: str) -> Any | None:
    """查快取。命中回傳結果，未命中回傳 None。"""
    if key in _store:
        _stats["hit"] += 1
        return _store[key]
    _stats["miss"] += 1
    return None


def set(key: str, value: Any) -> None:
    """寫入快取。"""
    _store[key] = value


def stats() -> dict[str, Any]:
    """命中率統計。"""
    total = _stats["hit"] + _stats["miss"]
    return {
        **_stats,
        "total": total,
        "hit_rate": round(_stats["hit"] / total, 3) if total else 0.0,
        "cached_items": len(_store),
    }


def clear() -> None:
    """清空快取（測試與教學示範用）。"""
    _store.clear()
    _stats.update(hit=0, miss=0)
