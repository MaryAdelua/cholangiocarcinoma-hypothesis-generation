"""Adversarial agent — the heart of the multi-agent contribution. Reviews ONE hypothesis
at a time and actively searches for disconfirming evidence, rather than validating what a
generator agent already found. Same model, temperature, and tool access as every other
agent and the baseline."""
import json
from typing import Any

import anthropic

from src.config import CONFIG
from src.llm_client import SourceRegistry, run_tool_loop
from src.logging_utils import RunLogger
from src.tools import RETRIEVAL_TOOLS, SUBMIT_ADVERSARIAL_REVIEW_TOOL, dispatch_tool_call

SYSTEM_PROMPT = f"""You are the ADVERSARIAL agent in a multi-agent research system studying \
early detection of {CONFIG.disease_context}. You review ONE hypothesis at a time. Your only \
job is to try to disprove, weaken, or complicate it using REAL evidence you retrieve with the \
search tools — negative studies, contradicting results, confounders, poor sensitivity/specificity \
findings, failed trials, or reasons the proposed marker or mechanism would not work in practice.

Be genuinely skeptical, not a rubber stamp. But also be honest: if after a real search you find \
no meaningful disconfirming evidence, say so and mark verdict as "survives" rather than \
manufacturing a weakness. Never cite a source ID from memory or invent one — only use IDs \
exactly as returned by a tool call in this conversation.

When you are done searching, call submit_adversarial_review."""


def _format_hypothesis_context(hypothesis: dict[str, Any], registry: SourceRegistry) -> str:
    sources = registry.sources
    lines = [
        f"Claim: {hypothesis['claim']}",
        f"Reasoning given: {hypothesis['reasoning']}",
        f"Original confidence: {hypothesis['confidence']}",
        "Supporting evidence already cited:",
    ]
    for sid in hypothesis.get("supporting_evidence", []):
        src = sources.get(sid)
        if src:
            lines.append(f"  - {sid}: {src.title} — {src.snippet[:200]}")
        else:
            lines.append(f"  - {sid} (source text unavailable)")
    return "\n".join(lines)


def review_hypothesis(
    client: anthropic.Anthropic,
    registry: SourceRegistry,
    logger: RunLogger,
    hypothesis: dict[str, Any],
) -> dict[str, Any]:
    tools = RETRIEVAL_TOOLS + [SUBMIT_ADVERSARIAL_REVIEW_TOOL]
    user_prompt = (
        "Try to find real evidence that disconfirms, weakens, or complicates this hypothesis:\n\n"
        + _format_hypothesis_context(hypothesis, registry)
    )
    submitted, _ = run_tool_loop(
        client=client,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        tools=tools,
        dispatch=dispatch_tool_call,
        submit_tool_name="submit_adversarial_review",
        logger=logger,
        registry=registry,
    )

    updated = dict(hypothesis)
    if submitted is None:
        logger.log("adversarial_no_submission", claim=hypothesis["claim"])
        updated["adversarial_verdict"] = "unknown"
        updated["adversarial_reasoning"] = "Adversarial agent did not complete review."
        return updated

    new_conflicting = submitted.get("additional_conflicting_evidence", [])
    if isinstance(new_conflicting, str):
        # Model occasionally stringifies the whole array instead of nesting real JSON;
        # try to parse it as one before falling back to treating it as a single bare ID.
        try:
            parsed = json.loads(new_conflicting)
            new_conflicting = parsed if isinstance(parsed, list) else [new_conflicting]
        except json.JSONDecodeError:
            new_conflicting = [new_conflicting] if new_conflicting else []
    if not isinstance(new_conflicting, list):
        new_conflicting = []
    new_conflicting = [c for c in new_conflicting if isinstance(c, str)]
    updated["conflicting_evidence"] = list(
        dict.fromkeys(list(hypothesis.get("conflicting_evidence", [])) + new_conflicting)
    )
    updated["adversarial_verdict"] = submitted.get("verdict", "unknown")
    updated["adversarial_reasoning"] = submitted.get("verdict_reasoning", "")
    if "revised_confidence" in submitted:
        updated["confidence"] = submitted["revised_confidence"]

    logger.log(
        "adversarial_review",
        claim=hypothesis["claim"],
        verdict=updated["adversarial_verdict"],
        new_conflicting_count=len(new_conflicting),
        revised_confidence=updated["confidence"],
    )
    return updated
