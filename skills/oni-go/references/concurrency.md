# Go concurrency

## errgroup is the default, not a special case

```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(8) // bound it; unbounded fan-out is how you DoS your own database
for _, item := range items {
    item := item // pre-1.22 only; loop vars are per-iteration from 1.22
    g.Go(func() error {
        return process(ctx, item)
    })
}
if err := g.Wait(); err != nil {
    return fmt.Errorf("process batch: %w", err)
}
```

`WithContext` cancels the derived ctx on the first non-nil error, so siblings stop instead of finishing work whose result is already discarded. `SetLimit` is what makes this safe against a 10k-item slice.

Use a bare `go func` only for a goroutine that outlives the request and whose lifetime you own explicitly — a background reaper started in `main` with a shutdown channel. In request-scoped code, never.

## Worker pool when you need backpressure

```go
jobs := make(chan Job)      // unbuffered: the producer blocks until a worker is free
results := make(chan Result, len(items))

g, ctx := errgroup.WithContext(ctx)
for range runtime.NumCPU() {
    g.Go(func() error {
        for j := range jobs {
            r, err := handle(ctx, j)
            if err != nil {
                return err // cancels ctx, unblocks everyone
            }
            select {
            case results <- r:
            case <-ctx.Done():
                return ctx.Err()
            }
        }
        return nil
    })
}
```

Two rules that prevent almost every deadlock here:

1. The goroutine that writes to a channel closes it. Never close from the reader side.
2. Every channel send and receive in a cancellable path is wrapped in a `select` with `<-ctx.Done()`. A send to a channel nobody will read is a permanent leak, and it will not show up in tests that always take the happy path.

## Cancellation actually has to be checked

A `ctx` you accept and never read is decoration. In a loop, check it:

```go
for _, chunk := range chunks {
    if err := ctx.Err(); err != nil {
        return err // caller gave up; stop burning CPU
    }
    ...
}
```

For anything blocking, pass the ctx down rather than polling — `http.NewRequestWithContext`, `db.QueryContext`, `exec.CommandContext`. A `ctx` that isn't threaded into the blocking call cannot interrupt it.

## Timeouts belong at the caller, not the callee

```go
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
```

`defer cancel()` on the line after, always — skipping it leaks the timer until the parent ctx dies. A library function should not invent its own timeout; it should honor the one it was given. The caller knows the deadline budget, the library does not.

## Mutex vs channel

Protecting a field: `sync.Mutex`, embedded next to the data it guards, with a comment naming what it guards. Coordinating ownership handoff between goroutines: channel. Counters: `sync/atomic`. Reaching for a channel to protect a map is how you end up with a goroutine that exists only to own a variable.

Use `sync.RWMutex` only when you have measured read contention. `RLock` is not free and the write path gets slower.

## Leak detection is cheap, add it

```go
func TestMain(m *testing.M) {
    goleak.VerifyTestMain(m)
}
```

`go.uber.org/goleak` fails the test run if a goroutine outlives it. This is the only reliable way to catch the leaks that a `select` without a `ctx.Done()` branch creates, because the symptom in production is memory growth over days, not a test failure.

## Never synchronize with time.Sleep

A `time.Sleep` in a test is a race condition with a delay attached. Synchronize on the actual signal — a channel, a `WaitGroup`, `sync.Cond`, or polling with `require.Eventually`. In production code a sleep in a retry loop needs jitter and a ctx-aware wait:

```go
select {
case <-time.After(backoff):
case <-ctx.Done():
    return ctx.Err()
}
```
