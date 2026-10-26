# Project Status

Research status as of: 2026-07-14
Documentation instructions clarified: 2026-10-26; no experiments rerun.

See [CLAUDE.md](CLAUDE.md) for the full project brief. This file tracks build progress;
[RESULTS.md](RESULTS.md) has the actual pilot findings.

## State: step-two build complete, scaled to n=50

All three deliverables from the build brief are built and proven end-to-end, first at a small
n=10 pilot scale, then scaled to n=50 per system:

- [x] System A — single-LLM baseline (`src/baseline/`)
- [x] System B — multi-agent system (`src/multiagent/`): literature, molecular, and signal
      generator agents → adversarial review agent → ranking agent → deterministic orchestrator
- [x] Evaluation harness (`src/evaluation/`): blind citation-support + novelty judge,
      independent falsification-survival check, hallucination-rate and grounding-depth
      metrics, comparison table with Wilson-interval uncertainty
- [x] Full logging (JSONL, one file per run in `logs/`) for every prompt, tool call,
      retrieval, and intermediate hypothesis
- [x] Results written up in [RESULTS.md](RESULTS.md), n=10 and n=50 both retained

Both systems share one model/temperature via `src/config.py`; only the architecture differs,
per the brief's fairness requirement. Current config: `run_size=50`,
`candidates_per_generator=25` (75 candidates generated per multi-agent run before ranking
trims to 50).

## How to run

Follow the [installation instructions](README.md#installation) for macOS/Linux or Windows
PowerShell, then run from the repository root with that virtual environment activated:

```bash
python run_baseline.py      # System A
python run_multiagent.py    # System B
python run_evaluation.py    # scores the latest baseline_*.json and multiagent_*.json in outputs/
```

If PowerShell activation is unavailable, substitute `.\.venv\Scripts\python.exe` for
`python`; no execution-policy change is needed. These commands call external APIs and
are experiment runs, not dependency-free documentation checks.

Requires `ANTHROPIC_API_KEY` set in `.env` (see `.env.example`) with sufficient credit
balance. At the current `run_size=50`, one full pass of all three (baseline + multiagent +
evaluation) is a few hundred LLM calls and has twice run an account's credit balance to zero
mid-run during this build — budget generously, or drop `run_size` back down for a cheaper
smoke test. The evaluation harness logs progress incrementally, so a credit-exhaustion
failure loses no work; re-running after topping up picks the existing `outputs/*.json` files
back up and starts scoring from scratch (fast, since it doesn't regenerate the runs).

## Project layout

```
src/
  config.py            shared model/temperature/run_size config
  schemas.py             Hypothesis, Source, RunResult (the shared hypothesis object)
  tools.py                 retrieval tool schemas + dispatch, shared by both systems
  llm_client.py              Anthropic tool-use loop + SourceRegistry (shared machinery)
  validation.py                code-side "drop uncited claims" enforcement
  logging_utils.py               JSONL run logging
  retrieval/                       Europe PMC, Open Targets, CIViC, ClinicalTrials.gov clients
  baseline/                          System A
  multiagent/                          System B (generators, adversarial, ranking, orchestrator)
  evaluation/                            harness (judge, falsification, metrics, entry point)
outputs/    one timestamped JSON per run (baseline_*, multiagent_*, evaluation_*.json/.md)
logs/       local JSONL research traces; intentionally not tracked in Git
```

## Known limitations at this stage

- **n=50 per system** — much tighter confidence intervals than the original n=10 pilot, but
  still a modest sample; per the brief, don't over-interpret gaps that fall within each
  other's interval (see RESULTS.md — this already caught one metric, citation support rate,
  reversing direction between the n=10 and n=50 runs).
- Baseline has no hard cap on hypothesis count (it asks the model for `run_size` but doesn't
  enforce it) and slightly overshot 50 → 52 in the current run; multi-agent's ranking stage
  deterministically cuts to exactly `run_size`.
- Retrieval APIs are queried live at run time; results (and therefore hypotheses) will differ
  run to run and are not reproducible byte-for-byte, though full logs make each run
  individually auditable.
- No patient-data/TCGA analysis — explicitly out of scope for this brief, deferred to a
  later phase per CLAUDE.md.

## Bugs fixed so far

See the "Bugs found and fixed" section in [RESULTS.md](RESULTS.md) for full detail. Summary:
an `ANTHROPIC_BASE_URL` env collision; extended-thinking token truncation silently emptying
tool submissions (fixed with a higher token budget + truncation-retry); malformed-JSON edge
cases from the model, including a scale-dependent one where the model stringified an entire
JSON array (silently degrading the ranking agent to a no-op at n=50 until caught by log
inspection, not the exit code). All fixes are explicit and logged, not silently swallowed —
parsing failures are visible in the JSONL logs as `*_malformed_*` / `*_unparseable` /
`*_wrong_type` events.

## Possible next steps (not started, awaiting direction)

- Scale up further if a tighter comparison is wanted — intervals are still fairly wide at
  n=50 for some metrics (e.g. citation support).
- Tune agent prompts/architecture based on where System B underperforms (citation support was
  behind baseline at n=50) — brief explicitly cautions against tuning to make System B "win,"
  so any changes should be justified on their own merits, not by the scoreboard.
- Begin the separate, later patient-data/TCGA brief.
