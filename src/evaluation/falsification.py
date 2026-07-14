"""Independent falsification-survival check. Reuses the multi-agent system's own adversarial
agent logic, but run here by the harness itself, identically and blind to source, on
hypotheses from BOTH systems — including the baseline, which never got adversarial review
during generation. This is what makes falsification survival a fair cross-system metric."""
from typing import Any

import anthropic

from src.llm_client import SourceRegistry
from src.logging_utils import RunLogger
from src.multiagent.adversarial_agent import review_hypothesis
from src.schemas import Hypothesis


def check_falsification_survival(
    client: anthropic.Anthropic,
    registry: SourceRegistry,
    logger: RunLogger,
    hypothesis: Hypothesis,
) -> dict[str, Any]:
    as_dict = {
        "claim": hypothesis.claim,
        "reasoning": hypothesis.reasoning,
        "confidence": hypothesis.confidence,
        "supporting_evidence": hypothesis.supporting_evidence,
        "conflicting_evidence": hypothesis.conflicting_evidence,
    }
    reviewed = review_hypothesis(client, registry, logger, as_dict)

    # review_hypothesis merges the reviewer's claimed conflicting-evidence IDs directly;
    # independently re-validate them against the registry (now including this search's
    # own real retrievals) before trusting them, same discipline as the main pipeline.
    all_sources = registry.sources
    raw_new = [
        cid for cid in reviewed.get("conflicting_evidence", [])
        if cid not in hypothesis.conflicting_evidence
    ]
    valid_new = [cid for cid in raw_new if cid in all_sources]
    hallucinated_new = [cid for cid in raw_new if cid not in all_sources]

    return {
        "verdict": reviewed.get("adversarial_verdict", "unknown"),
        "reasoning": reviewed.get("adversarial_reasoning", ""),
        "new_conflicting_evidence": valid_new,
        "hallucinated_conflicting_evidence": hallucinated_new,
    }
