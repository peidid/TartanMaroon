"""Local CLI for the advising assistant.

Usage:
    uv run advisor                  # interactive REPL (streams the working trace)
    uv run advisor chat "question"  # one-shot
    uv run advisor docs ["query"]   # inspect / test the document library
    uv run advisor serve            # SSE server for a web/Vercel UI
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich.console import Console

from .agent import Deps, build_agent
from .config import settings
from .models import StudentState
from .repository.json_repo import JsonRepository
from .streaming import AgentStreamer

app = typer.Typer(add_completion=False, help="CMU-Q agentic advising assistant.")
console = Console()

# Demo student until a real profile loader exists.
DEMO_STUDENT = StudentState(
    program="computer_science",
    completed={"15-112": "A", "21-127": "B", "15-122": "A", "15-150": "A", "21-120": "A"},
)


def _render(ev) -> None:
    """Render one streamed event to the terminal."""
    if ev.type == "tool_call":
        args = ", ".join(f"{k}={v!r}" for k, v in (ev.args or {}).items())
        console.print(f"[yellow]⚙  {ev.tool}[/]([dim]{args}[/])")
    elif ev.type == "tool_result":
        console.print(f"   [dim]↳ {ev.result}[/]")
    elif ev.type == "thinking":
        console.print(f"[magenta dim]{ev.text}[/]", end="")
    elif ev.type == "text":
        console.print(ev.text, end="", style="cyan")
    elif ev.type == "error":
        console.print(f"\n[red]error:[/] {ev.text}")


async def _run_once(streamer: AgentStreamer, prompt: str, history):
    console.print("[bold]advisor>[/] ", end="")
    async for ev in streamer.stream(prompt, history):
        _render(ev)
        if ev.type == "done":
            console.print()  # newline after streamed answer
    return streamer.last_messages


def _start():
    if not settings.openai_api_key:
        console.print("[red]OPENAI_API_KEY is not set (.env).[/]")
        raise typer.Exit(1)
    console.print("[dim]Loading catalog + programs…[/]")
    repo = JsonRepository(settings.data_dir)
    agent = build_agent()
    streamer = AgentStreamer(agent, Deps(repo=repo, student=DEMO_STUDENT))
    console.print(
        f"[bold green]CMU-Q Advising Assistant[/] "
        f"[dim]({settings.chat_model}, {len(repo.all_courses())} courses, "
        f"{len(repo.list_programs())} programs)[/]"
    )
    return streamer


def _repl():
    streamer = _start()
    console.print("[dim]Ask a question, or 'exit'. Tool calls stream above the answer.[/]\n")
    history = None
    while True:
        try:
            q = console.input("[bold cyan]you> [/]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit", ""}:
            break
        history = asyncio.run(_run_once(streamer, q, history))


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _repl()


@app.command()
def chat(question: str = typer.Argument(..., help="Ask one question and exit.")):
    """One-shot question (streams the working trace)."""
    streamer = _start()
    asyncio.run(_run_once(streamer, question, None))


@app.command()
def docs(query: str = typer.Argument("", help="Optional: test a find query.")):
    """Inspect the handbook/policy/advising document library (no embeddings)."""
    from .retrieval.library import get_library
    lib = get_library(settings.data_dir)
    cat = lib.catalog()
    console.print(f"[green]Library ready:[/] {len(cat)} documents.")
    if query:
        for r in lib.find(query, k=5):
            console.print(f"  [{r['score']}] [cyan]{r['source']}[/]")
    else:
        for c in cat[:40]:
            console.print(f"  [dim]{c['category']}[/]  {c['title']}")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Run the SSE server for a web/Vercel UI."""
    import uvicorn
    uvicorn.run("advisor.server:app", host=host, port=port)


def main():
    app()


if __name__ == "__main__":
    main()
