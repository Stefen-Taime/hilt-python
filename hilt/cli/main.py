import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from hilt.__version__ import __version__
from hilt.core.actor import Actor
from hilt.core.event import Content, Event
from hilt.instrumentation.auto import instrument, uninstrument
from hilt.instrumentation.context import get_context


def _demo_event() -> int:
    """Write a small demo event to the active HILT backend."""
    session = get_context().session
    if not session:
        print("❌ No active HILT session.")
        return 1

    evt = Event(
        session_id="cli_demo",
        actor=Actor(type="human", id="cli-user"),
        action="prompt",
        content=Content(text="Hello from `hilt demo` 👋"),
        extensions={"model": "cli-demo"},
    )
    session.append(evt)
    print("✅ Demo event written.")
    return 0


def _tail_file(path: Path, n: int) -> int:
    if not path.exists():
        print(f"❌ File not found: {path}")
        return 1
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()[-n:]
    for line in lines:
        try:
            print(json.loads(line))
        except Exception:
            print(line.rstrip())
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    # Start a session (local by default)
    if args.backend == "local":
        instrument(backend="local", filepath=args.file, providers=["openai"])
        print(f"📝 Local log: {args.file}")
    else:
        if not args.sheet_id:
            print("❌ --sheet-id is required for backend='sheets'")
            return 1
        instrument(
            backend="sheets",
            sheet_id=args.sheet_id,
            credentials_path=args.credentials,
            worksheet_name=args.worksheet,
            providers=["openai"],
        )
        print(f"📝 Google Sheets: {args.sheet_id} tab '{args.worksheet}'")

    try:
        return _demo_event()
    finally:
        uninstrument()


def cmd_tail(args: argparse.Namespace) -> int:
    return _tail_file(Path(args.file), args.n)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hilt", description="HILT CLI")
    sub = parser.add_subparsers(dest="cmd")

    # hilt version
    p_version = sub.add_parser("version", help="Print version")
    p_version.set_defaults(func=cmd_version)

    # hilt demo
    p_demo = sub.add_parser("demo", help="Write a demo event via HILT")
    p_demo.add_argument("--backend", choices=["local", "sheets"], default="local")
    p_demo.add_argument(
        "--file", default="logs/cli_demo.jsonl", help="Path to log file (local backend)"
    )
    p_demo.add_argument("--sheet-id", help="Google Sheet ID (sheets backend)")
    p_demo.add_argument("--worksheet", default="Logs", help="Sheet tab name (sheets)")
    p_demo.add_argument("--credentials", help="Path to credentials.json (sheets)")
    p_demo.set_defaults(func=cmd_demo)

    # hilt tail
    p_tail = sub.add_parser("tail", help="Show the last N lines of a local log")
    p_tail.add_argument("file")
    p_tail.add_argument("-n", type=int, default=20)
    p_tail.set_defaults(func=cmd_tail)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    handler = cast(Callable[[argparse.Namespace], int], func)
    return handler(args)
