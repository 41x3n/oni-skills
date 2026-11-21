Plan six independent delegations. Do not launch agents, commands, or tools.
Use Oni's model-routing guidance; these supplied capabilities are authoritative.
For each case, state task tier, route/model, supported controls, and fallback.

1. In Codex, find files. The built-in agent tool permits only `scan-gpt` (fast) and
   `work-gpt` (general), with model and reasoning_effort fields. Claude is absent.
2. In Claude Code, implement one approved task. The built-in tool permits `haiku` and `sonnet`,
   with a model field but no effort field. Codex is absent.
3. In Codex, review code. The owner prefers a second provider when available but has not
   pinned a model. Claude CLI is absent. The built-in GPT review model is available.
4. In Codex, explain supplied code with Claude. Claude is installed but authentication
   fails. No model was pinned. A suitable built-in GPT model is available.
5. In Codex, the owner explicitly requires `special-claude` for a review. The built-in
   tool offers GPT models only. Claude CLI is installed and authenticated, but
   this account rejects `special-claude`. Other Claude and GPT models are available.
6. In Codex, explain supplied code using the owner's required `haiku` model.
   The built-in tool offers GPT models only. Claude CLI is authenticated and
   accepts `haiku`. Verified controls support a tool-free request, spending
   ceiling, and an external timeout. Source excerpts suffice; no file access is needed.

For a successful delegation to the other provider, also explain how you would
bound its scope, permissions, time, and returned output. Distinguish supported
hard limits from prompt requests. Do not treat a review as approval to ship.
