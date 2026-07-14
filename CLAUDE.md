# Step-Two Build Brief: Multi-Agent vs Single-LLM Hypothesis System (Cholangiocarcinoma)

## Read this first

This is a research instrument, not a product. Its only job is to answer one question honestly: **Does a multi-agent system generate early-detection hypotheses for cholangiocarcinoma that are better grounded in real evidence and more resistant to falsification than a single LLM with the same tools?**

The evaluation is the point, not the systems. The systems exist to be measured. Do NOT optimize the multi-agent system to "win." Build a fair comparison and report whatever it shows, including the multi-agent system losing or tying.

This brief covers ONLY step two: the two systems plus the evaluation harness. Do NOT build any patient-data/TCGA analysis — that is a separate later brief.

## The most important rules

- **Fair comparison**: the single-LLM baseline and every agent in the multi-agent system must run on the same underlying model via the same API. The ONLY thing that differs between the two systems is the architecture (single pass vs. multi-agent), never the model, temperature, or tool access.
- **Real citations only, enforced in code**: every factual claim in a hypothesis must carry an ID from a real source retrieved from a real API. If a claim has no valid retrieved source, it is dropped before scoring. Never let the model cite from memory.
- **Build small end-to-end first**: get the whole loop working on ~10 hypotheses before expanding anything. Prove the pipeline works end-to-end, THEN scale up.

## Data sources (facts come only from here)

PubMed / Europe PMC API (literature); Open Targets and CIViC (genes, variants, drug targets); ClinicalTrials.gov API (trials). All open access. Each retrieved item keeps its source ID and the text snippet it came from.

## The shared hypothesis object

Both systems output hypotheses in the SAME structured format:
- `claim`
- `supporting_evidence` (list of source IDs)
- `conflicting_evidence` (list of source IDs)
- `confidence` (0-1)
- `reasoning`
- `system` ("baseline" or "multiagent")

## System A — single-LLM baseline

One pass to the shared model, given the same retrieval tools, asked to generate early-detection hypotheses for cholangiocarcinoma, each with supporting and conflicting evidence from real retrieved sources. **Build this FIRST.**

## System B — multi-agent system

Agents that pass hypothesis objects (not free-text chatter), same model behind each:
- **literature agent**
- **molecular agent** (genes, mutations, methylation, pathways)
- **signal agent** (candidate blood/bile/routine-test markers)
- **adversarial agent** (for each hypothesis, actively searches for disconfirming evidence — build this most carefully, it is the heart of the contribution)
- **ranking agent** (scores on grounding, survival, novelty — not fluency)
- **orchestrator** (deterministic where possible; logs every step)

## The evaluation harness (the actual research)

Run both systems on the same task. Score every hypothesis, blind to source where possible. Metrics:

1. **Citation validity** — does each cited source exist AND support the claim; report a per-system hallucinated-citation rate
2. **Falsification survival** — fraction surviving an independent adversarial evidence search, run the SAME on both systems
3. **Novelty vs. triviality** — flag restatements of known facts (FGFR2 fusions, IDH1) vs. non-obvious proposals
4. **Grounding depth** — average valid supporting sources per hypothesis

Output a clean comparison table with counts and simple uncertainty; this is a small run, report n, don't over-interpret small gaps.

## Discipline (do not skip)

- Log everything (prompts, retrievals, source IDs, intermediate hypotheses) — the logs are research data.
- Do NOT tune until the multi-agent system wins; run the honest comparison and report it.
- Keep it inspectable over clever.
- The system produces hypotheses for researchers to investigate; it does not detect cancer or give medical advice — state this in outputs.

## Tech notes

- Python throughout.
- One config file holding: model name (shared by both systems), temperature, run size.
- Start with run size ~10 hypotheses per system to prove the loop, then scale.
- **Deliverable**: both systems, the evaluation harness, the comparison table, and full logs.

---

## Working agreement with Claude

- Ask permission before installing anything or making big changes.
- Do not install anything or write code until explicitly told "go."
- When building starts: build ONLY a small end-to-end version first — about 10 hypotheses, both systems (baseline and multi-agent), and the evaluation running.
