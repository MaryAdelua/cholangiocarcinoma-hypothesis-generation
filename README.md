# Cholangiocarcinoma Early-Detection Hypothesis Generation: Multi-Agent vs. Single-LLM

A research instrument comparing whether a multi-agent LLM system generates early-detection
hypotheses for cholangiocarcinoma that are better grounded in real evidence and more
resistant to falsification than a single LLM with the same tools.

**This is a research instrument, not a diagnostic tool.** It does not detect cancer or
provide medical advice. It produces hypotheses for researchers to investigate further.

## Project Overview

Cholangiocarcinoma has poor survival outcomes largely because it is usually diagnosed late.
Large language models can search literature, genomic/variant databases, and clinical trial
registries far faster than a human researcher — but an LLM asked to "propose hypotheses"
will also confidently cite sources that don't say what it claims, or restate well-known
facts as if they were novel. The question this project asks is narrow and falsifiable:
**does splitting that work across multiple specialized, adversarial agents produce hypotheses
that are more defensible than a single model doing the same task in one pass** — or is
architecture, in this setting, not the thing that matters?

Two systems are built to be measured against each other, not to make either one "win":

- **System A (baseline)** — one LLM, one pass, the same retrieval tools, asked to propose
  hypotheses directly.
- **System B (multi-agent)** — literature, molecular, and signal generator agents produce
  candidates; an adversarial agent actively tries to disconfirm each one; a ranking agent
  scores grounding/survival/novelty; a deterministic orchestrator ties it together and logs
  every step.

Both share one model, one temperature, and identical tool access via a single config file
(`src/config.py`) — architecture is the only variable allowed to differ, so that any measured
difference is attributable to it and not to a stacked deck. An evaluation harness then scores
every hypothesis from both systems, blind to which system produced it, on four axes: citation
validity, falsification survival under an independent adversarial search, novelty vs.
triviality, and grounding depth. See [CLAUDE.md](CLAUDE.md) for the full build brief this
project was built against.

**Current result** (n≈50 per system): the multi-agent system's most consistent advantage is
grounding depth (2.16 vs. 1.50 avg. supporting sources/hypothesis, consistent in direction
across both an n=10 and n=50 run). Other metrics either favor the baseline, are statistically
indistinguishable, or converged to a shared finding — see [RESULTS.md](RESULTS.md) for the
full comparison table and interpretation, and note its explicit caution against
over-interpreting small gaps.

## Repository Structure

```
CLAUDE.md                  Full build brief / research design
RESULTS.md                 Comparison tables and interpretation (n=10 and n=50 runs)
STATUS.md                  Build/project status tracker
RUN_MANIFEST.json / .md    Per-run provenance: model/config used, verified vs. reconstructed
REPRODUCIBILITY_NOTES.md   Known reproducibility limitations and how they're addressed

src/
  config.py                 Shared model/temperature/run-size config (both systems, one file)
  schemas.py                   Hypothesis, Source, RunResult — the shared hypothesis object
  tools.py                       Retrieval tool schemas + dispatch, shared by both systems
  llm_client.py                    Anthropic tool-use loop + SourceRegistry
  validation.py                      Code-side "drop uncited claims" enforcement
  logging_utils.py                     JSONL run logging (every run is self-describing)
  retrieval/                             Europe PMC, Open Targets, CIViC, ClinicalTrials.gov
  baseline/                                System A — single-LLM baseline
  multiagent/                                System B — generators, adversarial, ranking, orchestrator
  evaluation/                                  Evaluation harness — judge, falsification, metrics

run_baseline.py     Entry point: python run_baseline.py
run_multiagent.py   Entry point: python run_multiagent.py
run_evaluation.py   Entry point: python run_evaluation.py

outputs/   One timestamped JSON (+ .md for evaluation) per run — tracked in git
logs/      One timestamped JSONL per run — full prompt/tool-call/retrieval trace,
           NOT tracked in git (size; see Reproducibility below), kept on disk
```

