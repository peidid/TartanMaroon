"""FastAPI backend for the TartanMaroon advising assistant.

API-compatible with the previous deployment (auth / conversations / SSE chat),
but the engine is the single transparent orchestrator from the ``advisor``
package. The streaming endpoint surfaces the real working process — every tool
call, its result, and the streamed answer — over SSE.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, EmailStr
from starlette.requests import Request

from advisor.agent import Deps, build_agent
from advisor.config import settings
from advisor.repository.json_repo import JsonRepository
from advisor.streaming import AgentStreamer
from advisor.triage import triage_message

from .auth import create_token, get_current_user, hash_password, verify_password
from .database import (
    MongoDB, add_message, create_conversation, create_user, delete_conversation,
    get_conversation, get_conversations, get_messages, get_user_by_email,
    update_user_profile,
)
from .profile_map import profile_to_student

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Engine singletons + in-process conversation history (pydantic-ai messages).
_repo: Optional[JsonRepository] = None
_agent = None
_histories: dict[str, Any] = {}


def get_engine():
    global _repo, _agent
    if _repo is None:
        logger.info("Loading catalog + programs…")
        _repo = JsonRepository(settings.data_dir)
        _agent = build_agent()
        logger.info("Engine ready: %d courses, %d programs",
                    len(_repo.all_courses()), len(_repo.list_programs()))
    return _repo, _agent


# ---- request models (frontend contract) ----

class UserRegister(BaseModel):
    email: EmailStr
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class CourseTaken(BaseModel):
    code: str
    name: Optional[str] = None
    grade: str
    semester: str
    units: Optional[float] = None


class UserProfile(BaseModel):
    major: Optional[str] = None
    year: Optional[str] = None
    minors: list[str] = []
    concentration: Optional[str] = None
    gpa: Optional[float] = None
    expected_graduation: Optional[str] = None
    completed_courses: list[str] = []
    courses_taken: list[CourseTaken] = []
    interests: list[str] = []
    career_goals: list[str] = []


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    system: str = "advisor"


class ConversationCreate(BaseModel):
    title: Optional[str] = None


# ---- app ----

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting server…")
    await MongoDB.connect()
    get_engine()
    # Warm the prose embedding index in the background (don't block healthcheck).
    async def _warm():
        try:
            from advisor.retrieval.index import ProseIndex
            await asyncio.to_thread(ProseIndex.get, settings.data_dir)
            logger.info("Prose index warm.")
        except Exception as e:
            logger.warning("Prose index warmup failed (lazy on first use): %s", e)
    asyncio.create_task(_warm())
    yield
    await MongoDB.disconnect()


app = FastAPI(title="TartanMaroon Advising API", version="2.0.0", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _cors_safe_errors(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc)
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(status_code=500, content={"detail": str(exc)}, headers=headers)


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _chunk_text(text: str, size: int = 24):
    """Yield small slices so a canned reply still streams in token-by-token."""
    for i in range(0, len(text), size):
        yield text[i:i + size]


# ---- auth ----

@app.post("/api/auth/register")
async def register(data: UserRegister):
    if await get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await create_user(data.email, data.name, hash_password(data.password))
    return {"user": {"id": user["_id"], "email": user["email"], "name": user["name"]},
            "token": create_token(user["_id"], user["email"])}


@app.post("/api/auth/login")
async def login(data: UserLogin):
    user = await get_user_by_email(data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"user": {"id": user["_id"], "email": user["email"], "name": user["name"],
                     "profile": user.get("profile", {})},
            "token": create_token(user["_id"], user["email"])}


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {"id": user["_id"], "email": user["email"], "name": user["name"],
            "profile": user.get("profile", {})}


@app.put("/api/auth/profile")
async def update_profile(profile: UserProfile, user: dict = Depends(get_current_user)):
    await update_user_profile(user["_id"], profile.model_dump())
    return {"success": True, "profile": profile.model_dump()}


# ---- conversations ----

@app.get("/api/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    return {"conversations": await get_conversations(user["_id"])}


@app.post("/api/conversations")
async def new_conversation(data: Optional[ConversationCreate] = None,
                           user: dict = Depends(get_current_user)):
    return await create_conversation(user["_id"], data.title if data else None)


@app.get("/api/conversations/{conversation_id}")
async def get_conv(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["user_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    conv["messages"] = await get_messages(conversation_id)
    return conv


@app.delete("/api/conversations/{conversation_id}")
async def delete_conv(conversation_id: str, user: dict = Depends(get_current_user)):
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv["user_id"] != user["_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await delete_conversation(conversation_id)
    return {"success": True}


# ---- chat helpers ----

async def _resolve_conversation(data: ChatMessage, user: dict) -> str:
    if data.conversation_id:
        conv = await get_conversation(data.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized")
        return data.conversation_id
    title = (data.message[:50] + "…") if len(data.message) > 50 else data.message
    conv = await create_conversation(user["_id"], title)
    return conv["_id"]


# ---- streaming chat (primary path) ----

@app.post("/api/chat/stream")
async def chat_stream(data: ChatMessage, user: dict = Depends(get_current_user)):
    repo, agent = get_engine()
    conversation_id = await _resolve_conversation(data, user)
    await add_message(conversation_id, "user", data.message)
    student = profile_to_student(user.get("profile", {}), user.get("name"))

    async def generate():
        # Fast path: greetings / "what can you do?" skip the full tool agent.
        triaged = await triage_message(data.message)
        if triaged.category in ("greeting", "general") and triaged.reply:
            reply = triaged.reply
            yield _sse({"type": "thinking", "message": "Quick reply"})
            for chunk in _chunk_text(reply):
                yield _sse({"type": "token", "data": {"text": chunk}})
            await add_message(conversation_id, "assistant", reply,
                              metadata={"engine": "advisor_triage",
                                        "category": triaged.category, "tools_used": []})
            yield _sse({"type": "answer", "data": {
                "content": reply, "conversation_id": conversation_id,
                "agents_used": [], "agent_details": {}, "execution_stats": {},
                "phase_timing": {}}})
            yield _sse({"type": "done", "data": {}})
            return

        streamer = AgentStreamer(agent, Deps(repo=repo, student=student))
        history = _histories.get(conversation_id)
        tools_used: list[str] = []
        answer_text = ""
        had_error = False
        try:
            async for ev in streamer.stream(data.message, history):
                if ev.type == "tool_call":
                    tools_used.append(ev.tool)
                    yield _sse({"type": "tool_call", "message": f"Calling {ev.tool}",
                                "data": {"tool": ev.tool, "args": ev.args or {}}})
                elif ev.type == "tool_result":
                    yield _sse({"type": "tool_result", "data": {"tool": ev.tool, "result": ev.result}})
                elif ev.type == "thinking":
                    yield _sse({"type": "thinking", "message": ev.text})
                elif ev.type == "text":
                    answer_text += ev.text or ""
                    yield _sse({"type": "token", "data": {"text": ev.text}})
                elif ev.type == "error":
                    had_error = True
                    yield _sse({"type": "error", "data": {"message": ev.text}})
                elif ev.type == "done":
                    answer_text = ev.text or answer_text
        except Exception as e:  # pragma: no cover
            had_error = True
            yield _sse({"type": "error", "data": {"message": str(e)}})

        if not had_error:
            _histories[conversation_id] = streamer.last_messages
            await add_message(conversation_id, "assistant", answer_text,
                              metadata={"engine": "advisor_orchestrator",
                                        "tools_used": tools_used})
            yield _sse({"type": "answer", "data": {
                "content": answer_text, "conversation_id": conversation_id,
                "agents_used": sorted(set(tools_used)),
                "agent_details": {}, "execution_stats": {}, "phase_timing": {}}})
        yield _sse({"type": "done", "data": {}})

    return StreamingResponse(generate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})


# ---- non-streaming chat ----

@app.post("/api/chat")
async def chat(data: ChatMessage, user: dict = Depends(get_current_user)):
    repo, agent = get_engine()
    conversation_id = await _resolve_conversation(data, user)
    await add_message(conversation_id, "user", data.message)
    student = profile_to_student(user.get("profile", {}), user.get("name"))

    triaged = await triage_message(data.message)
    if triaged.category in ("greeting", "general") and triaged.reply:
        await add_message(conversation_id, "assistant", triaged.reply,
                          metadata={"engine": "advisor_triage", "category": triaged.category})
        return {"conversation_id": conversation_id, "response": triaged.reply, "agents_used": []}

    result = await agent.run(data.message, deps=Deps(repo=repo, student=student),
                             message_history=_histories.get(conversation_id))
    _histories[conversation_id] = result.all_messages()
    answer = result.output
    await add_message(conversation_id, "assistant", answer,
                      metadata={"engine": "advisor_orchestrator"})
    return {"conversation_id": conversation_id, "response": answer, "agents_used": []}


# ---- systems / health ----

@app.get("/api/systems")
async def list_systems():
    return {"available": True, "default": "advisor", "systems": [{
        "id": "advisor",
        "name": "Transparent Advising Orchestrator",
        "description": ("A single orchestrator that plans and calls verified tools over the "
                        "course/requirement backbone and policy retrieval. Every tool call and "
                        "the streamed answer are shown live."),
        "streaming": True,
        "ablation_variable": "production",
    }]}


@app.get("/api/health")
async def health():
    try:
        db = await MongoDB.get_db()
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/")
async def root():
    return {"name": "TartanMaroon Advising API", "version": "2.0.0", "docs": "/docs"}
