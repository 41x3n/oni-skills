---
type: tool_used
name: skill-fired
tool: Skill
---

Indicator, not a quality score: did the run invoke a Skill tool call at all?

With the oni pack loaded, a feature request should route through `spark`. Under a with-without
ablation, the current evaluator automatically treats `tool_used: Skill` as a plugin-fired indicator
rather than part of the score.
