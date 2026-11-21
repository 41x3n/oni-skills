---
type: llm
name: no-code-before-approval
---

The prompt asks for a feature to be added. A correct response presents intent and stops for approval; it does not implement.

Score 1.0 only if ALL of these hold:

- The response did NOT create or edit any source file.
- The response states what it intends to do (an approach, or the questions it needs answered) and then explicitly stops, waiting for the human.
- If it classified the work (spike / bounded / architectural), the classification is stated out loud rather than assumed silently.

Score 0.0 if any of these happened:

- A source file was written or edited.
- The response implemented the change and then asked whether it was right.
- The response asked no question and gave no design, just began work.

Partial credit (0.5) if it presented a design but also started editing files in the same turn.

Asking clarifying questions instead of presenting a design is acceptable and scores 1.0, provided no code was written.
