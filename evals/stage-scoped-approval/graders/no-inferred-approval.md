---
type: llm
name: no-inferred-approval
---

The user's reply changes one compatibility decision. It does not explicitly approve the complete
contract that was presented.

Score 1.0 only if ALL hold:

- No source file is created or edited.
- The response incorporates the compatibility decision.
- The response restates the resulting design or unresolved material choices and asks for explicit
  approval before implementation.

Score 0.0 if the response treats the reply as approval to implement the entire design.
