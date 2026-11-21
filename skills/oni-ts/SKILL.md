---
name: oni-ts
description: Use when writing or reviewing TypeScript. Rules derived from failure modes measured across production TypeScript services and frontends.
---

# oni-ts

Counts come from 1561 TypeScript files in the author's production code: evidence, not generic advice. Your codebase may differ.

## Hard rules

1. **`as unknown as T` is a bug.** 117 sites. It means the types genuinely disagree and the disagreement was silenced. Parse with zod at the boundary — already used at 760 sites — or fix the type.
2. **Parse, don't cast.** 598 real `as Type` casts (`as const` at 311 is fine). A cast is a claim the compiler cannot check; `schema.parse()` is the same claim, checked at runtime.
3. **No `: any`.** 141 sites. `unknown` is already used at 486 sites — use it, then narrow. `any` disables checking for everything it touches.
4. **No `!.` non-null assertion.** 58 sites. Handle the null branch, or use `?.` with a real default. Every `!` is a runtime crash the compiler was trying to prevent.
5. **Never float a promise.** 6 unawaited `.then` chains. `await` it, or `void` it explicitly with a comment. A floated promise loses its rejection.

## Minor

- 37 loose `==`. Use `===` unless comparing to null deliberately.
- 72 `console.log`. Use the project logger outside scripts.
- 1 `@ts-expect-error`. Keep it at 1 or 0, always with a stated reason.

## Already good, keep it

zod at 760 sites, `unknown` at 486, optional chaining at 1247. That is the right spine — the casts are where it gets bypassed.

## Review order

Boundary parsing, then nullability, then promise handling. A bad cast at an API boundary corrupts everything downstream of it.

## Depth, on demand

Read the one that matches what you are doing. Do not read all three.

| File | Covers |
|---|---|
| `references/types.md` | cast vs parse, `satisfies`, one zod schema as source of truth, discriminated unions with `assertNever`, nullability and `??` vs `||`, `unknown` narrowing, utility types, the tsconfig flags `strict` misses |
| `references/async.md` | floating promises, `all` vs `allSettled` vs bounded pool, why `forEach` with async is always wrong, `AbortController` and timeouts, `fetch` not throwing on 4xx, `{ cause }`, retry classification, Node stream and sync-call rules |
| `references/boundaries.md` | the three-layer shape, parse in / validate out, one error mapping point, adapters returning domain types, module boundaries and cycles, config parsed at startup, React boundary rules |
