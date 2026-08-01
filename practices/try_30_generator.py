"""教材 5.1 之一：產生器函式（generator function）

為什麼在資料庫單元之前先講這個？因為 5.6 的依賴注入長這樣：

    def get_session():
        with Session(engine) as session:
            yield session          # ← 這個 yield 是什麼意思？

看懂 yield，才看得懂「FastAPI 如何在請求前借出 session、請求後自動收回」。

執行：uv run python practices/try_30_generator.py
"""


def count_down():
    """有 yield 的函式就是產生器函式：呼叫它不會執行任何內容，只會拿到一個產生器物件。"""
    print("  [函式內] 開始")
    yield 3
    yield 2
    yield 1
    print("  [函式內] 結束")


def with_cleanup():
    """yield 前後各做一件事——這正是 get_session 的形狀。

    yield 之前 = 借出資源前的準備；yield 之後 = 用完之後的收尾。
    """
    print("  [函式內] 準備資源")
    yield "資源"
    print("  [函式內] 收回資源")


print("=== 1. 呼叫產生器函式，函式體並不會執行 ===")
gen = count_down()
print("拿到的東西：", gen)

print("\n=== 2. 每次 next() 才執行到下一個 yield ===")
print("next() →", next(gen))
print("next() →", next(gen))
print("next() →", next(gen))
try:
    next(gen)
except StopIteration:
    print("再要就 StopIteration：值取完了")

print("\n=== 3. for 迴圈會自動處理 next 與 StopIteration ===")
for n in count_down():
    print("  取到", n)

print("\n=== 4. yield 前後：資源的借出與收回 ===")
gen2 = with_cleanup()
res = next(gen2)  # 執行到 yield，把資源借出來
print("拿到：", res)
print("（使用中…）")
try:
    next(gen2)  # 繼續往下跑，執行收尾
except StopIteration:
    pass

print("\n=== 5. with + yield：FastAPI 依賴注入的實際寫法 ===")
print("""
    def get_session():
        with Session(engine) as session:
            yield session
    # 請求進來 → 執行到 yield，把 session 交給路由函式
    # 路由跑完 → 從 yield 繼續往下，with 區塊結束，session 自動關閉
""")
