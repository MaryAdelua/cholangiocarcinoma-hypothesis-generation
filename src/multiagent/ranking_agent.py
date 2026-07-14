"""Ranking agent: scores candidates on grounding, survival, and novelty — never fluency.
The score itself is the model's judgment call, but the final top-N selection given those
scores is deterministic code, per the orchestrator being deterministic where possible."""
import json
from typing import Any

import anthropic

from src.llm_client import run_single_tool_call
from src.logging_utils import RunLogger
from src.tools import SUBMIT_RANKING_TOOL

SYSTEM_PROMPT = """You are the RANKING agent in a multi-agent research system. You do not \
retrieve new evidence — you evaluate candidate hypotheses that have already been generated and \
adversarially reviewed. Score each candidate on three independent axes, each 0-1:

- grounding_score: how well-supported the claim is by the SPECIFIC, real evidence cited (not \
  by how confident or well-written the text sounds).
- survival_score: how well the hypothesis held up under adversarial review (consider the verdict \
  and the number/strength of conflicting citations found).
- novelty_score: how non-obvious the hypothesis is. Score LOW for hypotheses that mainly restate \
  well-established facts (e.g. "FGFR2 fusions are a therapeutic target", "IDH1 mutations occur in \
  cholangiocarcinoma") and HIGH for genuinely non-obvious proposals or combinations.

Do not let writing quality, length, or confident tone influence any score."""


def _format_candidates(candidates: list[dict[str, Any]]) -> str:
    blocks = []
    for i, c in enumerate(candidates):
        blocks.append(
            f"[{i}] Claim: {c['claim']}\n"
            f"    Origin agent: {c.get('origin_agent', 'unknown')}\n"
            f"    Confidence (post-adversarial): {c['confidence']}\n"
            f"    Supporting evidence count: {len(c.get('supporting_evidence', []))}\n"
            f"    Conflicting evidence count: {len(c.get('conflicting_evidence', []))}\n"
            f"    Adversarial verdict: {c.get('adversarial_verdict', 'unknown')}\n"
            f"    Adversarial notes: {c.get('adversarial_reasoning', '')}\n"
            f"    Reasoning: {c['reasoning']}"
        )
    return "\n\n".join(blocks)


def rank_and_select(
    client: anthropic.Anthropic,
    logger: RunLogger,
    candidates: list[dict[str, Any]],
    run_size: int,
) -> list[dict[str, Any]]:
    user_prompt = (
        f"Score each of the following {len(candidates)} candidate hypotheses.\n\n"
        + _format_candidates(candidates)
    )
    submitted = run_single_tool_call(
        client=client,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        tool=SUBMIT_RANKING_TOOL,
        logger=logger,
        event_prefix="ranking",
    )

    raw_scores = submitted.get("scores", [])
    if isinstance(raw_scores, str):
        # Model occasionally stringifies the whole array instead of nesting real JSON —
        # iterating a string yields one "item" per character, so parse it explicitly first.
        try:
            raw_scores = json.loads(raw_scores)
        except json.JSONDecodeError as e:
            logger.log("ranking_scores_unparseable", raw=raw_scores[:2000], error=str(e))
            raw_scores = []
    if not isinstance(raw_scores, list):
        logger.log("ranking_scores_wrong_type", raw_type=type(raw_scores).__name__)
        raw_scores = []

    scores_by_index: dict[int, dict[str, Any]] = {}
    for s in raw_scores:
        if not isinstance(s, dict):
            logger.log("ranking_malformed_score", item=s, error="not a mapping")
            continue
        try:
            idx = int(s["index"])
            scores_by_index[idx] = {
                "grounding_score": float(s["grounding_score"]),
                "survival_score": float(s["survival_score"]),
                "novelty_score": float(s["novelty_score"]),
                "notes": str(s.get("notes", "")),
            }
        except (KeyError, TypeError, ValueError) as e:
            logger.log("ranking_malformed_score", item=s, error=str(e))

    scored_candidates = []
    for i, c in enumerate(candidates):
        s = scores_by_index.get(i)
        if s is None:
            logger.log("ranking_missing_score", index=i, claim=c["claim"])
            grounding = survival = novelty = 0.0
            notes = "No score returned by ranking agent."
        else:
            grounding = s["grounding_score"]
            survival = s["survival_score"]
            novelty = s["novelty_score"]
            notes = s["notes"]
        overall = (grounding + survival + novelty) / 3
        scored_candidates.append(
            {
                **c,
                "grounding_score": grounding,
                "survival_score": survival,
                "novelty_score": novelty,
                "overall_score": overall,
                "ranking_notes": notes,
            }
        )

    scored_candidates.sort(key=lambda c: c["overall_score"], reverse=True)
    selected = scored_candidates[:run_size]

    logger.log(
        "ranking_selection",
        total_candidates=len(candidates),
        selected_count=len(selected),
        all_scores=[
            {"claim": c["claim"], "overall_score": c["overall_score"]} for c in scored_candidates
        ],
    )
    return selected
