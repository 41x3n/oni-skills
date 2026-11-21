# Design depth

Load only the sections the proposed change triggers. The goal is to expose expensive mistakes while
the design is cheap to change, not to make every feature produce an architecture document.

## Minimum sufficient design

Record:

- intended outcome and observable success
- non-goals and the boundary of this slice
- existing behavior or component being reused
- new components only where a requirement or invariant needs an owner
- failure behavior and how the important path is proved

Remove a proposed component and ask what requirement fails. If none does, remove it. Prefer an
existing module, data path, or operational primitive when it preserves the same invariants.

## Durable state

Before approving a schema, queue, cache, ledger, or stateful workflow, show a compact state model:

| Question | Required answer |
|---|---|
| Ownership | Which domain owns each record and its lifecycle? |
| Purpose | What distinct invariant or query requires each durable record? |
| Cardinality | One or many on each relationship, and what enforces it? |
| Lifecycle | Valid states, transitions, terminal states, and deletion behavior. |
| Integrity | Database constraints, idempotency keys, and transaction boundary. |
| Concurrency | Duplicate, retry, race, and out-of-order behavior. |
| Access | Critical writes and reads; indexes follow these paths. |
| Retention | What is audited, expired, compacted, or legally retained? |
| Migration | Backfill, compatibility window, rollout order, and rollback. |

Use concrete example rows or one lifecycle trace when names alone hide how tables interact. If two
records share ownership, lifecycle, cardinality, and access patterns, justify why they are separate.
Ask the human to approve this model before `plan` turns it into migration tasks.

## External services

Trace `trigger -> service -> consumer` across every affected layer. The test strategy is incomplete
if the full suite cannot run when the real service is unavailable. Surface generated values, async
delivery, replay, and local replacement decisions before approval.

## Five-risk adversarial pass

After the design stabilizes, name the five most consequential uncovered inputs or failure modes.
Prioritize data loss, duplicate effects, invalid state, tenant or secret exposure, irreversible
migration, unbounded work, and operational recovery. Each retained risk needs an owner: a constraint,
test, monitor, rollout gate, or explicit accepted limitation.

If this pass changes the contract or state model, present the revised complete design for approval
again. Do not carry the old approval across a material revision.
