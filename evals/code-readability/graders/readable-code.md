---
type: llm
name: readable-code
---

Judge the returned TypeScript module, not promises about readability or formatter output.
The starting module has adjacent top-level declarations and functions, and its preparation,
execution, persistence, loop, and return steps run together. That dense baseline fails.

For full credit, require all of these observable outcomes:

- Blank lines separate the top-level types and functions. Within functions, blank lines
  separate meaningful steps, including preparation from execution, upload from persistence,
  and result initialization/iteration/return. Equivalent cohesive restructuring is valid;
  blank lines inside every expression or between every statement are not required.
- Names communicate roles, helpers have coherent responsibilities, and the sequential
  execution plus failure/cleanup flow are apparent from the code. Do not reward arbitrary
  short-function limits, trivial extracted helpers, or comments narrating obvious lines.
- `publishAllowed` is optional. Archived assets and assets with explicit `false` return
  the original skipped shape without dependency calls. Missing and `true` retain publishing.
- Results retain their shapes and input order. Processing stays sequential, upload is
  awaited before record, and record is awaited before returning success. Preparation stays
  outside the cleanup region: failed preparation does not discard. Successful preparation
  always leads to awaited discard, including when upload or record rejects. Rejections
  propagate, with the original `finally` behavior if discard itself rejects.
- No libraries, unrelated behavior changes, or broad refactors appear.

Score 1.0 when all outcomes hold. Score 0.5 when semantics are preserved and the explicit
false skip is correct, but one meaningful spacing/clarity requirement remains unmet.
Score 0.0 for missing code, an incorrect skip condition, any semantic regression, or a
module that retains the dense top-level and logical-step layout. Adding the flag alone to
the baseline is still 0.0. Explanation text cannot compensate for dense or incorrect code.

Do not require particular helper names, comments, or phrasing. Well-structured inlined
logic or a cohesive helper can both pass. Do not require execution claims: this fixture
forbids execution, so honestly reporting verification as skipped is correct.
