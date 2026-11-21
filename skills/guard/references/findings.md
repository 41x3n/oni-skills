# The findings behind guard's rules

Every rule in `SKILL.md` is one of these. They came from two audits run on
2026-09-22: one against two freshly generated Go services, one against this
pack's own scripts. Each was verified by reproducing it, not by reading alone.

This file is the evidence base, the same way `scripts/baseline.json` is the
evidence base for the language rules. A rule whose finding is listed here can
be checked; a rule invented from a category list cannot.

---

## 1. Unauthenticated cross-tenant read — HIGH

`internal/transcribe/http.go`, `GET /v1/jobs` → `Service.Jobs()`

```go
mux.HandleFunc("GET /v1/jobs", func(w http.ResponseWriter, r *http.Request) {
    writeJSON(w, log, http.StatusOK, jobsResponse{Jobs: s.Jobs()})
})
```

`Jobs()` returned `slices.Collect(maps.Values(s.jobs))` — the whole store. No
auth, no ownership concept anywhere in the codebase.

**Reproduced:** `curl http://host/v1/jobs` returned every job with its full
transcript and `media_url`.

Two things made it worse than a transcript leak:

- Media URLs for private content are usually presigned. `X-Amz-Signature`,
  `X-Goog-Signature` and SAS tokens **are bearer credentials**. Polling the
  endpoint harvests live, replayable download capability for other tenants'
  media.
- It nullified the service's own 128-bit job IDs. The strongest ID scheme in
  the comparison bought nothing, because no ID had to be guessed.

**Fix:** route deleted, along with `Jobs()` and its wire type. A job ID is now
the only capability to read a job.

**Note the asymmetry:** the other service in the comparison was safe here — not
because it defended the route, but because it never wrote one. Restraint was
the control.

---

## 2. Upstream error bodies reflected verbatim — MEDIUM

`internal/transcribe/service.go`, `fail()` stored `cause.Error()` directly into
the client-visible `Job.Error`.

Two classes of data escaped to anonymous callers:

- **Infrastructure.** A transport failure wraps `*url.Error`, which stringifies
  the full endpoint. With `DEEPGRAM_BASE_URL` pointed at an internal proxy:
  `dial tcp 10.4.2.17:8443: connect: connection refused` — an internal
  hostname, a private IP, a port, and DNS behaviour, handed to an external
  attacker with no other path to them.
- **Credential state.** A 401/403 from the provider told any caller whether the
  operator's key was expired, revoked, or over quota.

**Fix:** a closed vocabulary — `media could not be fetched`, `media contained
no transcribable audio`, `transcription provider failed`, plus a timeout case.
The full error stays in the chain for the log. Classification lives in the
adapter so the domain package still never imports the vendor package.

The default case matters: **an unrecognised error collapses to the vaguest
reason.** A failure mode nobody anticipated cannot leak by default.

---

## 3. Unrestricted host in a caller-supplied URL — LOW

Validation checked scheme and non-empty host and stopped:

```go
if (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" {
```

`file://` and `gopher://` were correctly rejected. `http://169.254.169.254/`,
`http://127.0.0.1:6379/` and internal DNS names all passed.

**Rated LOW deliberately, and left open.** The service never fetches the URL —
it only marshals it into a request body a third party acts on. There is no
SSRF against this service's own network or cloud metadata, which is the common
false positive. What remained was a blind reachability oracle against the
*vendor's* fetcher, readable only because finding 2 piped the outcome back;
fixing finding 2 closed the channel.

The lesson is the rating discipline, not the bug: **an SSRF-shaped pattern is
not an SSRF until you trace who actually dials the URL.**

**When something does dial it, validate the address it connects to, not the string:**

- Resolve the host, check every resulting address, then connect to that checked IP. Checking a
  name and letting the client resolve it again loses to DNS rebinding.
- Turn off automatic redirects, or re-run the whole check on every hop.
- Reject loopback (`127.0.0.0/8`, `::1`), `0.0.0.0` and `::`, link-local (`169.254.0.0/16`,
  `fe80::/10`, which holds cloud metadata), RFC1918, unique-local `fc00::/7`, and IPv4-mapped
  IPv6 (`::ffff:127.0.0.1`) by checking the mapped address. Also reject `.internal` names.
- An allowlist of origins beats every blocklist above. Prefer it when the destinations are known.

---

## 4. Unquoted path in a persisted command — MEDIUM

`scripts/install-hook.sh` wrote the hook command into the user's settings:

```python
command = f"bash {router}"      # router is the absolute checkout path
```

A checkout at `~/Downloads/oni pack/oni` stored a command the shell splits into
`bash /Users/x/Downloads/oni`. Any file planted at that truncated prefix
executes as bash **on every session start, persistently** — and `~/Downloads`
is browser-writable, so an extension-less file named `oni` is a realistic
plant. A path containing `$(...)` or a backtick was direct injection.

Worse, the health check would have called it fine: it stripped a `bash ` prefix
and ran `[[ -f ]]` on the rest, which succeeds on the unsplit string.

**Fix:** `shlex.quote(router)`, and the checker parses with `shlex.split` and
takes the last word.

**The tell:** the pack's own plugin manifest already quoted the same path
correctly. Two code paths configuring the same thing disagreed about the
invariant — that disagreement is the bug, found by comparing them.

---

## 5. Config edit at the wrong granularity — LOW

The same script filtered the user's `SessionStart` list at *entry* granularity
while matching at *hook* granularity. An entry is a group, and users
consolidate several commands into one. If the router shared a group with the
user's own hooks, both `--remove` and a re-add silently deleted theirs.

**Fix:** strip only matching hooks; keep the entry if anything else remains.

Recoverable only because the script took a timestamped backup first. **Back up
before writing to a file you did not create** — it turned a data-loss bug into
an inconvenience.

---

## 6. Path spliced into interpreter source — LOW

```bash
python3 -c "import json; json.load(open('$SETTINGS'))"
```

A path containing an apostrophe becomes executable Python. Not independently
exploitable — the paths come from trusted config — but it is the same
missing-quoting defect as finding 4, and the same file already did it correctly
elsewhere with an argv heredoc.

**Fix:** pass paths as `sys.argv[1]`, never into the source string.

---

## The tests were defending the bugs

Fixing findings 1 and 2 broke three tests, all of which asserted the vulnerable
behavior:

| test | asserted | now asserts |
|---|---|---|
| `TestListJobs` | `GET /v1/jobs` returns 200 and two jobs | fails if 200; greps the body for leaked IDs and URLs |
| `TestRunRecordsTranscriberFailure` | `Job.Error == upstream.Error()` | upstream text absent, public reason present |
| `TestRunSurvivesPanickingTranscriber` | panic text appears in `Job.Error` | panic detail does **not** reach the client |

A fourth was deleted outright: `TestJobsReturnsNewestFirst` tested the sort
order of a list endpoint that should not exist.

This is the general case, not an accident of this codebase. A test written
against behavior nobody examined for security locks that behavior in, and a
green suite then reads as evidence the code is fine. When a security fix
changes observable behavior and no test fails, the coverage is pointed at the
wrong thing.

## What the audits cleared

Worth recording, so the same ground is not re-covered: the uninstall path only
ever unlinks symlinks and never follows to a target; the scan and measure
scripts have no `eval`, `pickle`, `subprocess` or network access, and the
measure script reads token counts only, never message content; no credentials
anywhere in the repo; no injection reachable through the services' JSON
handling, since `json.Marshal` escapes and path parameters are used only as map
keys.
