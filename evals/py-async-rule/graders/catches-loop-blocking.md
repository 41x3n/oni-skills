---
type: llm
name: catches-loop-blocking
---

The snippet has two blocking calls inside `async def`. The review must identify the event-loop problem as the headline, not bury it in a list of style notes.

Score 1.0 if the response:

- names `requests.get` as a synchronous call that blocks the event loop, and recommends `httpx.AsyncClient` (or an equivalent async client)
- names `time.sleep` as blocking, and recommends `await asyncio.sleep`
- makes clear the consequence is loop-wide — every concurrent request is stalled, not just this task

Score 0.5 if it catches both calls but frames the impact as "this function is slow" rather than as blocking the loop for everything.

Score 0.0 if it misses either blocking call, or if its top finding is something else — naming, type hints, the mutable accumulator, list comprehensions.

Bonus observations that do not change the score: suggesting `asyncio.gather` or a `TaskGroup` for concurrency, bounding fan-out with a semaphore, or reusing one client instead of a per-call one. These are correct and welcome, but the two blocking calls are the pass condition.
