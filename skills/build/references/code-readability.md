# Code readability

Apply this to new and changed code before implementation and during final review.
Keep the approved behavior and repository conventions. Do not reformat unrelated code.

- Separate top-level functions, types, and declarations with blank lines. Group tightly
  related constants or fields when that matches the language and repository conventions.
- Within a function, put blank lines between meaningful steps: validation, preparation,
  execution, persistence, and cleanup. Keep a cohesive expression or operation together.
  Separate an external write from recording its outcome, even when each is one line.
  Do not separate every `await` when several awaits belong to one cohesive step.
  A formatter passing does not prove that these separators exist.
- Use names that state the value's role and the operation's intent. Avoid abbreviations
  that make the reader trace assignments to understand the code.
- Keep helpers cohesive. Extract a step when a name clarifies a distinct responsibility,
  repeated operation, or complex decision. Do not impose function-length limits or make
  trivial helpers just to shorten a function.
- Make execution order and failure paths visible. Keep guards, side effects, error
  propagation, resource ownership, and awaited cleanup easy to follow. A readability
  refactor must preserve ordering, return values, errors, and cleanup guarantees.
- Comment on a subtle reason, invariant, or constraint when the code alone cannot explain
  it. Do not narrate obvious statements or use comments to excuse unclear structure.
- Use the repository's formatter and language idioms. Do not add spacing that conflicts
  with them or introduce a new style for a small change.

Example: preparation, an external write, its history record, and cleanup remain visible.

```typescript
const session = await openSession();

try {
  const update = await remoteStore.write(session, changes);

  await history.record(update.revision);
} finally {
  await session.close();
}
```

Review the actual source after formatting. Can a reader identify the declarations,
follow each logical step, and see what happens on failure? Fix density in the touched
code without broad refactors. Run the relevant correctness checks too: visual clarity
does not establish semantic preservation.
