"""關聯範例（教材 4.4 補充）：一對多 + 多對多

串成一條完整關聯：
    User  —(一對多)→  UserImage  ←(多對多)→  Tag

注意：此檔僅作示範，預設不會被建表。原因：SQLModel 的 table=True 模型是在
「class 定義被執行（= 模組被 import）時」才由 metaclass 自動註冊進 SQLModel.metadata；
本模組啟動時沒被任何地方 import，故這些表從未註冊，init_db() 的 create_all() 也不會建。
若要啟用，需在 app/database.py 的 init_db() 呼叫前先 import 此模組（讓 class 定義被執行）。
"""

from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class ImageTagLink(SQLModel, table=True):
    """多對多的「關聯表（中介表）」：只放兩邊的外鍵，兩者合為複合主鍵"""

    __tablename__ = "image_tag_links"

    image_id: Optional[int] = Field(default=None, foreign_key="user_images.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tags.id", primary_key=True)


class User(SQLModel, table=True):
    # 表名明訂為 users：user 是 PostgreSQL 的保留字，當表名容易出問題
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    # 一對多：一個 User 有多張 UserImage
    images: list["UserImage"] = Relationship(back_populates="owner")


class UserImage(SQLModel, table=True):
    """為避免與 app.models.image.Image 衝突，使用獨立表"""

    __tablename__ = "user_images"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    # 一對多（多的一方）：owner_id 是真正存進表的外鍵
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")
    owner: Optional[User] = Relationship(back_populates="images")
    # 多對多：用 link_model 指定中介表，兩邊都是 list
    tags: list["Tag"] = Relationship(back_populates="images", link_model=ImageTagLink)


class Tag(SQLModel, table=True):
    """標籤：一個 Tag 可貼多張圖，一張圖可有多個 Tag（多對多）"""

    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    images: list["UserImage"] = Relationship(back_populates="tags", link_model=ImageTagLink)
