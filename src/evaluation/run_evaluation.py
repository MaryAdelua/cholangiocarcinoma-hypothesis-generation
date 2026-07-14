"""Evaluation harness entry point — the actual research instrument. Loads the most recent
baseline and multiagent run outputs, scores every hypothesis blind to source, and produces
a comparison table. The systems exist to be measured by this; do not tune this file to make
either system look better."""
import glob
import json
import os
import random

from src.evaluation.falsification import check_falsification_survival
from src.evaluation.judge import judge_hypothesis
from src.evaluation.metrics import (
    EvaluationReport,
    HypothesisEvaluation,
    aggregate_system_evaluation,
    render_comparison_table,
)
from src.llm_client import SourceRegistry, get_client
from src.logging_utils import RunLogger
from src.schemas import RunResult

SHUFFLE_SEED = 42


def _latest_output(system: str) -> str:
    matches = sorted(glob.glob(os.path.join("outputs", f"{system}_*.json")))
    if not matches:
        raise FileNotFoundError(f"No outputs/{system}_*.json found. Run run_{system}.py first.")
    return matches[-1]


def _load_run_result(path: str) -> RunResult:
    with open(path, encoding="utf-8") as f:
        return RunResult.model_validate(json.load(f))


def run_evaluation() -> EvaluationReport:
    logger = RunLogger(system="evaluation")
    client = get_client()

    baseline_path = _latest_output("baseline")
    multiagent_path = _latest_output("multiagent")
    baseline_result = _load_run_result(baseline_path)
    multiagent_result = _load_run_result(multiagent_path)
    logger.log(
        "evaluation_start",
        baseline_run=baseline_path,
        multiagent_run=multiagent_path,
        baseline_n=len(baseline_result.hypotheses),
        multiagent_n=len(multiagent_result.hypotheses),
    )

    # Shuffle system/hypothesis pairs together so nothing about processing order hints at
    # which system produced which hypothesis (defense in depth — the judge/falsification
    # prompts themselves never mention "system" either).
    queue = [("baseline", h) for h in baseline_result.hypotheses] + [
        ("multiagent", h) for h in multiagent_result.hypotheses
    ]
    random.Random(SHUFFLE_SEED).shuffle(queue)

    sources_by_system = {
        "baseline": baseline_result.retrieved_sources,
        "multiagent": multiagent_result.retrieved_sources,
    }

    # Falsification search shares ONE registry across both systems, seeded with everything
    # already retrieved by either system, so the reviewer has real context for existing
    # citations and any new searches accumulate into the same real-evidence pool.
    shared_registry = SourceRegistry()
    shared_registry.register(list(baseline_result.retrieved_sources.values()))
    shared_registry.register(list(multiagent_result.retrieved_sources.values()))

    judge_by_system: dict[str, list[dict]] = {"baseline": [], "multiagent": []}
    falsification_by_system: dict[str, list[dict]] = {"baseline": [], "multiagent": []}
    per_hypothesis: list[HypothesisEvaluation] = []

    for i, (system, hypothesis) in enumerate(queue):
        logger.log(
            "evaluation_progress", index=i, total=len(queue), system=system, claim=hypothesis.claim
        )
        judgment = judge_hypothesis(client, logger, hypothesis, sources_by_system[system])
        judge_by_system[system].append(judgment)

        falsification = check_falsification_survival(client, shared_registry, logger, hypothesis)
        falsification_by_system[system].append(falsification)

        per_hypothesis.append(
            HypothesisEvaluation(
                system=system,
                claim=hypothesis.claim,
                citation_checks=judgment.get("citation_checks", []),
                novelty=judgment.get("novelty", "unknown"),
                novelty_reasoning=judgment.get("novelty_reasoning", ""),
                falsification_verdict=falsification["verdict"],
                falsification_reasoning=falsification["reasoning"],
                new_conflicting_evidence=falsification["new_conflicting_evidence"],
            )
        )

    baseline_eval = aggregate_system_evaluation(
        "baseline",
        baseline_result,
        judge_by_system["baseline"],
        falsification_by_system["baseline"],
    )
    multiagent_eval = aggregate_system_evaluation(
        "multiagent",
        multiagent_result,
        judge_by_system["multiagent"],
        falsification_by_system["multiagent"],
    )

    table = render_comparison_table([baseline_eval, multiagent_eval])

    report = EvaluationReport(
        run_ids={"baseline": baseline_result.run_id, "multiagent": multiagent_result.run_id},
        system_evaluations=[baseline_eval, multiagent_eval],
        per_hypothesis=per_hypothesis,
        comparison_table_markdown=table,
    )

    logger.log("evaluation_complete", run_id=logger.run_id)

    os.makedirs("outputs", exist_ok=True)
    out_json = os.path.join("outputs", f"{logger.run_id}.json")
    with open(out_json, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    out_md = os.path.join("outputs", f"{logger.run_id}.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(table + "\n")

    print(table)
    print()
    print(f"Full report: {out_json}")
    print(f"Table: {out_md}")
    print(f"Log: {logger.path}")

    return report


if __name__ == "__main__":
    run_evaluation()
