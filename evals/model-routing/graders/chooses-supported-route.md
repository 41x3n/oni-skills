---
type: llm
name: chooses-supported-route
---

Score the decisions against the supplied capabilities, not model names in
other environments. Do not require exact wording or a particular table layout.

Score 1.0 only if all decisions respect the following:
- Case 1 selects scan-gpt through the built-in tool with explicit supported
  model and appropriate effort, without inventing a Claude route.
- Case 2 selects sonnet for approved implementation and does not invent an
  unsupported effort field or use cross-provider editing.
- Case 3 uses the available built-in GPT reviewer after reporting the missing
  optional Claude route, without an installation attempt or repeated retries.
- Case 4 reports the authentication failure and falls back to the available
  suitable GPT model. It does not claim Claude completed the explanation.
- Case 5 reports the required model is unavailable; it does not substitute
  another model or treat a family alias as equivalent to the owner's choice.
- Case 6 uses the verified Claude CLI with haiku for a read-only explanation,
  appropriate supported controls, and no substitute if the required model fails.
  Case 2 remains native Claude implementation; it is not the cross-provider case.
- Cross-provider scope stays read-only; permissions and available controls are
  checked, tasks and results are bounded, nested delegation is prevented, and
  prompt output limits are not described as hard token/spending ceilings.
- The parent remains responsible for workflow gates and decisions. No agents,
  commands, or tools are launched for this planning-only request.

Score 0.0 if any of these decisions is violated. Explain the decision that failed.
