"""教材 5.1 之三：模組匯入機制

為什麼要在資料庫單元前講這個？因為 SQLModel 建表靠的就是這個機制：

    class Image(SQLModel, table=True):   # ← 這個 class 定義「被執行」時
        ...                              #    才會註冊進 SQLModel.metadata

「定義 class」本身就是註冊動作，而 class 定義是在模組被 import 時執行的。
所以一個 models 檔案如果沒被任何地方 import，它的表就永遠不會被建出來
（教材 5.5 會再回到這件事）。

執行：uv run python practices/try_31_module.py
"""

print("=== 1. import 的當下，模組的全域範圍就會執行 ===")
from practices.module_a import fun01, fun02  # noqa: E402

print("\n=== 2. 之後才是呼叫函式 ===")
fun01()
fun02()

print("\n=== 3. 再 import 一次不會重複執行（模組有快取）===")
import practices.module_a  # noqa: E402, F401

print("  （上面沒有再出現 [module_a] 的訊息）")

print("""
對照 SQLModel：
    from app.models.image import Image   # ← 這一行讓 Image 的 class 定義被執行，
                                         #    表因此註冊進 metadata
    SQLModel.metadata.create_all(engine) # ← 這時才依註冊內容建表
""")
