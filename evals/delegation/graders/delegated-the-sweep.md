---
type: llm
name: delegated-the-sweep
---

This is a repo-wide search whose raw output does not belong in the main context.

Score 1.0 if the response either:

- dispatched the search to a subagent and reported back a conclusion (a `file:line` list or an answer), or
- ran bounded searches whose output stayed small — a grep with a line limit, counts, or paths only — and did not read whole files to answer it.

Score 0.0 if the response:

- read multiple files in full into the main context to answer the question
- ran an unbounded search and pasted the raw result
- used no search at all and answered from assumption

The distinguishing question: at the end of the turn, is the main context holding a conclusion, or is it holding the search output? A conclusion scores 1.0; a dump scores 0.0.

Answer correctness is not scored here. A wrong answer arrived at with good context hygiene still scores 1.0 on this grader.
