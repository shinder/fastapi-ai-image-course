"""應用組態（教材 2.2）：從 .env 讀取設定，集中管理"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "my-fastapi")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # 單元九：MongoDB 連線設定
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "ai_image_db")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_VISION_MODEL: str = os.getenv("OLLAMA_VISION_MODEL", "gemma3:4b")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    # 教材 8.7：MediaPipe 手部偵測；模型檔已隨版控附上，遺失時用 scripts/download_models.py 重新下載
    HAND_MODEL_PATH: str = os.getenv("HAND_MODEL_PATH", "./ml_models/hand_landmarker.task")
    HAND_MAX_NUM: int = int(os.getenv("HAND_MAX_NUM", "2"))
    # 超過這個邊長就先縮圖再推論（座標是正規化的，縮圖不影響結果）
    HAND_MAX_SIDE: int = int(os.getenv("HAND_MAX_SIDE", "1280"))
    # 教材 附錄 D（H03 串流）：同時允許幾條 WebSocket 連線。
    # 每條連線都會自己建一個 detector（各佔一組原生執行緒與記憶體），
    # 不設上限的話一個班的人同時連進來就會把伺服器吃垮
    HAND_WS_MAX_CONN: int = int(os.getenv("HAND_WS_MAX_CONN", "4"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")


settings = Settings()
