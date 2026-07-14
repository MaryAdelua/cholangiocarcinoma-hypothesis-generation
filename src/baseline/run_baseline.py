"""System A — single-LLM baseline. One pass: same model and same retrieval tools as the
multi-agent system, but no multi-agent orchestration. Built first per the build brief."""
import json
import os

from pydantic import ValidationError

from src.config import CONFIG
from src.llm_client import get_client, run_tool_loop
from src.logging_utils import RunLogger
from src.schemas import RawHypothesis, RunResult
from src.tools import RETRIEVAL_TOOLS, SUBMIT_HYPOTHESES_TOOL, dispatch_tool_call
from src.validation import validate_hypotheses

SYSTEM_PROMPT = f"""You are a research assistant generating early-detection hypotheses for \
{CONFIG.disease_context}, a cancer with poor prognosis largely due to late diagnosis.

Your task: propose {CONFIG.run_size} distinct, specific hypotheses about signals, markers, \
mechanisms, or approaches that could help detect {CONFIG.disease_context} earlier than current \
practice. Use the search tools to find real evidence before proposing each hypothesis.

Rules you MUST follow:
- Every factual claim must be backed by evidence you actually retrieved via the search tools \
in this conversation. Never cite a source ID from memory or invent one — only use IDs exactly \
as returned by a tool call.
- For each hypothesis, actively look for both supporting AND conflicting evidence. If you find \
evidence that complicates or contradicts a hypothesis, include it in conflicting_evidence rather \
than dropping the hypothesis.
- Prefer specific, checkable claims over vague ones. Note where a hypothesis would be a novel \
combination or application versus a well-established fact.
- Assign confidence (0-1) reflecting how well-grounded the hypothesis is in the evidence you found.
- This system does not diagnose or treat cancer and does not constitute medical advice. It \
produces hypotheses for researchers to investigate further.

When you have gathered enough evidence, call submit_hypotheses with your final list."""

USER_PROMPT = (
    f"Generate {CONFIG.run_size} early-detection hypotheses for {CONFIG.disease_context}. "
    "Use the search tools as needed before submitting."
)


def run_baseline() -> RunResult:
    logger = RunLogger(system="baseline")
    client = get_client()

    tools = RETRIEVAL_TOOLS + [SUBMIT_HYPOTHESES_TOOL]
    submitted, registry = run_tool_loop(
        client=client,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=USER_PROMPT,
        tools=tools,
        dispatch=dispatch_tool_call,
        submit_tool_name="submit_hypotheses",
        logger=logger,
    )

    if submitted is None:
        raise RuntimeError(
            f"Baseline run did not submit hypotheses within {CONFIG.max_agent_turns} turns. "
            f"See log: {logger.path}"
        )

    raw_items = submitted.get("hypotheses", [])
    if isinstance(raw_items, str):
        # Model occasionally stringifies the whole array instead of nesting real JSON —
        # iterating a string yields one "item" per character, so parse it explicitly first.
        try:
            raw_items = json.loads(raw_items)
        except json.JSONDecodeError as e:
            logger.log("baseline_hypotheses_unparseable", raw=raw_items[:2000], error=str(e))
            raw_items = []
    if not isinstance(raw_items, list):
        logger.log("baseline_hypotheses_wrong_type", raw_type=type(raw_items).__name__)
        raw_items = []

    raw_hypotheses: list[RawHypothesis] = []
    for item in raw_items:
        try:
            raw_hypotheses.append(RawHypothesis.model_validate(item))
        except ValidationError as e:
            logger.log("baseline_malformed_hypothesis", item=item, error=str(e))

    valid, dropped_hyps, dropped_citations = validate_hypotheses(
        raw_hypotheses, registry.sources, system="baseline"
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
        system="baseline",
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
        f"Baseline run complete: {len(valid)} valid hypotheses, {len(dropped_hyps)} dropped "
        f"(no valid supporting evidence), {len(dropped_citations)} citations dropped."
    )
    print(f"Output: {out_path}")
    print(f"Log: {logger.path}")

    return result


if __name__ == "__main__":
    run_baseline()
