# TypeScript async

## Every promise is awaited, voided, or returned

```ts
// rejection becomes an unhandled rejection; in Node 15+ that exits the process
doWork()

// handled
await doWork()
return doWork()
void doWork().catch((e) => log.error({ err: e }, "background work failed"))
```

A floated promise loses both its result and its rejection. Turn this on so the compiler finds them: `@typescript-eslint/no-floating-promises`. It is the single highest-value lint rule in a Node codebase.

`void` is the explicit "fire and forget" marker — and it still needs a `.catch`, because voiding the promise does not void the rejection.

## Concurrency: all, allSettled, or a bounded pool

```ts
// fails fast; the other requests keep running but their results are discarded
const [a, b] = await Promise.all([fetchA(), fetchB()])

// every outcome, no short-circuit
const results = await Promise.allSettled(items.map(process))
const failed = results.filter((r) => r.status === "rejected")
```

`Promise.all` over a 10k-item array opens 10k sockets. Bound it:

```ts
async function mapLimit<T, R>(
  items: readonly T[],
  limit: number,
  fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const out: R[] = new Array(items.length)
  let next = 0
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (next < items.length) {
        const i = next++
        out[i] = await fn(items[i]!)
      }
    }),
  )
  return out
}
```

`p-limit` if you would rather not own it. Either way the limit is explicit, not accidental.

## Sequential in a loop is sometimes correct

```ts
// serial: each iteration waits. Right when order matters or the target rate-limits.
for (const item of items) {
  await process(item)
}

// parallel
await Promise.all(items.map(process))
```

`forEach` with an async callback is neither — it returns before any of the work finishes, and every promise floats. Never use it with async.

## Timeouts and cancellation

```ts
const ac = new AbortController()
const timer = setTimeout(() => ac.abort(), 5_000)
try {
  const res = await fetch(url, { signal: ac.signal })
  if (!res.ok) {
    throw new HttpError(res.status, "upstream request failed")
  }
  return Schema.parse(await res.json())
} finally {
  clearTimeout(timer)
}
```

`fetch` has no default timeout — without a signal, a hung upstream hangs your handler until the platform kills it. `clearTimeout` in `finally` or you leak a timer per call and keep the event loop alive.

An upstream response body can contain secrets. Do not read it into an error. The response mapper logs only the numeric upstream status and returns a fixed public failure.

Thread the caller's signal through rather than creating a new controller in a library function; combine with `AbortSignal.any([a, b])` when you need both a caller signal and a local deadline.

## fetch does not throw on 4xx/5xx

`res.ok` must be checked explicitly. A `fetch` wrapped in `try/catch` with no `res.ok` check treats a 500 as success and hands the error page to `JSON.parse`, producing a parse error that names the wrong cause.

## Errors keep their cause

```ts
class HttpError extends Error {
  constructor(readonly status: number, message: string, options?: ErrorOptions) {
    super(message, options)
    this.name = "HttpError"
  }
}

try {
  await upload(file)
} catch (e) {
  throw new UploadFailed(`upload ${file.name}`, { cause: e })
}
```

`{ cause: e }` preserves the chain — Node prints it and structured loggers serialize it. Rethrowing a new error without `cause` discards the only information that identifies the real failure. Set `name` explicitly; subclass names are lost through some bundlers' minification.

## Retry only what is retryable

```ts
const retryable = (e: unknown) =>
  e instanceof HttpError ? e.status === 429 || e.status >= 500 : e instanceof TypeError // network

for (let attempt = 0; ; attempt++) {
  try {
    return await call()
  } catch (e) {
    if (attempt >= 3 || !retryable(e)) throw e
    await sleep(2 ** attempt * 100 + Math.random() * 100) // jitter, or all clients retry in lockstep
  }
}
```

Never retry a 400 or a validation failure; the second attempt fails identically and you have turned one error into four. Respect `Retry-After` when present.

## Node specifics

`node:` prefix on builtin imports (`node:fs/promises`) — explicit and unshadowable. `fs/promises` over callbacks over `fs.readFileSync` in any request path; a sync read blocks the event loop exactly like a blocking call in Python's loop.

Streams for anything large: `await pipeline(src, transform, dest)` from `node:stream/promises`, which propagates errors and cleans up. Manual `.pipe()` chains leak the source on a destination error.

## Testing async

```ts
await expect(upload(bad)).rejects.toThrow(HttpError)
```

`await` the assertion. `expect(p).rejects` without `await` passes vacuously whatever the promise does — a silently useless test.

Fake timers for backoff logic so a retry test runs in milliseconds; never a real `sleep` in a test. No arbitrary `setTimeout` as synchronization — wait on the condition.