What each major directory is for:

- **`src/retrieval/`** — thin clients for the four open-access data sources this project is
  allowed to draw facts from (Europe PMC/PubMed, Open Targets, CIViC, ClinicalTrials.gov).
  Every retrieval returns a `Source` with a stable ID, title, snippet, and URL — nothing here
  ever returns free text the model could mistake for a citable claim.
- **`src/baseline/`** — System A. A single prompt, the shared retrieval tools, one
  conversation, one final structured submission.
- **`src/multiagent/`** — System B. Each agent (literature/molecular/signal generators,
  adversarial reviewer, ranker) is its own module; `orchestrator.py` is the only place that
  wires them together, and it's plain deterministic Python, not another LLM call.
- **`src/evaluation/`** — the actual research instrument. Loads both systems' latest outputs,
  scores every hypothesis blind to source, and produces the comparison table.
- **`outputs/`** — the result of each run: which hypotheses survived citation validation, what
  was dropped and why, and (for evaluation runs) the full per-metric comparison.
- **`logs/`** — everything that happened during a run, at a level of detail beyond what any
  single output file records: every prompt sent, every tool call and its raw result, every
  intermediate hypothesis before validation. Present on disk but not tracked in git (see
  Reproducibility).

## Installation

Requires Python 3.11+ and an Anthropic API key with available credit.

Clone the existing repository without changing its directory name:

```bash
git clone https://github.com/MaryAdelua/cholangiocarcinoma-hypothesis-generation.git
cd cholangiocarcinoma-hypothesis-generation
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit the local `.env` and set `ANTHROPIC_API_KEY`; do not commit it. Keep the
virtual environment activated for the `python` commands below. If PowerShell
activation is unavailable, use `.\.venv\Scripts\python.exe` in place of
`python` for installation and each workflow command; no execution-policy
change is required. Confirm that your selected Python interpreter is 3.11 or newer.

All retrieval APIs (Europe PMC, Open Targets, CIViC, ClinicalTrials.gov) are open access —
no additional keys needed.

## Experiment workflow

Three sequential steps, each reading the outputs of the previous:

```bash
python run_baseline.py      # System A: single LLM, one pass, writes outputs/baseline_<ts>.json
python run_multiagent.py    # System B: multi-agent pipeline, writes outputs/multiagent_<ts>.json
python run_evaluation.py    # Scores the LATEST baseline_*.json and multiagent_*.json in
                             # outputs/, blind to source, writes outputs/evaluation_<ts>.json/.md
