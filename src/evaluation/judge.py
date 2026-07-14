"""Blind evaluation judge: checks whether each supporting citation actually supports its
claim, and rates novelty vs. triviality. Runs identically on hypotheses from both systems
and is never told which system produced the hypothesis it is looking at."""
from typing import Any

import anthropic

from src.llm_client import run_single_tool_call
from src.logging_utils import RunLogger
from src.schemas import Hypothesis, Source

SUBMIT_JUDGMENT_TOOL: dict[str, Any] = {
    "name": "submit_judgment",
    "description": "Submit your blind evaluation of this single hypothesis.",
    "input_schema": {
        "type": "object",
        "properties": {
            "citation_checks": {
                "type": "array",
                "description": "One entry for every supporting citation shown to you, in the same order.",
                "items": {
                    "type": "object",
                    "properties": {
                        "citation_id": {"type": "string"},
                        "supports_claim": {
                            "type": "string",
                            "enum": ["yes", "partially", "no"],
                            "description": "yes = directly supports the specific claim; partially = related but doesn't fully establish it; no = does not support it",
                        },
                        "reasoning": {"type": "string"},
                    },
                    "required": ["citation_id", "supports_claim", "reasoning"],
                },
            },
            "novelty": {
                "type": "string",
                "enum": ["trivial_restatement", "non_obvious"],
                "description": (
                    "trivial_restatement for hypotheses that mainly restate well-known facts "
                    "(e.g. 'FGFR2 fusions are a therapeutic target', 'IDH1 mutations occur in "
                    "cholangiocarcinoma'); non_obvious for genuinely non-trivial proposals or "
                    "combinations a researcher wouldn't already take for granted."
                ),
            },
            "novelty_reasoning": {"type": "string"},
        },
        "required": ["citation_checks", "novelty", "novelty_reasoning"],
    },
}

SYSTEM_PROMPT = """You are an independent, blinded evaluator of early-detection research \
hypotheses for cholangiocarcinoma. You do not know, and must not try to guess, which system \
produced this hypothesis — judge it purely on its own merits.

For each supporting citation given, read the actual retrieved source text and judge whether it \
genuinely supports the specific claim being made (not just topically related to the same \
disease or gene): "yes" (directly supports), "partially" (related but doesn't fully establish \
the claim), or "no" (does not support it).

Then judge novelty: is this hypothesis mainly a restatement of a well-established fact (e.g. \
"FGFR2 fusions are targetable in cholangiocarcinoma", "IDH1 mutations occur in a subset of \
CCA"), or a genuinely non-obvious proposal or combination? Do not let writing quality, length, \
or confident tone affect either judgment — evaluate only the substance."""


def _format_hypothesis(hypothesis: Hypothesis, sources: dict[str, Source]) -> str:
    lines = [
        f"Claim: {hypothesis.claim}",
        f"Reasoning given: {hypothesis.reasoning}",
        "",
        "Supporting citations:",
    ]
    if not hypothesis.supporting_evidence:
        lines.append("  (none)")
    for cid in hypothesis.supporting_evidence:
        src = sources.get(cid)
        if src:
            lines.append(f"  [{cid}] {src.title}\n      {src.snippet[:600]}")
        else:
            lines.append(f"  [{cid}] (source text unavailable)")
    return "\n".join(lines)


def judge_hypothesis(
    client: anthropic.Anthropic,
    logger: RunLogger,
    hypothesis: Hypothesis,
    sources: dict[str, Source],
) -> dict[str, Any]:
    user_prompt = _format_hypothesis(hypothesis, sources)
    submitted = run_single_tool_call(
        client=client,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        tool=SUBMIT_JUDGMENT_TOOL,
        logger=logger,
        event_prefix="judge",
    )
    logger.log("judge_result", claim=hypothesis.claim, judgment=submitted)
    return submitted
