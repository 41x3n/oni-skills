# Choose an agent model

Read before delegating when model choice is uncertain, and before using another
provider's command-line tool. All workflow gates remain the parent's responsibility.

## Select a route

1. Classify the task using `build`'s fast/general/stronger tiers. Use the least
   costly suitable available model when pricing is known. Do not assume model
   cost or quality from its name alone. Escalate difficulty when evidence warrants it.
2. Inspect available tools, model choices, configured roles, and supported controls.
   A model listed for the parent is not necessarily available to a child or CLI.
   Honor explicit user model choices; never silently replace a required model.
3. Prefer the built-in agent tool when it supports the chosen model. Set model
   and supported effort controls explicitly. On Codex, read `codex.md` for tool
   and role differences. On Claude, use supported model IDs or aliases; confirm
   resolved model information when the client exposes it.
4. Give a short task, relevant evidence, permitted actions, success condition,
   and a result limit. Pass task-specific context rather than the conversation.
5. Use another provider's verified CLI for read-only research, explanations, or
   review when useful or requested. These CLI routes must not edit files.
   Approved implementation through built-in agents still follows `build`.
   State the chosen provider/model and why it fits the task before launching.
6. If command, authentication, model, permissions, or task execution fails,
   report the failed route. Make at most one suitable supported fallback when
   no model is pinned. Otherwise report the limitation; do not substitute the
   required model. If no suitable delegate exists, the parent handles the task.

Claude's Haiku, Sonnet, and Opus families are common examples of these task tiers,
not universal requirements. Resolve current allowed models at runtime. GPT model
IDs and Claude aliases are not interchangeable. Independent review can provide
another perspective, but is not proof a change is correct or permission to ship.

## Cross-provider task boundary

- Check installed CLI help and authentication status without exposing credentials.
  Use existing authentication; do not ask for pasted tokens or alter user settings.
- Run in a neutral temporary directory with selected excerpts when possible.
  Pass prompts via stdin and commands as argv, without shell interpolation.
  Do not include credentials, unrelated files, or the full conversation.
- Inspect effective permissions and tools. Disable unrelated apps, plugins,
  hooks, and nested delegation using verified client controls. File read-only
  mode does not disable connected apps or their external write operations.
  If required isolation cannot be established, use the supported fallback.
- Prefer a tool-free request when supplied excerpts suffice. For repository
  reading, use the client's read-only controls and only required read tools.
  Never use permission-bypass flags or grant edits to complete this task.
- Put an external timeout around the process. Set client turn and spending
  limits where supported. Do not treat a requested word limit as a hard token
  or spending ceiling. The inspected Codex CLI has no spending-cap flag.
- Apply the current Oni writing guidance explicitly to the fresh process; it
  may not inherit the parent's instructions. Tell it not to delegate or use
  unrelated tools, and retain the parent's responsibility for gates.
- Capture raw logs outside the conversation. Return at most 20 useful lines
  with evidence locations, uncertainties, and actual model information when
  reported. Validate the result against evidence; failures are not valid findings.

## Claude command-line controls

For a text-only task, the inspected client supports this argument pattern.
Verify help on the target machine before using it; aliases and flags can change.
The caller must supply the prompt through stdin, a neutral cwd, and a timeout.

```text
claude -p --model haiku --effort low --safe-mode --tools ''
  --disable-slash-commands --no-session-persistence --setting-sources ''
  --strict-mcp-config --mcp-config '{"mcpServers":{}}'
  --output-format json --max-budget-usd 0.15
```

This is an argv pattern, not a multiline shell command. Empty arguments remain
empty arguments. Safe mode and the empty tool list suppress customization and
tool access. Check JSON success/error fields, not just the process exit status.

## Codex command-line controls

The inspected `codex exec` supports model choice, ephemeral execution, user-config
isolation, read-only file access, JSON events, and a prompt from stdin:

```text
codex --ask-for-approval never exec --model <allowed-model>
  --ephemeral --ignore-user-config --ignore-rules --sandbox read-only
  --skip-git-repo-check --json
  -c 'model_reasoning_effort="low"' -c 'features.multi_agent=false' -
```

Use a neutral cwd without project configuration. `--ignore-user-config` is an
exec option; it is not accepted by `codex mcp list`. It retains normal login
authentication. The inspected client also supports `--ignore-rules`, used here
to suppress ambient instruction files. Supply the task and writing guidance
explicitly. Check managed/project integrations as well as user settings.
Do not assume `-c 'mcp_servers={}'` disables existing servers. Inspect enabled
status and effective tools; names can remain in `mcp list` even when disabled.

Codex's file sandbox is not a tool-free mode. Built-in tools may remain available.
Verify the allowed task has no unrelated tool activity in JSON events, and fail
closed when required integration isolation is unavailable. `never` prevents
interactive approval; it does not grant permission to blocked actions. Bound
elapsed time externally and validate completed result/error events. Do not claim
a resolved model when only the requested model is visible.

## Sources

- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Claude subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude CLI](https://code.claude.com/docs/en/cli-reference)

Controls were checked against installed Claude Code 2.1.285 and Codex CLI 0.160.1.
Presence of a binary or successful login status is not proof of model access.
