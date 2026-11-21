# TypeScript types

## A cast is a lie; a parse is a check

```ts
// claims, unchecked — wrong at runtime, silent
const job = (await res.json()) as TranscodeJob

// checks, throws at the boundary with the offending path
const job = TranscodeJob.parse(await res.json())
```

Every `as` at an I/O boundary is an assertion that the network agrees with your types. `as unknown as T` is the same assertion with the compiler's objection explicitly overruled — it means the types genuinely disagreed and the disagreement was silenced rather than resolved. Treat each one as a bug with a location.

Legitimate `as`: `as const`, narrowing a literal the compiler cannot infer, and `satisfies` cases below. That's it.

## satisfies instead of annotate-or-cast

```ts
// annotation widens: `theme.colors.brand` is string, autocomplete gone
const theme: Record<string, Record<string, string>> = { ... }

// cast lies: no check that the shape matches at all
const theme = { ... } as ThemeConfig

// satisfies checks the shape AND keeps the literal types
const theme = {
  colors: { brand: "#0af", bg: "#111" },
  radius: 8,
} satisfies ThemeConfig
```

`satisfies` is the answer nearly every time someone reaches for a cast on an object literal.

## One zod schema, type derived from it

```ts
export const TranscodeJob = z.object({
  jobId: z.string().uuid(),
  inputUri: z.string().url(),
  target: z.enum(["h264", "hevc", "av1"]),
  bitrateKbps: z.number().int().positive().max(200_000),
})
export type TranscodeJob = z.infer<typeof TranscodeJob>
```

Schema is the single source; the type is derived. A hand-written `interface` next to a schema drifts the first time someone edits one of them, and nothing catches it.

Use `.strict()` on anything from an external producer so a renamed field is an error rather than a silent default. `.safeParse` where you want to branch, `.parse` where throwing to an error boundary is correct.

## Discriminated unions over optional fields

```ts
type Asset =
  | { kind: "image"; width: number; height: number }
  | { kind: "audio"; durationS: number }

function describe(a: Asset): string {
  switch (a.kind) {
    case "image": return `${a.width}x${a.height}`
    case "audio": return `${a.durationS}s`
    default: return assertNever(a)
  }
}

function assertNever(x: never): never {
  throw new Error(`unhandled: ${JSON.stringify(x)}`)
}
```

`assertNever` in the default branch turns "added a variant, forgot a case" into a compile error. Without it, a new variant falls through silently — the single most common cause of a UI rendering nothing.

An interface with six optional fields where only two combinations are legal pushes that knowledge onto every reader. Make illegal states unrepresentable instead.

## Nullability

```ts
// crashes at runtime; the compiler was trying to tell you
const name = user!.profile!.name

// handle it
const name = user?.profile?.name ?? "unknown"

// or narrow once and let control flow do the rest
if (!user?.profile) return null
const name = user.profile.name
```

Every `!` is a deliberate opt-out of the check you turned on `strictNullChecks` to get. Early return narrows for the whole remaining function body, which reads better than chained `?.` everywhere.

Distinguish absent from empty: `?? ` falls back only on `null`/`undefined`, `||` also swallows `0` and `""`. `bitrate || 128` silently rewrites a legitimate `0`.

## unknown, then narrow

```ts
function handle(e: unknown): string {
  if (e instanceof HttpError) return `${e.status}: ${e.message}`
  if (e instanceof Error) return e.message
  return String(e)
}
```

`catch (e: any)` gives up all checking inside the handler — where you are least able to reason and most likely to access a property that doesn't exist. `unknown` forces narrowing, which is the only way to know what you actually have.

## Utility types, not re-declaration

```ts
type JobPatch = Partial<Pick<TranscodeJob, "target" | "bitrateKbps">>
type JobRow = Omit<TranscodeJob, "inputUri"> & { inputKey: string }
```

Derive from the source type so a field rename propagates. A parallel hand-written `JobPatch` is the same drift problem as a hand-written interface beside a schema.

Prefer `type` for unions, intersections, and mapped types; `interface` when you need declaration merging or you are describing an object contract others extend. Do not mix both styles for the same concept in one codebase.

## tsconfig that earns its keep

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,   // arr[0] is T | undefined, because it is
    "exactOptionalPropertyTypes": true, // absent !== undefined
    "noImplicitOverride": true,
    "verbatimModuleSyntax": true
  }
}
```

`noUncheckedIndexedAccess` is the highest-value flag not enabled by `strict` — array and record access genuinely can miss, and the flag makes you say what happens when it does.

`@ts-expect-error` over `@ts-ignore` — it fails when the underlying problem is fixed, so it cleans itself up. Always with a reason on the same line.
