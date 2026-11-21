---
name: debug
description: Use on any bug, test failure, crash, or unexpected behavior, before proposing a fix. Root cause before edit, no symptom patching.
---

# debug

## Gate

No fix proposed until the root cause is named and its mechanism explained. A symptom fix hides the bug and buys the same debugging session a second time.

## 1. Read the actual error

Quote the shortest decisive line: file, line, expected vs actual. Not the whole log. If you have not read the real error text, you are guessing.

## 2. Reproduce

One command that fails reliably. Write it down. If you cannot reproduce it, that is the first bug to solve.

## 3. One hypothesis at a time

State it as a prediction: "if X is the cause, Y will be true." Test the prediction, not the fix. A hypothesis that cannot be wrong is not a hypothesis.

## 4. Trace to the origin

Follow the bad value back to where it was created, not where it exploded. Delegate evidence gathering using `build`'s search tier — it is a `file:line` question. Diagnose the root cause on the parent.

## 5. Name it, then fix it

One sentence: what is wrong, and why it produced this symptom. Then fix. Then the failing case becomes a test.

## Stuck after three attempts

Stop editing. Name the assumption you have not questioned. Ask one diagnostic question. Three failed fixes means your model of the system is wrong, and more edits make it worse.

## Refuse

- Fixing before reproducing.
- Changing two things at once.
- "Let me add logging and see" before the existing error text has been read.
