# TypeScript boundaries

A boundary is anywhere data crosses from something you do not control into something you do: HTTP handler, queue consumer, config load, LLM response, `localStorage`, URL params, a third-party SDK's return value. Types are guesses until a boundary checks them.

## The three-layer shape

```
route/handler   parse input -> call service -> map result to response
service         domain logic on validated types only. No Request, no Response.
adapter         db, bucket, http client. Returns domain types, not rows.
```

A service that takes a `Request` cannot be tested without constructing one, and it cannot be reused from a queue consumer. Parse at the edge and the inner layers never see `unknown`.

## Request in, response out

```ts
const Body = z.object({ target: z.enum(["h264", "hevc"]), bitrateKbps: z.number().int().positive() })

app.post("/jobs", async (req, res) => {
  const parsed = Body.safeParse(req.body)
  if (!parsed.success) {
    return res.status(400).json({ error: "invalid_body", issues: parsed.error.issues })
  }
  const job = await service.create(parsed.data)   // typed from here down
  return res.status(201).json(JobResponse.parse(job))
})
```

Parse the response too when the client is a separate team's code — it catches the day someone adds a field holding a `Date` that serializes differently than the contract says.

## One error shape, one mapping point

```ts
type ApiError = { error: string; message: string; issues?: unknown }

function toResponse(e: unknown): { status: number; body: ApiError } {
  if (e instanceof z.ZodError) return { status: 400, body: { error: "invalid", message: "bad request", issues: e.issues } }
  if (e instanceof NotFoundError) return { status: 404, body: { error: "not_found", message: e.message } }
  if (e instanceof HttpError) {
    log.error({ upstreamStatus: e.status }, "upstream request failed")
    return { status: 502, body: { error: "upstream", message: "upstream request failed" } }
  }
  log.error({ err: e }, "unhandled")
  return { status: 500, body: { error: "internal", message: "internal error" } }
}
```

One function, used by the error middleware. Per-route `try/catch` blocks that each invent a status code produce an API where the same failure returns 400, 422, and 500 depending on which endpoint you hit.

Never leak an internal message on a 500 — stack traces and SQL in a response body are an information leak. Log the detail, return the generic.

An `HttpError` may carry an upstream response body in its message or cause. Return a fixed 502 and public message, and log only its numeric status.

## Adapters return domain types

```ts
// leaks the schema: every caller now depends on column names
async function getJob(id: string): Promise<JobRow>

// owns the mapping in one place
async function getJob(id: string): Promise<Job | null> {
  const row = await db.selectFrom("jobs").where("id", "=", id).executeTakeFirst()
  return row ? { id: row.id, target: row.target, bitrateKbps: row.bitrate_kbps } : null
}
```

`snake_case` stops at the adapter. A rename in the database then touches one function instead of forty call sites.

Return `null` for "not found" when the caller decides what it means; throw when absence is always an error. Pick one per function and document it in the signature — `Promise<Job | null>` already does.

## Module boundaries

Every directory exports through one `index.ts`. Importing `../services/transcode/internal/probe` from a route means the internals are public and cannot be changed. If a deep import is needed, the thing it reaches for belongs in the public surface.

No cycles. If A imports B and B imports A, the shared piece is a third module — usually the types. `import type { Job } from "./types"` costs nothing at runtime with `verbatimModuleSyntax`.

## Config once, at startup

```ts
const Env = z.object({
  DATABASE_URL: z.string().url(),
  BUCKET: z.string().min(1),
  MAX_WORKERS: z.coerce.number().int().positive().default(8),
})

export const env = Env.parse(process.env)  // throws at import, not mid-request
```

`process.env.X!` scattered through modules fails on the first code path that needs it, often minutes into a job, with a message that says `undefined` and nothing about which variable.

## React boundaries, briefly

Server data is parsed where it arrives, not in the component. A component receiving `unknown` and casting it puts a validation failure inside a render, where the error boundary shows a blank screen instead of a message.

Derive instead of syncing — a `useEffect` whose only job is to set state from props is a boundary violation that causes a double render and a stale frame. Compute it during render, or `useMemo` it if the cost is real.

Props typed as a discriminated union match the `assertNever` pattern in `types.md`: one component, explicit variants, no "if `mode` is `edit` then `onSave` is required" left as a comment.
