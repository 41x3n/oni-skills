# build on Codex

Read this when running under Codex. The gates and loop remain unchanged.
Use `model-routing.md` for shared task tiers and cross-provider CLI guidance.

## Available controls

Inspect the tools exposed by the current client. Different clients expose
different spawn fields and supported models. Missing tools are not permission
to change user settings or assume a configuration flag will add them.

- If the tool exposes `model` and `reasoning_effort`, set both from allowed
  values. Setting only the model can reset effort to a costly default. Choose
  a level the selected model supports.
- If it exposes configured agent roles instead, select an available role whose
  model, effort, permissions, and instructions suit the task. Do not invent roles.
- If a control is absent, do not pass it. Report the limitation and use the
  supported role/default or a verified CLI route for a read-only task.
- Use `fork_turns: "none"` when supported. Supply task-specific context;
  copying the entire conversation increases cost and confuses ownership.
- Report the actual model when the client exposes it. A request or configuration
  is not proof the client used that model; do not conceal substitutions.

Choose the cheapest suitable tier when cost information is known. Model IDs
are not portable across clients or providers. Never send Claude aliases to a
GPT-only spawn tool or assume every client has the parent's full model list.

## Roles and defaults

When the user asks to configure persistent roles, official Codex documentation
supports `model` and `model_reasoning_effort` in custom agent files. Verify the
current role/default schema before proposing settings. Never write guessed
`[agents]` keys automatically.

## Follow-ups and waiting

Resume an existing child with the available follow-up tool instead of spawning
another agent for the same task. Finished agents may be evicted or require
closing depending on the client; follow the current tool schema.

Do useful independent work while a child runs. When only a child remains, use
the client's event-driven wait. Keep blocking waits short enough to provide
progress updates; avoid busy polling.

## What carries over

The delegation thresholds, conclusion-only results, test-first gate, one task
per commit, session boundaries, and shell hygiene are unchanged. The parent
checks evidence and remains responsible for every workflow gate.

Source: [official Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).
