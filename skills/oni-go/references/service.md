# Go services and workers

## Shape

```
cmd/worker/main.go       flag parsing, config, wiring, shutdown. Nothing else.
internal/transcode/      one domain per package, named for the domain
internal/transcode/store.go   interface + the one real impl
```

Package name is the domain (`transcode`, `epg`, `publish`), never `utils`, `helpers`, `common`, or `models`. A package named for a layer attracts unrelated code until it depends on everything and nothing can be tested in isolation.

Exported surface is the smallest thing that works. `internal/` by default; promote out of it only when a second module actually imports it.

## Constructor takes dependencies, returns a struct

```go
type Service struct {
    store  Store
    bucket Bucket
    log    *slog.Logger
}

func New(store Store, bucket Bucket, log *slog.Logger) *Service {
    return &Service{store: store, bucket: bucket, log: log}
}
```

No package-level state, no `init()` that touches the network, no singletons. Dependencies as interfaces owned by *this* package — the consumer defines the interface it needs, not the provider. That is what makes a two-method fake possible instead of mocking someone else's 30-method client.

Never store a `ctx` in the struct. Request-scoped lifetime in a process-scoped object is a bug waiting for the second request.

## Interfaces at the consumer, one or two methods

```go
// in the package that uses it
type Bucket interface {
    Put(ctx context.Context, key string, r io.Reader) error
}
```

Do not define an interface until there are two implementations or a test needs a fake. A one-implementation interface written "for flexibility" is indirection with no payoff, and it hides the real signature behind a second name.

## Graceful shutdown

```go
func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    srv := &http.Server{Addr: ":8080", Handler: h}

    g, gctx := errgroup.WithContext(ctx)
    g.Go(func() error {
        if err := srv.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
            return err
        }
        return nil
    })
    g.Go(func() error {
        <-gctx.Done()
        sctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
        defer cancel()
        return srv.Shutdown(sctx) // fresh ctx: gctx is already cancelled
    })
    if err := g.Wait(); err != nil {
        slog.Error("exit", "err", err)
        os.Exit(1)
    }
}
```

The shutdown ctx must be fresh. Deriving it from the cancelled one makes `Shutdown` return instantly and drops in-flight requests — the exact thing it exists to prevent. Keep the drain timeout under your orchestrator's kill grace period.

## Structured logging

```go
log := slog.With("worker", "transcode", "job_id", job.ID)
log.InfoContext(ctx, "started", "input_bytes", n)
```

Key-value pairs, never `fmt.Sprintf` into the message. Attach the stable fields once with `With` and pass that logger down. One log line per state change — start, finish, fail — not per loop iteration; a per-item log in a 10k-item batch costs more than the work.

Log levels that mean something: `Error` is "a human must look at this", `Warn` is "degraded but handled", `Info` is state changes, `Debug` is off in production.

## Tests: table-driven, real behavior

```go
func TestNormalize(t *testing.T) {
    tests := map[string]struct {
        in      string
        want    string
        wantErr error
    }{
        "strips whitespace": {in: "  a ", want: "a"},
        "rejects empty":     {in: "", wantErr: ErrEmpty},
    }
    for name, tc := range tests {
        t.Run(name, func(t *testing.T) {
            got, err := Normalize(tc.in)
            if !errors.Is(err, tc.wantErr) {
                t.Fatalf("err = %v, want %v", err, tc.wantErr)
            }
            if got != tc.want {
                t.Errorf("got %q, want %q", got, tc.want)
            }
        })
    }
}
```

Map keys as test names, so the name *is* the assertion in the failure output. `errors.Is` for error comparison, never string equality. `t.Fatalf` when continuing would panic, `t.Errorf` when you want the rest of the checks to run too.

`t.Cleanup` over `defer` in helpers — it runs in the right order relative to subtests. `t.Parallel()` on anything that does not share mutable state, and `-race` always in CI.

Fake at the interface you defined, not at the HTTP layer, and not with a mock framework. A struct with function fields is enough:

```go
type fakeBucket struct {
    put func(context.Context, string, io.Reader) error
}

func (f fakeBucket) Put(ctx context.Context, k string, r io.Reader) error {
    return f.put(ctx, k, r)
}
```

## Before optimizing

`go test -bench . -benchmem`, then `-cpuprofile`. The answer is almost always an allocation in a loop or an N+1 query, not the thing you guessed. `sync.Pool`, `strings.Builder`, and preallocated slice capacity are the three fixes that pay off; everything else needs a profile first.
