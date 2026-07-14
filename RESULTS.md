# Results — Multi-Agent vs Single-LLM Hypothesis Generation

## Current results: n=50 per system (2026-07-14)

Model: shared across both systems (see `src/config.py`)

Baseline run: `outputs/baseline_20260713T215554Z.json` (52 hypotheses — model slightly
overshot the requested 50; it has no hard cap unlike the multi-agent system's ranking cutoff)
Multi-agent run: `outputs/multiagent_20260713T232713Z.json` (50 hypotheses, selected from 79
candidates)
Evaluation report: `outputs/evaluation_20260714T022723Z.json` / `.md`
Full traces: `logs/baseline_20260713T215554Z.jsonl`, `logs/multiagent_20260713T232713Z.jsonl`,
`logs/evaluation_20260714T022723Z.jsonl`

### Comparison table

| Metric | Baseline (n=52) | Multi-agent (n=50) |
|---|---|---|
| Hallucinated citation rate (generation-time) | 0/83 (0%) [0–4%] | 1/418 (0.2%) [0–1%] |
| Citation support rate (independent judge, supporting cites) | 33/78 (42%) [32–53%] | 33/108 (31%) [23–40%] |
| Falsification survival (independent adversarial search) | 0/52 (0%) [0–7%] | 0/50 (0%) [0–7%] |
| Novelty rate (non-obvious vs. restatement) | 36/52 (69%) [56–80%] | 34/50 (68%) [54–79%] |
| Grounding depth (avg valid supporting sources/hypothesis) | 1.50 | 2.16 |

n≈50 hypotheses per system. Intervals are 95% Wilson score intervals. Still a modest sample —
treat as a stronger-but-not-definitive pilot comparison.

### Interpretation

- **Citation existence enforcement remains excellent at scale.** 0% hallucinated citations for
  baseline (0/83); multi-agent had exactly 1 hallucinated citation out of 418 attempted (0.2%),
  correctly caught and dropped by code-side validation before it could reach the final output.
  Both are effectively clean; the multi-agent system simply attempts far more citations in
  total (more agents, more searches), so its raw count is larger even though its rate is just
  as low.

- **Citation support rate reversed from the n=10 pilot.** At n=10, multi-agent looked ahead
  (32% vs. 14% full support). At n=50, baseline is now ahead (42% vs. 31%), with overlapping
  confidence intervals in both cases. This reversal is a direct, concrete illustration of why
  the brief warns against over-interpreting small-n gaps — the n=10 direction simply didn't
  hold once the sample grew 5x.

- **Falsification survival dropped to zero for both systems.** At n=10, one multi-agent
  hypothesis survived independent adversarial review. At n=50, *zero* hypotheses from either
  system fully survived — every single one was rated "weakened," none "refuted." This is now
  a much more solid finding at this larger n: neither architecture produces early-detection
  claims that hold up cleanly against genuinely skeptical, independent search. This looks like
  a property of the problem domain (early-detection hypotheses for a rare, hard-to-detect
  cancer are inherently contestable) rather than a weakness specific to either system.

- **Grounding depth gap held and widened.** Multi-agent 2.16 vs. baseline 1.50 avg supporting
  sources per hypothesis — same direction as n=10 (2.50 vs. 2.20), and the most consistent
  multi-agent advantage across both runs. This is the one metric where the multi-agent
  system's edge looks real rather than noise.

- **Novelty converged to a near-tie.** 69% vs. 68% (was 90% vs. 80% at n=10) — no meaningful
  gap at this n.

### Bottom line at n=50

The multi-agent system's most defensible advantage is grounding depth — consistent in
direction and magnitude across both the n=10 and n=50 runs. Citation support rate reversed
between runs and should be treated as noise, not signal, at these sample sizes. Falsification
survival converged to zero for both systems, which is itself a meaningful (if humbling)
finding about the domain. No metric shows a large, robust, non-overlapping multi-agent win —
consistent with the brief's instruction to report the honest result rather than engineer one.

---

## Earlier pilot: n=10 per system (2026-07-13)

Kept for transparency and as the direct point of comparison for the citation-support reversal
noted above.

Baseline run: `outputs/baseline_20260713T200812Z.json`
Multi-agent run: `outputs/multiagent_20260713T202858Z.json`
Evaluation report: `outputs/evaluation_20260713T210801Z.json` / `.md`

| Metric | Baseline (n=10) | Multi-agent (n=10) |
|---|---|---|
| Hallucinated citation rate (generation-time) | 0/25 (0%) [0–13%] | 0/92 (0%) [0–4%] |
| Citation support rate (independent judge, supporting cites) | 3/22 (14%) [5–33%] | 8/25 (32%) [17–52%] |
| Falsification survival (independent adversarial search) | 0/10 (0%) [0–28%] | 1/10 (10%) [2–40%] |
| Novelty rate (non-obvious vs. restatement) | 9/10 (90%) [60–98%] | 8/10 (80%) [49–94%] |
| Grounding depth (avg valid supporting sources/hypothesis) | 2.20 | 2.50 |

See git-free history in `outputs/` and `logs/` for this run's full detail; the interpretation
above (n=50 section) supersedes conclusions drawn from this smaller run alone.

---

## Bugs found and fixed (research-process transparency)

- `ANTHROPIC_BASE_URL` set in the shell (used internally by Claude Code) was being inherited
  by the `anthropic` SDK client, routing requests to the wrong endpoint. Fixed by pinning
  `base_url` explicitly in `get_client()`.
- Extended-thinking output occasionally consumed the full `max_tokens` budget before the
  model reached its tool call, silently truncating `submit_hypotheses` into an empty `{}`
  (two of three generator agents produced 0 candidates in one run without erroring). Fixed
  by raising `max_tokens` (8192, then 16000 at n=50) and adding truncation-detection +
  automatic retry in `run_tool_loop` / `run_single_tool_call`.
- The model occasionally violated the declared JSON schema (a bare string instead of an
  array, or a string instead of an object inside an array). Hardened the generator, ranking,
  and adversarial-review parsing to validate/skip malformed entries with a logged warning
  instead of crashing.
- At n=50 scale, the model sometimes stringified an entire JSON array (e.g. the ranking
  agent's `scores` field) instead of nesting real JSON. The earlier per-item defensive check
  absorbed this without crashing but silently degraded ranking to a no-op — all 76 candidates
  got zero score, so "ranking" just returned candidates in original generation order. Caught
  by inspecting the run log rather than trusting the "success" exit code; fixed with an
  explicit `json.loads()` fallback applied consistently in the ranking, generator, and
  adversarial-evidence parsers, then re-ran and confirmed real score variance.
- Two runs stopped mid-way on `anthropic.BadRequestError: credit balance too low` — a billing
  limit, not a code issue. The evaluation harness's log-progress design meant no work was
  lost; re-running after topping up resumed correctly from the existing output files.
