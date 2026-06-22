"""MongoDB 連線（教材單元九，補充教材）

用 PyMongo 原生 async（AsyncMongoClient）連線；Motor 已被官方棄用，FastAPI 改用此 API。
連不到時不讓整個應用崩潰：印警告並讓 client 保持 None，沒用到 Mongo 的路由仍可運作
（與單元四 init_db 的優雅降級精神一致）。
"""

from typing import Optional

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError

from app.config import settings

# 全域共用一個連線 client；連線失敗時為 None
_client: Optional[AsyncMongoClient] = None


async def connect_mongo() -> bool:
    """應用啟動時呼叫：建立連線並實際 ping 一次確認可達。"""
    global _client
    try:
        # serverSelectionTimeoutMS 設短一點，連不到時不會卡太久
        client = AsyncMongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")  # 真的連一次，確認伺服器可達
        _client = client
        print(f"✅ MongoDB 連線成功：{settings.MONGO_URL}")
        return True
    except PyMongoError as exc:
        _client = None
        print("=" * 70)
        print("⚠️  無法連線到 MongoDB，已略過。沒用到 Mongo 的功能仍可正常使用。")
        print(f"   MONGO_URL：{settings.MONGO_URL}")
        print(f"   錯誤：{exc}")
        print("=" * 70)
        return False


async def close_mongo() -> None:
    """應用關閉時呼叫：關閉連線、釋放資源。"""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def get_db():
    """取得資料庫物件；未連線時回 None。"""
    if _client is None:
        return None
    return _client[settings.MONGO_DB]
