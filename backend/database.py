"""MongoDB (Motor) layer for user/conversation/message storage.

Schema-compatible with the previous AdvisingBot deployment so existing Atlas
data and the frontend keep working: collections ``users``, ``conversations``,
``messages`` with the same fields. Catalog data (courses/programs) is NOT here —
that is loaded from ``data/`` by the advisor engine.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

load_dotenv()  # project-root .env

logger = logging.getLogger(__name__)


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> AsyncIOMotorDatabase:
        if cls.db is not None:
            return cls.db

        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable is required")
        db_name = os.getenv("MONGODB_DATABASE", "advising_bot")

        # Railway-internal Mongo runs without TLS; Atlas/external needs it.
        if "railway.internal" in mongo_uri:
            cls.client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=30000)
        else:
            if "?" not in mongo_uri:
                mongo_uri += "?retryWrites=true&w=majority"
            cls.client = AsyncIOMotorClient(
                mongo_uri, serverSelectionTimeoutMS=30000, tlsAllowInvalidCertificates=True
            )

        await cls.client.admin.command("ping")
        cls.db = cls.client[db_name]
        logger.info("Connected to MongoDB database: %s", db_name)
        await cls._create_indexes()
        return cls.db

    @classmethod
    async def _create_indexes(cls):
        if cls.db is None:
            return
        try:
            await cls.db.users.create_index("email", unique=True)
            await cls.db.conversations.create_index("user_id")
            await cls.db.conversations.create_index([("user_id", 1), ("created_at", -1)])
            await cls.db.messages.create_index("conversation_id")
            await cls.db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])
        except Exception as e:  # non-fatal
            logger.warning("Could not create indexes (non-fatal): %s", e)

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None

    @classmethod
    async def get_db(cls) -> AsyncIOMotorDatabase:
        if cls.db is None:
            await cls.connect()
        return cls.db


# ---- users ----

async def create_user(email: str, name: str, password_hash: str) -> dict[str, Any]:
    db = await MongoDB.get_db()
    user_doc = {
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
        "profile": {
            "major": None, "year": None, "minors": [], "concentration": None,
            "gpa": None, "expected_graduation": None, "completed_courses": [],
            "courses_taken": [], "interests": [], "career_goals": [],
        },
    }
    result = await db.users.insert_one(user_doc)
    user_doc["_id"] = str(result.inserted_id)
    return user_doc


async def get_user_by_email(email: str) -> Optional[dict[str, Any]]:
    db = await MongoDB.get_db()
    user = await db.users.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
    return user


async def get_user_by_id(user_id: str) -> Optional[dict[str, Any]]:
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(user_id):
        return None
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
    return user


async def update_user_profile(user_id: str, profile: dict[str, Any]) -> bool:
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(user_id):
        return False
    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"profile": profile, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


# ---- conversations ----

async def create_conversation(user_id: str, title: Optional[str] = None) -> dict[str, Any]:
    db = await MongoDB.get_db()
    conv_doc = {
        "user_id": user_id,
        "title": title or "New Conversation",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "message_count": 0,
    }
    result = await db.conversations.insert_one(conv_doc)
    conv_doc["_id"] = str(result.inserted_id)
    return conv_doc


async def get_conversations(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    db = await MongoDB.get_db()
    cursor = db.conversations.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
    out = []
    async for conv in cursor:
        conv["_id"] = str(conv["_id"])
        out.append(conv)
    return out


async def get_conversation(conversation_id: str) -> Optional[dict[str, Any]]:
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(conversation_id):
        return None
    conv = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    if conv:
        conv["_id"] = str(conv["_id"])
    return conv


async def delete_conversation(conversation_id: str) -> bool:
    db = await MongoDB.get_db()
    if not ObjectId.is_valid(conversation_id):
        return False
    await db.messages.delete_many({"conversation_id": conversation_id})
    result = await db.conversations.delete_one({"_id": ObjectId(conversation_id)})
    return result.deleted_count > 0


# ---- messages ----

async def add_message(conversation_id: str, role: str, content: str,
                      metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    db = await MongoDB.get_db()
    msg_doc = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {},
    }
    result = await db.messages.insert_one(msg_doc)
    msg_doc["_id"] = str(result.inserted_id)
    await db.conversations.update_one(
        {"_id": ObjectId(conversation_id)},
        {"$set": {"updated_at": datetime.utcnow()}, "$inc": {"message_count": 1}},
    )
    return msg_doc


async def get_messages(conversation_id: str, limit: int = 50) -> list[dict[str, Any]]:
    db = await MongoDB.get_db()
    cursor = db.messages.find({"conversation_id": conversation_id}).sort("timestamp", 1).limit(limit)
    out = []
    async for msg in cursor:
        msg["_id"] = str(msg["_id"])
        out.append(msg)
    return out
