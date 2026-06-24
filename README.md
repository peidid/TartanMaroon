# CMU-Q Academic Advising Assistant

An agentic-search advising assistant for Carnegie Mellon University in Qatar. An
LLM orchestrator plans and calls tools over a structured course/requirement
backbone (deterministic queries + a prerequisite DAG) and a retrieval layer over
policy/advising prose.

> Scope: an **engineering** advising Q&A system that works on campus. The verified
> neuro-symbolic *planning* research (solver, formalization faithfulness,
> uncertainty) is a later phase — see `0 Important Docs/Research Idea.md`.

## Architecture

```
   Orchestrator (Pydantic AI + OpenAI) — plans & calls tools, STREAMS its trace
         │                                                  │
   Structured tools (deterministic)                  Document tools (agentic)
   course_details / prerequisites / check_eligibility      find_documents(query)
   courses_unlocked_by / course_offerings / is_offered     read_document(source)
   list_programs / program_requirements / degree_progress  list_documents(category)
         │                                                    over policy/advising prose
   Repository (JSON now → MongoDB later)
     • courses + networkx prereq DAG
     • normalized Requirement trees (majors, minors, gen-ed) + degree_progress
```

Every run emits a normalized event stream (thinking · tool_call · tool_result ·
text · done) consumed by both the CLI and an SSE server, so the working process
is transparent to users — and ready to drive a Vercel UI via `EventSource`.

- **Structured backbone** — courses, requirements, offerings: typed Pydantic
  models, queried deterministically. Prereq strings are parsed into boolean ASTs
  and assembled into a `networkx` DAG.
- **Prose** — policies / student life / advising docs: an in-memory document
  library (~100 small files). The agent browses the catalog, finds docs by
  keyword (with snippets), and reads them *in full* — no chunking/embeddings, so
  tables and policies are never truncated.
- **Repository pattern** — JSON-file implementation now; MongoDB adapter is a
  config swap (prod target: Railway + MongoDB, UI on Vercel).

## Layout

```
src/advisor/
  config.py            # settings (.env): model names, paths, keys
  models.py            # Pydantic: Course, Offering, StudentState
  prereqs/             # boolean prereq parser → AST + evaluator (100% parse)
  etl/                 # load courses + offerings from raw data/ JSON
  graph/               # build the networkx prereq DAG
  requirements/        # normalize the 5 program shapes + degree_progress engine
  repository/          # base interface + JSON impl (+ Mongo later)
  retrieval/           # document library: catalog + keyword find + full read
  triage.py            # fast greeting/intro classifier (skips the tool loop)
  tools/               # deterministic advising tools
  streaming.py         # normalized event stream (CLI + SSE share it)
  agent.py             # Pydantic AI orchestrator
  server.py            # Starlette SSE endpoint for a web/Vercel UI
  cli.py               # local REPL / one-shot / index / serve
data/                  # raw knowledge base (see 0 Important Docs/DATA.md)
```

## Setup & usage

```bash
uv sync                              # Python 3.12 venv + deps
cp .env.example .env                 # then add your OPENAI_API_KEY

uv run advisor                       # interactive REPL — streams the working trace
uv run advisor chat "what's left for my CS degree?"
uv run advisor docs "transfer into CS"   # inspect/test the document library
uv run advisor serve                 # SSE server at /chat?q=... for the web UI
uv run pytest                        # deterministic suite (incl. 100% prereq parse on real data)
```

The CLI prints each tool call (`⚙ degree_progress(...)`) and its result above
the streamed answer. The SSE server emits the same events as JSON for a frontend.

## Web app (backend + frontend)

```
backend/        FastAPI + MongoDB (Motor) + JWT auth.  Routes: /api/auth/*,
                /api/conversations*, /api/chat/stream (SSE), /api/health.
                The chat engine is the advisor orchestrator; the streamed SSE
                events (tool_call · tool_result · token · answer) drive the UI's
                transparent reasoning trace. User profiles map → StudentState.
frontend/       Next.js 14 (App Router, Tailwind). Auth, profile, conversation
                history, and a live tool-call reasoning panel.
Dockerfile      Backend image for Railway (uv-based).
railway.json    Railway build (Dockerfile) + /api/health healthcheck.
```

### Deploy

- **Backend → Railway**: deploys from this repo's root `Dockerfile`. Set env
  vars `MONGODB_URI`, `MONGODB_DATABASE`, `OPENAI_API_KEY`, `JWT_SECRET_KEY`,
  `ALLOWED_ORIGINS` (your Vercel URL). Health: `/api/health`.
- **Frontend → Vercel**: set project **Root Directory = `frontend`**; env var
  `NEXT_PUBLIC_API_URL` = the Railway backend URL.
- Schema-compatible with the previous AdvisingBot Mongo (`users`/`conversations`/
  `messages`), so existing data and logins carry over (keep `JWT_SECRET_KEY`).

### Run locally

```bash
# backend (needs MONGODB_URI + OPENAI_API_KEY in .env)
uv run uvicorn backend.server:app --reload
# frontend
cd frontend && npm install && NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```
