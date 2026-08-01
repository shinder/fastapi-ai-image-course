"""用戶 CRUD（教材 5.7）

刻意挑「只有 id / name 兩個欄位」的 User 當第一個 CRUD 對象：
欄位少、沒有檔案上傳，可以把注意力完全放在 session / select / commit 上。
熟悉之後再看 images.py 的完整版（多了驗證、分頁、檔案處理）。

順帶一提：這個模組 import 了 app.models.user，因此 User / UserImage / Tag
三張表會在此時註冊進 SQLModel.metadata，啟動時的 create_all() 就會把它們建出來
（教材 5.5 說明過這個機制）。
"""

from fastapi import APIRouter, Form, HTTPException, status
from sqlmodel import select

from app.database import SessionDep
from app.models.user import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("")
def list_users(session: SessionDep, skip: int = 0, limit: int = 20):
    """Read：列表查詢（skip / limit 分頁，與 images 的參數一致）。

    教材 6.9 的用戶列表頁用的是同一組查詢——那裡把結果填進 HTML 樣板，
    這裡直接回 JSON，這就是「同一份查詢、兩種輸出」。
    """
    stmt = select(User).offset(skip).limit(limit)
    return session.exec(stmt).all()


@router.get("/{user_id}")
def get_user(session: SessionDep, user_id: int):
    """Read：取單筆。session.get() 是依主鍵查詢的捷徑，比 select 更直接。"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到這個用戶")
    return user


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(session: SessionDep, name: str = Form(...)):
    """Create：用表單欄位建立一筆。

    這裡用 Form 而非 JSON，方便直接從 HTML 表單或 Swagger UI 送出。
    """
    user = User(name=name)
    session.add(user)  # 加入 session（尚未寫入資料庫）
    session.commit()  # 提交交易，真正寫入
    session.refresh(user)  # 重新讀回，取得資料庫產生的 id
    return {"id": user.id, "name": user.name}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(session: SessionDep, user_id: int):
    """Delete：刪除成功回 204（無內容）。"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "找不到這個用戶")
    session.delete(user)
    session.commit()
