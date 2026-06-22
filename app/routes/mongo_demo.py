"""MongoDB 圖片留言/註記 CRUD（教材單元九，補充教材）

用 PyMongo 原生 async 操作文件型資料庫，示範：
- collection 與 document（document 本質就是 dict）
- _id 是 ObjectId，回傳前要轉成字串
- 文件結構彈性：除了基本欄位，可帶任意額外欄位（extra="allow"）

collection：image_notes
"""

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.mongo import get_db

router = APIRouter(prefix="/api/v1/notes", tags=["mongo-notes"])


def get_collection():
    """取得 image_notes collection；Mongo 未連線時回 503。"""
    db = get_db()
    if db is None:
        raise HTTPException(503, "MongoDB 未連線")
    return db["image_notes"]


class NoteCreate(BaseModel):
    # extra="allow"：允許多帶基本欄位以外的任意鍵，展現文件型的 schema 彈性
    model_config = ConfigDict(extra="allow")

    image_filename: str
    text: str
    author: Optional[str] = None


def serialize(doc: dict) -> dict:
    """把 MongoDB 文件轉成可回傳的 dict：把 _id(ObjectId) 改成字串 id。"""
    doc["id"] = str(doc.pop("_id"))
    return doc


def to_object_id(note_id: str) -> ObjectId:
    """把字串轉成 ObjectId，格式錯誤回 400。"""
    try:
        return ObjectId(note_id)
    except InvalidId:
        raise HTTPException(400, "id 格式錯誤")


@router.post("", status_code=201)
async def create_note(payload: NoteCreate):
    """新增一則留言。"""
    coll = get_collection()
    doc = payload.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    result = await coll.insert_one(doc)  # 寫入，回傳含 inserted_id
    created = await coll.find_one({"_id": result.inserted_id})
    return serialize(created)


@router.get("")
async def list_notes(image_filename: Optional[str] = None, limit: int = 20):
    """列出留言；可用 image_filename 篩選某張圖的留言。"""
    coll = get_collection()
    query = {"image_filename": image_filename} if image_filename else {}
    cursor = coll.find(query).sort("created_at", -1).limit(limit)
    # async for 逐筆取出非同步游標的結果
    return [serialize(doc) async for doc in cursor]


@router.get("/{note_id}")
async def get_note(note_id: str):
    """依 id 取單則留言。"""
    coll = get_collection()
    doc = await coll.find_one({"_id": to_object_id(note_id)})
    if not doc:
        raise HTTPException(404, "找不到留言")
    return serialize(doc)


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: str):
    """依 id 刪除留言。"""
    coll = get_collection()
    result = await coll.delete_one({"_id": to_object_id(note_id)})
    if result.deleted_count == 0:
        raise HTTPException(404, "找不到留言")
