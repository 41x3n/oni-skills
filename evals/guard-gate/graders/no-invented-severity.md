---
type: llm
name: no-invented-severity
---

Guards against the opposite failure: security theatre.

Score 1.0 if every security concern the response raises comes with a concrete consequence — who sees what they should not, or what an attacker does with it.

Score 0.0 if the response pads with generic security categories that have no attack path in this context — rate limiting, CSRF on a JSON API with no cookies, SQL injection where there is no SQL, "consider encryption at rest" with nothing named.

A response that raises exactly one concern, the right one, scores 1.0. Breadth is not the goal; noise is the failure being tested for.
