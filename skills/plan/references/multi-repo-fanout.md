# Fan out one plan across repos

Read when an approved design spans two or more repos or deployed services and
the plan is about to get one slice per repo. The parent session stays the
orchestrator; each slice runs in its own fresh session (a thread, worktree or
agent per repo) at the same time.

## Use it when

- Every slice lives in a different repo or service, and
- the contract between them can be written down before any code, and
- each slice can be built and verified alone against that contract.

Stay sliced and sequential otherwise: one repo, a contract still being
discovered, or slices that must land in order. Parallel sessions on an unclear
contract produce three confident, incompatible halves.

## The plan

Add a `## Contract` section under `## Approved design`. It is the only shared
state between sessions, so it names exact strings, not intentions:

```markdown
## Contract
- Request field: `liveVertical: boolean` on create/add/PATCH Feed
- Reply fields: `liveVerticalUrl`, `liveVerticalErrorCode`
- Error codes: `LIVE_VERTICAL_UNAVAILABLE`, `LIVE_VERTICAL_NOT_LIVE`
- Setting keys: `media.liveVertical.enabled`, `media.liveVertical.defaultOn`
- Paths: `…/feed/{feedId}/{uuid}/9x16/index.m3u8`
- Old-peer rule: each side ignores an unknown field, so deploy order is free
```

One slice per repo, same branch name in each. Each slice ends with its own PR.
Add a last slice, owned by the parent, with three tasks:

1. Cross-repo contract check: grep every contract string in every repo.
2. Merge and deploy: PR state, deploy checks, deployed version, migrations run.
3. Dev run against the real services: the rollout checks, each with a pass rule.

The dev run is not optional. Unit tests mock the vendor; quotas, start times
and stuck jobs only show against the real one.

## Launching

Each child gets: the plan path, its slice number, the contract, blanket commit
approval if the human gave it, and the instruction to end with a report of what
changed, what deviated from the plan, and what is still open.

Plan approval is not permission to launch. Before launching, list one line per
child (repo, slice, branch) and ask once; one yes launches them all, each in its
own message, at the same time.

## Orchestrating

The parent owns every gate. Wait on all children, not one; act on each report
as it lands. Sort every open point:

| Point | Action |
|---|---|
| Bug inside the slice | Send back to that child's session |
| Vendor or API question | Add to the open-questions doc |
| Needs a real deploy to answer | Add to the dev-run checklist |
| Gap between slices | Check the other slices, then decide or ask |
| Pre-existing problem | Propose a separate issue |
| Deviation from the plan | Accept only if no user-visible state is hidden; otherwise ask |

A deviation that hides a state a user should see (a setting with no read-only
view, an error with no message) is a missing requirement, not a simplification.
Accepting one cost a follow-up PR the first time this pattern ran.

## Test scripts against real services

- Click or submit once, then read back what was created. A double submit makes
  duplicate records, and dev data is not deleted to clean up.
- Poll for the status names the system actually reports, not the ones you
  expect. Read one real response before writing the loop.
- Record every resource the run creates, and confirm the vendor side is torn
  down after it stops.

## Done

The plan's Status is `shipped` only after the dev run. Write its results into
the tracker issue and the operations doc, including checks not yet run.
