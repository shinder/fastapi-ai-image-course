"""一對多關聯範例（教材 4.4 補充）

注意：此檔僅作示範。若要啟用，需在 app/database.py 的 init_db()
呼叫前 import 此模組，並調整 Image 的 owner_id 欄位。
"""
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    # 表名明訂為 users：user 是 PostgreSQL 的保留字，當表名容易出問題
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    images: list["UserImage"] = Relationship(back_populates="owner")


class UserImage(SQLModel, table=True):
    """為避免與 app.models.image.Image 衝突，使用獨立表"""
    __tablename__ = "user_images"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")
    owner: Optional[User] = Relationship(back_populates="images")