```

Run size and shared model settings are controlled entirely by `src/config.py`
(`run_size`, `candidates_per_generator`, `model_name`, `temperature`, `max_agent_turns`) —
one file, read by both systems, per the project's fairness requirement.

**Cost note**: at `run_size=50`, a full pass of all three scripts is several hundred LLM
calls. Budget accordingly, or lower `run_size` for a cheap smoke test.

## Outputs

Each run produces:
- `outputs/<system>_<timestamp>.json` — structured result: valid hypotheses (with
  `system: "baseline"|"multiagent"`), dropped hypotheses/citations (with reasons),
  and the full set of retrieved sources.
- `outputs/evaluation_<timestamp>.json` / `.md` — the comparison: per-system metrics
  (hallucination rate, citation support, falsification survival, novelty, grounding
  depth) with Wilson-interval uncertainty, plus per-hypothesis judge/falsification detail.
- `logs/<run>_<timestamp>.jsonl` — every prompt, tool call, retrieval result, and
  intermediate hypothesis for that run, as its own JSONL research-data trace. Starts with a
  `run_config` line recording the exact model/settings used (added 2026-07-14 — see
  `RUN_MANIFEST.md` for how older runs, which predate this, were handled).

## Reproducibility

This project is **not bit-for-bit reproducible**: retrieval hits live APIs and generation
runs at `temperature=1.0`, so re-running will retrieve different sources and generate
different hypotheses even with identical code. What it is instead is fully *auditable*:

- **The logging system** (`src/logging_utils.py`) makes every run self-describing. Each
  run's `.jsonl` log begins with a `run_config` event recording the exact model, temperature,
  run size, and other settings used, followed by every prompt, tool call, and intermediate
  result — enough to reconstruct exactly what happened in that run, even though the run
  itself can't be replayed to get identical output.
- **`RUN_MANIFEST.json` / `RUN_MANIFEST.md`** exist because that logging capability was added
  partway through the project — runs before 2026-07-14 don't have a `run_config` line. The
  manifest retrospectively records, for every run behind the results in `RESULTS.md`, exactly
  what's known about the model/config/code state that produced it, with each fact tagged as
  either directly verified from that run's own log or source files, reconstructed from
  multiple corroborating sources (with the basis stated), or explicitly `unknown`. Nothing in
  it is asserted without a stated basis.
- **`REPRODUCIBILITY_NOTES.md`** explains the gap the manifest closes — why pre-2026-07-14
  runs weren't self-describing, why this project's lack of prior version-control history
  means some early-run metadata can't be recovered with certainty, and what's still a
  limitation going forward (still no automated versioning of `config.py` changes beyond git
  commits themselves).
- **Git**: this repository is version-controlled from 2026-07-14 onward. `logs/` is
  intentionally not tracked (28MB+ and growing; a size/repo-hygiene choice, not a privacy
  one — see `.gitignore`); it remains on disk as the primary research record and is
  referenced by path from `RUN_MANIFEST.json`.

## Known limitations

- **Sample size**: current results are at n≈50 hypotheses per system — real, but still a
  modest pilot. `RESULTS.md` documents at least one metric (citation support rate) whose
  direction reversed between the n=10 and n=50 runs, illustrating why gaps within each
  other's confidence interval shouldn't be over-read.
- **Baseline has no hard cap** on hypothesis count (it's asked for `run_size`, not enforced);
  the multi-agent system's ranking stage deterministically cuts to exactly `run_size`.
- **No patient-data/TCGA analysis** — out of scope for this build; a separate later phase
  per `CLAUDE.md`.
- **No git history before 2026-07-14** — see Reproducibility above.

## Reproducing the experiments

1. Follow Installation above.
2. Run the three scripts in order (`run_baseline.py`, `run_multiagent.py`,
   `run_evaluation.py`).
3. Compare your `outputs/evaluation_<timestamp>.md` against the tables in `RESULTS.md`.
   Exact numbers will differ (live retrieval + temperature=1.0); the qualitative pattern —
   near-zero hallucination for both systems, multi-agent's grounding-depth edge, low
   falsification survival for both — is what to look for, not exact reproduction.
4. For a cheap sanity check before a full run, temporarily lower `run_size` in
   `src/config.py` (e.g. to 5) — this reduces `candidates_per_generator` proportionally if
   you scale it too, and cuts the API cost substantially.

## Future Work

Not started, listed here as candidate directions rather than commitments:

- **Scale up further.** Confidence intervals are still fairly wide at n=50 for some metrics
  (e.g. citation support rate) — a larger run would narrow them.
- **Investigate System B's weaker metrics on their own merits.** Citation support rate was
  behind the baseline at n=50. The build brief explicitly cautions against tuning the
  multi-agent system just to win the comparison, so any changes here should be justified by
  what's actually wrong (e.g. a specific agent's prompt, not the scoreboard).
- **Patient-data / TCGA analysis** — a separate, later phase per `CLAUDE.md`, deliberately
  out of scope for this build.
- **Broader disease coverage.** The architecture (shared config, retrieval tools, evaluation
  harness) doesn't assume cholangiocarcinoma specifically; extending to other rare,
  late-diagnosed cancers would test whether the current findings generalize.

## License

No license has been selected or included in this public repository.

## Citation

*Citation information will be added following publication or preprint release.*
