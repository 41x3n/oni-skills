---
name: oni-py
description: Use when writing or reviewing Python. Rules derived from failure modes measured across production Python services and agents.
---

# oni-py

Counts come from 1488 Python files in the author's production code: evidence, not generic advice. Your codebase may differ.

## Hard rules

1. **No blocking call inside `async def`.** 37 `time.sleep` against 470 `async def`. Use `await asyncio.sleep`, and `httpx.AsyncClient` rather than `requests` (3 sites). One blocking call stalls the whole event loop, not just its own task.
2. **`except Exception` needs a re-raise or a named reason.** 368 broad catches, 25 of them `except: pass`. A silent swallow converts a crash into corrupt state that surfaces much later. Catch the specific error, or log and re-raise.
3. **Pydantic model, not `dict[str, Any]`.** 353 `dict[str, Any]` while `BaseModel` is already used at 956 sites. An untyped dict moves the failure from the boundary to somewhere deep and much later.
4. **Type the parameters.** 1542 non-test functions have at least one untyped parameter. Annotate params and return on anything crossing a module boundary.
5. **`logger`, never `print`.** 425 `print()` in source, 0 in tests. Use the module logger — `print` in a worker is invisible in production.

## Already good, keep it

- `BaseModel` at 956 sites. Parse at the edge, pass models inward.
- `httpx` / `aiohttp` at 39 sites against 3 `requests`. Keep the async client.

## Review order

Event-loop blocking, then swallowed exceptions, then boundary types. A blocked loop takes down every request; a missing annotation takes down none.

## Depth, on demand

Read the one that matches what you are doing. Do not read all three.

| File | Covers |
|---|---|
| `references/async.md` | what blocks the loop and what doesn't, client reuse and timeouts, `TaskGroup` over `gather`, semaphores, why a floating task gets garbage-collected, cancellation must re-raise, async testing |
| `references/typing-pydantic.md` | parse at the edge, `extra="forbid"` and `frozen`, validator modes, discriminated unions with `match`, `BaseSettings`, `model_dump(mode="json")`, `TypeAdapter` placement, strict mypy |
| `references/errors-testing.md` | package exception hierarchy, the three broad-catch outages, `raise from`, structured logging, asserting on error shape not message, fixture scope, hand-written fakes over `MagicMock` |
