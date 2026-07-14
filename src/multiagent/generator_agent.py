"""Shared runner for the three domain-generator agents (literature, molecular, signal).
Each is the same tool-use loop and the same model/temperature/tool access as every other
agent and the baseline — only the role and system prompt differ."""
import json
from typing import Any

import anthropic
from pydantic import ValidationError

from src.llm_client import SourceRegistry, run_tool_loop
from src.logging_utils import RunLogger
from src.schemas import RawHypothesis
from src.tools import RETRIEVAL_TOOLS, SUBMIT_HYPOTHESES_TOOL, dispatch_tool_call


def run_generator(
    client: anthropic.Anthropic,
    registry: SourceRegistry,
    logger: RunLogger,
    role: str,
    system_prompt: str,
    user_prompt: str,
) -> list[dict[str, Any]]:
    tools = RETRIEVAL_TOOLS + [SUBMIT_HYPOTHESES_TOOL]
    submitted, _ = run_tool_loop(
        client=client,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=tools,
        dispatch=dispatch_tool_call,
        submit_tool_name="submit_hypotheses",
        logger=logger,
        registry=registry,
    )

    if submitted is None:
        logger.log("generator_no_submission", role=role)
        return []

    raw_items = submitted.get("hypotheses", [])
    if isinstance(raw_items, str):
        # Model occasionally stringifies the whole array instead of nesting real JSON —
        # iterating a string yields one "item" per character, so parse it explicitly first.
        try:
            raw_items = json.loads(raw_items)
        except json.JSONDecodeError as e:
            logger.log("generator_hypotheses_unparseable", role=role, raw=raw_items[:2000], error=str(e))
            raw_items = []
    if not isinstance(raw_items, list):
        logger.log("generator_hypotheses_wrong_type", role=role, raw_type=type(raw_items).__name__)
        raw_items = []

    candidates: list[dict[str, Any]] = []
    for item in raw_items:
        try:
            validated = RawHypothesis.model_validate(item)
        except ValidationError as e:
            logger.log("generator_malformed_hypothesis", role=role, item=item, error=str(e))
            continue
        candidates.append({**validated.model_dump(), "origin_agent": role})

    logger.log(
        "generator_candidates", role=role, count=len(candidates), raw_count=len(raw_items)
    )
    return candidates
