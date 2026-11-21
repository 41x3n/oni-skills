---
type: llm
name: reviews-state-model
---

This architectural request introduces durable state whose mistakes would be expensive to migrate.

Score 1.0 only if the response stops before implementation planning and presents a compact,
reviewable state model covering:

- entity ownership and why each durable record exists
- relationships or cardinality
- lifecycle or state transitions
- deduplication, concurrency, or transaction invariants
- retention or deletion behavior
- the important read/write access patterns

It must ask the human to review the model. Exact table names and SQL are not required.

Score 0.0 if it writes a task plan without exposing the state model for review, or produces tables
without explaining the invariant each one protects.
