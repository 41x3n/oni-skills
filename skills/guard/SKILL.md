---
name: guard
description: Use when a change touches an external input path - a route, handler, queue consumer, webhook, upload, auth or session logic, secret handling, a command or query built from a value, or a config file the user owns. Also before shipping a diff that touches one. Names the trust boundary and what validates it.
---

# guard

Security has no natural trigger, so `spark` invokes this at design and `ship` at diff review.

## Gate

No external input path ships without naming, one line each: **where untrusted data enters**, **what validates it**, **who may read the result**. Any of the three answering "nothing" or "anyone" is the finding.

Never ask someone to paste a password, token, or private key into chat. Use stdin, a credential
store, or a secret manager without echoing it; if already pasted, do not repeat it and recommend rotation.

## Does this need guard?

Any one is a yes: a new route, handler, consumer, webhook or upload · auth or ownership logic · a secret moving · a command, query, path, URL or interpreter source built from a value · a config file the user owns · an upstream error reaching a caller.

## The five rules

Each is a real finding from this codebase. `references/findings.md` has the file, the attack path, and the fix.

1. **Every read route answers "whose data is this?"** No ownership filter means every caller gets every other caller's data — and unguessable IDs buy nothing, because nothing needs guessing.
2. **Upstream errors do not pass through.** Map public reasons; log detail. Verbatim reflection leaks infrastructure and credential state.
3. **A URL from a caller is a destination something will dial.** Checking the scheme is not validating the host: dial the IP you checked, re-check redirects, or allowlist origins. Trace who actually dials it first — an SSRF-shaped pattern is not SSRF until you do.
4. **Never build a command, query, path, or interpreter source by concatenation.** `shlex.quote`, argv, or parameter binding. A path with a space or `$(...)` in a stored command is persistent execution.
5. **Edits to config you do not own are surgical.** Match deletion granularity; back up first.

**A security fix that breaks no test is a fix whose test was wrong** — a passing suite can be defending the bug. Check before you claim the fix.

## Report

Per finding: `file:line`, severity, the path from attacker input to impact, the fix. No attack path, no finding. "Nothing above the bar" is a valid result.

## Refuse

- A severity with no attack path behind it.
- Fixing a finding without checking whether a test asserted it.
- Listing theoretical categories instead of reading the diff.
