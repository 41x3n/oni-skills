# Python async

## The event loop has one thread

Any synchronous call inside `async def` blocks every other task on that loop — not just the current request. A 200ms `requests.get` in one handler adds 200ms of latency to every concurrent request on that worker.

```python
# blocks the loop
time.sleep(1)
requests.get(url)
conn.execute(sql)
Image.open(p).resize(...)

# does not
await asyncio.sleep(1)
await client.get(url)                       # httpx.AsyncClient
await conn.fetch(sql)                       # asyncpg
await asyncio.to_thread(resize_image, p)    # CPU/blocking work, off-loop
```

`asyncio.to_thread` is the escape hatch for a blocking library you cannot replace. For genuinely CPU-bound work it does not help — the GIL still serializes it; use `ProcessPoolExecutor` via `loop.run_in_executor`.

## One client, reused

```python
class Client:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=3.0),
            limits=httpx.Limits(max_connections=50),
        )

    async def aclose(self) -> None:
        await self._http.aclose()
```

Constructing `AsyncClient` per request throws away the connection pool and pays a TLS handshake every call. Build it once at startup, close it at shutdown (FastAPI: a `lifespan` context manager). A timeout is mandatory — httpx's default is no timeout on some paths, and a hung upstream becomes a hung worker.

## TaskGroup, not gather

```python
async with asyncio.TaskGroup() as tg:
    for item in items:
        tg.create_task(process(item))
```

`TaskGroup` (3.11+) cancels siblings when one task raises and re-raises as an `ExceptionGroup`. `asyncio.gather` without `return_exceptions=True` leaves siblings running after the first failure; with it, errors become return values you have to remember to inspect. Use `gather` only when you want the results positionally and have handled both cases.

Bound the fan-out:

```python
sem = asyncio.Semaphore(10)

async def process(item: Item) -> Result:
    async with sem:
        return await do_work(item)
```

Unbounded `create_task` over a large list opens as many sockets as there are items.

## Never let a task float

```python
# the reference is dropped; the loop may garbage-collect the task mid-flight
asyncio.create_task(background_work())

# keep a reference
self._tasks: set[asyncio.Task[None]] = set()
t = asyncio.create_task(background_work())
self._tasks.add(t)
t.add_done_callback(self._tasks.discard)
```

A task whose only reference is the loop's weak set can be collected before it finishes, and its exception is never raised — the work silently does not happen. If the task is fire-and-forget, it still needs an exception handler, or the failure goes to the loop's default handler and out of your logs.

## Cancellation is an exception, and it must propagate

```python
try:
    await long_running()
except asyncio.CancelledError:
    await cleanup()      # fine
    raise                # mandatory
```

Swallowing `CancelledError` makes a task un-cancellable, so shutdown hangs until the orchestrator kills the process. Never catch it under a bare `except Exception` — in 3.8+ it inherits from `BaseException`, so `except Exception` correctly misses it. That is one more reason not to widen the catch.

Timeouts:

```python
async with asyncio.timeout(5):
    await operation()
```

`asyncio.timeout` (3.11+) over `wait_for` — it composes and gives a clearer traceback.

## Async iteration for streams

```python
async def stream_rows(q: str) -> AsyncIterator[Row]:
    async with pool.acquire() as conn:
        async for rec in conn.cursor(q):
            yield Row.model_validate(dict(rec))
```

Yield per row rather than building a list. A `fetchall` on a large result holds the whole set in memory and delays the first byte until the last row arrives.

## Testing

```python
@pytest.mark.anyio
async def test_handler() -> None:
    async with httpx.AsyncClient(transport=ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/assets/1")
    assert r.status_code == 200
```

`anyio` or `pytest-asyncio` with an explicit mode in config. Test through the ASGI transport rather than calling handlers directly — it exercises dependency injection, serialization, and error middleware, which is where most bugs actually are.

No `time.sleep` and no `asyncio.sleep` as synchronization. Wait on the real signal: an `asyncio.Event`, a queue item, or poll with a deadline.
