"""SSE server exposing the streaming advising agent to a web UI.

`GET /chat?q=...&session=...` streams Server-Sent Events whose payloads are
:class:`AdvisorEvent` JSON (thinking / text / tool_call / tool_result / done).
The Vercel frontend can consume this with ``EventSource`` and render the live
working trace. In-memory per-session history; swap for real auth + the Mongo
repository in production.
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

from .agent import Deps, build_agent
from .config import settings
from .models import StudentState
from .repository.json_repo import JsonRepository
from .streaming import AgentStreamer

_repo = JsonRepository(settings.data_dir)
_agent = build_agent()
_sessions: dict[str, object] = {}

# Demo student; replace with an authenticated profile lookup in production.
_DEMO = StudentState(
    program="computer_science",
    completed={"15-112": "A", "21-127": "B", "15-122": "A", "15-150": "A", "21-120": "A"},
)


async def health(_request):
    return JSONResponse({"ok": True, "courses": len(_repo.all_courses()),
                         "programs": len(_repo.list_programs())})


async def chat(request):
    q = request.query_params.get("q", "").strip()
    session = request.query_params.get("session", "default")
    if not q:
        return JSONResponse({"error": "missing 'q'"}, status_code=400)

    streamer = AgentStreamer(_agent, Deps(repo=_repo, student=_DEMO))
    history = _sessions.get(session)

    async def gen():
        async for ev in streamer.stream(q, history):
            yield {"event": ev.type, "data": ev.model_dump_json()}
        _sessions[session] = streamer.last_messages

    return EventSourceResponse(gen())


app = Starlette(
    routes=[Route("/health", health), Route("/chat", chat)],
    middleware=[Middleware(CORSMiddleware, allow_origins=["*"],
                           allow_methods=["*"], allow_headers=["*"])],
)
