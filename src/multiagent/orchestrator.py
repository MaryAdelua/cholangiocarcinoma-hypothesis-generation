"""System B — deterministic orchestrator. Wires literature, molecular, and signal generator
agents into a shared source registry, runs the adversarial agent over every candidate, then
the ranking agent, then trims to the top run_size deterministically. Every agent call runs
through the same shared model/temperature/tools as System A — only this architecture differs."""
import os

from src.config import CONFIG
from src.llm_client import SourceRegistry, get_client
from src.logging_utils import RunLogger
from src.multiagent import literature_agent, molecular_agent, signal_agent
from src.multiagent.adversarial_agent import review_hypothesis
from src.multiagent.generator_agent import run_generator
from src.multiagent.ranking_agent import rank_and_select
from src.schemas import RawHypothesis, RunResult
from src.validation import validate_hypotheses


def run_multiagent() -> RunResult:
    logger = RunLogger(system="multiagent")
    client = get_client()
    registry = SourceRegistry()

    n = CONFIG.candidates_per_generator
    logger.log("orchestrator_start", candidates_per_generator=n, run_size=CONFIG.run_size)

    candidates = []
    candidates += run_generator(
        client,
        registry,
        logger,
        literature_agent.ROLE,
        literature_agent.SYSTEM_PROMPT,
        literature_agent.user_prompt(n),
    )
    candidates += run_generator(
        client,
        registry,
        logger,
        molecular_agent.ROLE,
        molecular_agent.SYSTEM_PROMPT,
        molecular_agent.user_prompt(n),
    )
    candidates += run_generator(
        client,
        registry,
        logger,
        signal_agent.ROLE,
        signal_agent.SYSTEM_PROMPT,
        signal_agent.user_prompt(n),
    )
    logger.log("orchestrator_generation_complete", total_candidates=len(candidates))

    reviewed = [review_hypothesis(client, registry, logger, c) for c in candidates]
    logger.log("orchestrator_adversarial_complete", reviewed_count=len(reviewed))

    selected = rank_and_select(client, logger, reviewed, CONFIG.run_size)
    logger.log("orchestrator_ranking_complete", selected_count=len(selected))

    raw_hypotheses = [
        RawHypothesis(
            claim=c["claim"],
            supporting_evidence=c.get("supporting_evidence", []),
            conflicting_evidence=c.get("conflicting_evidence", []),
            confidence=c["confidence"],
            reasoning=c["reasoning"],
        )
        for c in selected
    ]
    valid, dropped_hyps, dropped_citations = validate_hypotheses(
        raw_hypotheses, registry.sources, system="multiagent"
    )

    logger.log(
        "validation_summary",
        raw_count=len(raw_hypotheses),
        valid_count=len(valid),
        dropped_hypothesis_count=len(dropped_hyps),
        dropped_citation_count=len(dropped_citations),
        retrieved_source_count=len(registry),
    )

    result = RunResult(
        system="multiagent",
        hypotheses=valid,
        dropped_hypotheses=dropped_hyps,
        dropped_citations=dropped_citations,
        retrieved_source_count=len(registry),
        run_id=logger.run_id,
        retrieved_sources=registry.sources,
    )

    os.makedirs("outputs", exist_ok=True)
    out_path = os.path.join("outputs", f"{logger.run_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    print(
        f"Multi-agent run complete: {len(valid)} valid hypotheses (selected from "
        f"{len(candidates)} candidates), {len(dropped_hyps)} dropped (no valid supporting "
        f"evidence), {len(dropped_citations)} citations dropped."
    )
    print(f"Output: {out_path}")
    print(f"Log: {logger.path}")

    return result


if __name__ == "__main__":
    run_multiagent()
