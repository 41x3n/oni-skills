# Measurements

These numbers come from the author's own usage and repositories. Nobody else can reproduce them,
and your results will differ. To measure your own usage:

```bash
python3 scripts/measure.py --days 28
```

It reads local Claude Code transcripts (`~/.claude/projects`) and Codex sessions
(`~/.codex/sessions`) and reports where the context cost goes.

## Where the cost was

Four weeks of the author's Claude Code usage:

| | |
|---|---|
| API calls | 21,178 |
| cache read | 5,254M tokens |
| average context per call | 256K tokens |
| main-thread share of cost | 91.0% |
| skill-body share of content | ~1% |

Shortening skill prose was worth about 1%. Keeping bulk content out of the main context was worth
30-50%. That is why oni delegates by default.

## A/B against a larger pack

Same prompt, same Go service. Both runs reached the same design, shipped green tests, and found
the `io.Reader` bug shown in the README.

| | oni | larger pack |
|---|---|---|
| turns | 43 | 103 |
| cost | $2.31 | $7.18 |
| markdown written | 192 lines | 1,383 lines |

## Expected savings by lever

| Lever | Estimated reduction |
|---|---|
| Delegation by default | 30-50% |
| Session boundaries | 10-20% |
| Subagent model routing | ~7% |
| No inline heredocs | 2-4% |
| Terser skill prose | ~1% |

Other notes from the same sample:

- A spec, plan, per-task briefs and reports came to 492 files and about 2.2M tokens, all re-read
  during execution. Hence one plan file per feature.
- In Codex, 4 of 7 subagents ran the top model at `xhigh` effort, even for file lookups. That is
  what happens when nobody chooses.

Running oni beside another large process pack costs both packs' skill descriptions every session
with none of the savings. Pick one. `doctor.sh` warns when both are enabled.
