"""Shared Anthropic tool-use loop. Both System A and System B agents run through this
same loop, on the same model/config — only the prompts, tool sets, and orchestration
around it are allowed to differ."""
import json
from typing import Any, Callable

import anthropic

from src.config import CONFIG
from src.logging_utils import RunLogger
from src.schemas import Source


class SourceRegistry:
    """Accumulates every source actually returned by a real tool call this session.
    Anything not in here was never retrieved and cannot be cited."""

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}

    def register(self, sources: list[Source]) -> None:
        for s in sources:
            self._sources[s.id] = s

    @property
    def sources(self) -> dict[str, Source]:
        return dict(self._sources)

    def __len__(self) -> int:
        return len(self._sources)


def get_client() -> anthropic.Anthropic:
    if not CONFIG.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    # Pin to the public API explicitly — some shells (e.g. inside Claude Code) set
    # ANTHROPIC_BASE_URL for their own internal use, which the SDK would otherwise
    # inherit and use to route requests, causing auth failures against a personal key.
    return anthropic.Anthropic(
        api_key=CONFIG.anthropic_api_key, base_url="https://api.anthropic.com"
    )


def run_tool_loop(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    tools: list[dict[str, Any]],
    dispatch: Callable[[str, dict[str, Any]], list[Source]],
    submit_tool_name: str,
    logger: RunLogger,
    max_turns: int | None = None,
    registry: SourceRegistry | None = None,
) -> tuple[dict[str, Any] | None, SourceRegistry]:
    """Generic agentic tool-use loop: executes every retrieval tool call for real,
    accumulates a SourceRegistry, and stops as soon as the model calls submit_tool_name.
    Returns (submitted_input, registry); submitted_input is None if never submitted.

    Pass an existing `registry` to accumulate sources across multiple agent calls in the
    same run (e.g. the multi-agent system's several generator agents sharing one pool of
    real retrieved sources) — omit it to start a fresh one (e.g. the single-pass baseline)."""
    max_turns = max_turns or CONFIG.max_agent_turns
    registry = registry if registry is not None else SourceRegistry()
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    logger.log("agent_start", system_prompt=system_prompt, user_prompt=user_prompt)

    for turn in range(max_turns):
        response = client.messages.create(
            model=CONFIG.model_name,
            max_tokens=16000,
            temperature=CONFIG.temperature,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        logger.log(
            "model_response",
            turn=turn,
            stop_reason=response.stop_reason,
            content=[block.model_dump() for block in response.content],
        )

        if response.stop_reason == "max_tokens":
            # Response (often a long thinking block) got cut off mid-generation — any
            # tool_use input may be truncated/incomplete (we've seen this silently produce
            # an empty {} for submit_hypotheses). Don't append it to history — a dangling
            # tool_use with no tool_result would break the next API call anyway — just
            # retry the identical turn rather than trusting a possibly-malformed payload.
            logger.log("agent_truncated_retry", turn=turn)
            continue

        messages.append({"role": "assistant", "content": response.content})

        submitted_input: dict[str, Any] | None = None
        tool_result_blocks: list[dict[str, Any]] = []

        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == submit_tool_name:
                submitted_input = block.input
                continue
            try:
                sources = dispatch(block.name, block.input)
                registry.register(sources)
                result_payload: Any = [s.model_dump() for s in sources]
                logger.log(
                    "tool_call",
                    turn=turn,
                    tool_name=block.name,
                    tool_input=block.input,
                    result_count=len(sources),
                    results=result_payload,
                )
            except Exception as e:
                logger.log(
                    "tool_call_error",
                    turn=turn,
                    tool_name=block.name,
                    tool_input=block.input,
                    error=str(e),
                )
                result_payload = {"error": str(e)}

            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result_payload),
                }
            )

        if submitted_input is not None:
            logger.log("agent_submit", turn=turn, submitted=submitted_input)
            return submitted_input, registry

        if not tool_result_blocks:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Please continue gathering evidence with the search tools, then call "
                        f"'{submit_tool_name}' with your final hypotheses."
                    ),
                }
            )
            continue

        messages.append({"role": "user", "content": tool_result_blocks})

    logger.log("agent_max_turns_reached", max_turns=max_turns)
    return None, registry


def run_single_tool_call(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    tool: dict[str, Any],
    logger: RunLogger,
    event_prefix: str = "single_call",
    max_retries: int = 3,
) -> dict[str, Any]:
    """One-shot forced tool call, no retrieval loop. For agents (e.g. ranking, judging) that
    reason over evidence already gathered rather than retrieving anything new."""
    logger.log(f"{event_prefix}_start", system_prompt=system_prompt, user_prompt=user_prompt)

    for attempt in range(max_retries):
        response = client.messages.create(
            model=CONFIG.model_name,
            max_tokens=16000,
            temperature=CONFIG.temperature,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user_prompt}],
        )
        logger.log(
            f"{event_prefix}_response",
            attempt=attempt,
            stop_reason=response.stop_reason,
            content=[block.model_dump() for block in response.content],
        )
        if response.stop_reason == "max_tokens":
            # Truncated mid-generation — the tool input may be incomplete. Retry rather
            # than trust a possibly-malformed payload.
            logger.log(f"{event_prefix}_truncated_retry", attempt=attempt)
            continue
        for block in response.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                return block.input

    raise RuntimeError(
        f"Model did not produce a complete call to {tool['name']} within {max_retries} attempts"
    )
