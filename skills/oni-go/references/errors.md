# Go errors

## Wrap with context that the caller does not already have

```go
if err := db.QueryRowContext(ctx, q, id).Scan(&x); err != nil {
    return fmt.Errorf("load asset %s: %w", id, err)
}
```

The message adds the identifier and the operation. It does not add the word "error", the function name, or "failed to" — the caller's own wrap supplies the call path, and `errors.Is` supplies the class. A chain reading `process: load asset abc123: sql: no rows in result set` tells you everything; `error: failed to process: error querying: sql: no rows` tells you the same thing three times.

`%w` always. `%v` severs the chain and every `errors.Is` above you starts silently returning false.

Wrap more than one error with `errors.Join(err1, err2)` — both stay matchable by `errors.Is`.

## Sentinel for "which case", typed for "with what data"

```go
var ErrNotFound = errors.New("not found")

// caller
if errors.Is(err, ErrNotFound) {
    return status.Error(codes.NotFound, "asset")
}
```

```go
type ValidationError struct {
    Field  string
    Reason string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("field %s: %s", e.Field, e.Reason)
}

// caller
var ve *ValidationError
if errors.As(err, &ve) {
    return badRequest(ve.Field)
}
```

Never compare error strings. `strings.Contains(err.Error(), "not found")` breaks the first time a dependency rewords a message, and it breaks at runtime, in production, silently.

## Classify for retry at the boundary, once

```go
func retryable(err error) bool {
    if errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
        return false // the caller gave up; retrying is wasted work
    }
    var terr interface{ Temporary() bool }
    if errors.As(err, &terr) {
        return terr.Temporary()
    }
    var se *googleapi.Error
    if errors.As(err, &se) {
        return se.Code == 429 || se.Code >= 500
    }
    return false
}
```

The default is "not retryable". Retrying a 400 forever is worse than failing once — it turns a bad request into an outage, and the logs fill with the same error while the real cause scrolls away.

## Panic is for programmer error only

Nil map write, impossible switch branch, a `MustCompile` at package init. Anything that depends on input, network, or disk returns an error. A panic in a request handler takes down every in-flight request on that goroutine's process unless something recovered it, and the recovery is itself a place bugs hide.

If you do recover — at the top of a worker loop, so one bad job doesn't kill the pool — log the stack and convert to an error:

```go
defer func() {
    if r := recover(); r != nil {
        err = fmt.Errorf("panic: %v\n%s", r, debug.Stack())
    }
}()
```

Named return required, or the converted error is discarded.

## Ignoring an error needs a reason on the line

```go
_ = resp.Body.Close() // best effort; response already fully read
```

Not `_ = doSomething()` with no comment. Six months later nobody can tell whether the error was impossible or whether someone was in a hurry. For `defer f.Close()` on a file you wrote to, the error is *not* ignorable — an unflushed buffer means data loss:

```go
defer func() {
    if cerr := f.Close(); cerr != nil && err == nil {
        err = fmt.Errorf("close %s: %w", path, cerr)
    }
}()
```

## Log at the top, return everywhere else

One error, one log line. Log where you handle it — usually the request boundary or the worker loop — and return it everywhere below. Logging and returning the same error means the same failure appears four times at four stack depths, and the volume makes the real signal unfindable.

```go
if err := h.process(ctx, job); err != nil {
    slog.ErrorContext(ctx, "job failed", "job_id", job.ID, "err", err)
    continue
}
```

`slog.ErrorContext` over `slog.Error` — it picks up trace IDs from the ctx. Pass the error as a value under an `err` key, not interpolated into the message, or you lose the ability to group by message.
