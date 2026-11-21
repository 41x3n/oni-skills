---
name: oni-go
description: Use when writing or reviewing Go. Rules derived from failure modes measured across production Go services.
---

# oni-go

Counts come from 210 Go files in the author's production code: evidence, not generic advice. Your codebase may differ.

## Hard rules

1. **`errgroup`, never bare `go func(`.** 15 bare goroutines against 7 `errgroup`/`WaitGroup`. A bare `go func` cannot return an error and cannot be cancelled — each one is a leak waiting on a slow dependency. Use `errgroup.WithContext`.
2. **Never `_ = someCall()`.** 31 ignored errors. Handle it, or write `//nolint` with the reason. A silently ignored error is a production incident with no log line.
3. **Wrap with `%w`, never `%v`.** 23 sites use `%v`; 261 correctly use `%w`. `%v` severs the chain, so every downstream `errors.Is` / `errors.As` silently stops matching.
4. **`ctx context.Context` is the first parameter of anything doing IO.** 304 functions do this; 24 source-file functions do IO without it. No ctx means no timeout and no cancellation.
5. **Name the type instead of `any`.** 251 uses of bare `any`. At a trust boundary use a concrete struct; inside, use a type parameter.

## Already good, keep it

- `slog` at 139 sites against 8 stdlib `log`. Never add `log.Printf`.
- `defer x.Close()` at 157 sites. Keep pairing acquire with defer on the next line.
- `context.Background()` appears only 5 times in library code. Keep it confined to `main` and tests.

## Review order

Errors, then goroutine lifetime, then ctx propagation, then types. A leaked goroutine outranks an ugly signature.

## Depth, on demand

Read the one that matches what you are doing. Do not read all three.

| File | Covers |
|---|---|
| `references/concurrency.md` | errgroup, worker pools with backpressure, cancellation, timeouts, mutex vs channel, leak detection, why never `time.Sleep` |
| `references/errors.md` | wrap messages that add information, sentinel vs typed errors, retry classification, when panic is correct, recover in a worker loop, log-at-the-top |
| `references/service.md` | package layout, constructor injection, consumer-side interfaces, graceful shutdown, slog patterns, table-driven tests, hand-written fakes |
