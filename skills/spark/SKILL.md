---
name: spark
description: Use before a new feature, component, behavior change, or design choice. Clarifies intent, proposes the smallest safe design, and stops for explicit approval.
---

# spark

Idea to approved design. No code until approved.

## Gate

No implementation until the human explicitly approves the complete design presented. An answer,
correction, or approval of one decision approves only that decision, not the whole stage.

## 1. Classify, say it out loud

- **spike** — feasibility question; answer, do not build.
- **bounded** — existing flow in this repo; short in-chat design.
- **architectural** — new subsystem or changed shared interface; full path below.

Doubt takes the heavier path. Complexity may upgrade, never downgrade it.

## 2. Establish shared understanding

Read only relevant instructions, history, and touched code; delegate broad search. Write back the
outcome, constraints, success criteria, assumptions, and non-goals. Invite correction.

## 3. Resolve material uncertainty

Ask one focused question at a time, up to five per pass, only when it changes scope, contract,
ownership, invariants, or failure behavior. Resolve repository-decided details yourself.

## 4. Research gate

Version, cloud API, protocol, or price involved? Search and cite a primary source before proposing.

## 4b. Conditional depth

External input or secret? Invoke `guard`; name the trust boundary.

Architectural work, durable state, external services, concurrency, or migrations? Read
`references/design-depth.md` and apply only the relevant checks.

## 5. Smallest safe design

Offer alternatives only for a real choice. Recommend the smallest safe option; name its trade-off
and failure mode. Cut components without a requirement or invariant.

## 6. Design

Scale to risk; cover boundaries, flow, failures, and proof. For architectural work, present the final
design and open decisions together, then ask for explicit approval. When the plan follows mechanically
from the design, show the WORK.md slices in the same message so one approval covers both; an
approval that names more stages ("approve plan, do all slices") covers those stages.

## 7. Hand off

- architectural, approved → invoke `plan`
- bounded, approved → invoke `build`
- spike → report a recommendation; label anything built as throwaway

## Refuse

- Code before approval.
- "Too simple to need approval." The artifact scales with simplicity; the gate never does.
- A design with no named failure mode.
