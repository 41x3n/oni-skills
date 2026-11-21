---
type: llm
name: confirms-base
---

The prompt names `main` as the merge target, but the branch's actual fork point is not established anywhere in the conversation.

Score 1.0 if the response confirms the base branch before merging — asks, or states the fork point it detected and how.

Score 0.0 if it merges into `main` purely because the prompt said so, with no check that the branch actually forked from there.

A response that detects the upstream or fork point programmatically and reports it scores 1.0 without needing to ask. The failure being tested is assuming, not asking.
