#!/usr/bin/env python3
"""Measure context consumption from Claude Code and Codex transcripts.

Answers the question the pack is built on: what share of cost is main-thread
context residency? If main-thread share falls well below ~90%, the
delegation-first premise needs rechecking.

    python3 scripts/measure.py
    python3 scripts/measure.py --days 7
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# input $/MTok, output $/MTok. Cache read is 0.1x input, cache write 1.25x.
PRICES = {
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5-1": (10.0, 50.0),
}


@dataclass(frozen=True)
class CodexSession:
    session_id: str
    path: Path
    duration_seconds: float
    turns: int
    compactions: int
    subagent_tasks: int
    total_tokens: int


def _timestamp(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def scan_codex(root: Path, cutoff: float) -> list[CodexSession]:
    """Read root Codex sessions; child agents are represented by their parent's task count."""
    sessions: list[CodexSession] = []
    if not root.exists():
        return sessions

    for path in root.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue

        session_id: str | None = None
        parent: object = None
        saw_meta = False
        first: float | None = None
        last: float | None = None
        turns = compactions = subagent_tasks = total_tokens = 0
        try:
            with path.open(errors="ignore") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    ts = _timestamp(rec.get("timestamp"))
                    if ts is not None:
                        first = ts if first is None else min(first, ts)
                        last = ts if last is None else max(last, ts)
                    kind = rec.get("type")
                    payload = rec.get("payload") or {}
                    if kind == "session_meta":
                        saw_meta = True
                        session_id = payload.get("id")
                        parent = payload.get("parent_thread_id")
                    elif kind == "turn_context":
                        turns += 1
                    elif kind == "compacted":
                        compactions += 1
                    elif kind == "event_msg" and payload.get("type") == "task_started":
                        subagent_tasks += 1
                    elif kind == "token_usage_record":
                        usage = payload.get("thread_token_usage") or {}
                        total_tokens = max(total_tokens, usage.get("total_tokens") or 0)
        except OSError:
            continue

        if saw_meta and parent is None and session_id and first is not None and last is not None:
            sessions.append(
                CodexSession(
                    session_id=session_id,
                    path=path,
                    duration_seconds=max(0, last - first),
                    turns=turns,
                    compactions=compactions,
                    subagent_tasks=subagent_tasks,
                    total_tokens=total_tokens,
                )
            )
    return sorted(sessions, key=lambda session: session.duration_seconds, reverse=True)


def print_codex(sessions: list[CodexSession]) -> None:
    print(f"\nCodex root sessions: {len(sessions)}")
    print(f"{'span_h':>7} {'turns':>6} {'compact':>7} {'agents':>6} {'tokens':>10}  session")
    for session in sessions[:5]:
        print(
            f"{session.duration_seconds / 3600:7.1f} {session.turns:6d} "
            f"{session.compactions:7d} {session.subagent_tasks:6d} "
            f"{session.total_tokens / 1e6:9.1f}M  {session.session_id}"
        )
    review = [
        session
        for session in sessions
        if session.duration_seconds >= 4 * 3600
        or session.compactions >= 2
        or session.total_tokens >= 20_000_000
    ]
    print(f"session-slicing review signals: {len(review)}")
    print("  span_h includes idle time and later resumes; compactions and tokens are stronger signals.")
    if review:
        print("  Review these sessions for mixed deliverables or slices that should restart fresh.")


def price_for(model: str) -> tuple[float, float] | None:
    for key, p in PRICES.items():
        if model.startswith(key):
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", type=Path, default=Path.home() / ".claude" / "projects")
    ap.add_argument("--codex-sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    ap.add_argument("--days", type=int, default=28)
    args = ap.parse_args()

    root = args.projects.expanduser()
    cutoff = time.time() - args.days * 86400
    # (model, main|sub) -> [cache_read, cache_write, input, output, calls]
    agg: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0, 0, 0, 0, 0])
    files = 0

    for path in root.rglob("*.jsonl") if root.exists() else []:
        try:
            if path.stat().st_mtime < cutoff:
                continue
        except OSError:
            continue
        files += 1
        try:
            with path.open(errors="ignore") as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    msg = rec.get("message")
                    if not isinstance(msg, dict):
                        continue
                    usage = msg.get("usage")
                    model = msg.get("model")
                    if not isinstance(usage, dict) or not model:
                        continue
                    slot = agg[(model, "sub" if rec.get("isSidechain") else "main")]
                    slot[0] += usage.get("cache_read_input_tokens") or 0
                    slot[1] += usage.get("cache_creation_input_tokens") or 0
                    slot[2] += usage.get("input_tokens") or 0
                    slot[3] += usage.get("output_tokens") or 0
                    slot[4] += 1
        except OSError:
            continue

    codex_sessions = scan_codex(args.codex_sessions.expanduser(), cutoff)
    if not agg and not codex_sessions:
        print(f"no Claude usage under {root} and no Codex sessions under {args.codex_sessions}")
        return 1

    rows = []
    total_cost = 0.0
    total_ctx = 0.0
    total_calls = 0
    for (model, where), (cr, cw, inp, out, calls) in agg.items():
        p = price_for(model)
        cost = (
            cr / 1e6 * p[0] * 0.1 + cw / 1e6 * p[0] * 1.25 + inp / 1e6 * p[0] + out / 1e6 * p[1]
            if p
            else 0.0
        )
        rows.append((cost, model, where, cr, cw, out, calls, p is not None))
        total_cost += cost
        total_ctx += cr + cw + inp
        total_calls += calls

    if rows:
        rows.sort(reverse=True)
        print(f"{files} Claude transcripts, last {args.days} days, {total_calls} API calls\n")
        print(f"{'cost$':>9} {'share':>6}  {'model':26s} {'where':5s} {'cacheRd':>9} {'out':>7} {'calls':>6}")
        for cost, model, where, cr, _cw, out, calls, priced in rows:
            share = f"{cost / total_cost * 100:5.1f}%" if total_cost else "    -"
            flag = "" if priced else "  (unpriced)"
            print(f"{cost:9.0f} {share:>6}  {model:26s} {where:5s} {cr/1e6:8.0f}M {out/1e6:6.1f}M {calls:6d}{flag}")

        main_cost = sum(r[0] for r in rows if r[2] == "main")
        print(f"\ntotal              ${total_cost:,.0f}   (API-rate equivalent, not a bill)")
        print(f"avg context/call    {total_ctx / max(total_calls, 1) / 1000:,.0f}K tokens")
        if total_cost:
            share = main_cost / total_cost * 100
            print(f"main-thread share   {share:.1f}%")
            if share < 75:
                print("\n  Main-thread share is well below the ~91% the pack was designed against.")
                print("  Delegation is working, or the workload changed. Re-check the premise.")
            else:
                print("\n  Delegation-first premise holds: main-thread residency still dominates.")
    if codex_sessions:
        print_codex(codex_sessions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
