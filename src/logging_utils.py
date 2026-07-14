"""Append-only JSONL run logging. Every prompt, tool call, retrieval, and
intermediate hypothesis is research data and must be kept, not just the final output."""
import json
import os
from datetime import datetime, timezone
from typing import Any


class RunLogger:
    def __init__(self, system: str, log_dir: str = "logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.run_id = f"{system}_{timestamp}"
        self.path = os.path.join(log_dir, f"{self.run_id}.jsonl")

        # Local import to avoid a config<->logging_utils import cycle. Every run (baseline,
        # multiagent, evaluation) goes through RunLogger, so logging this here — rather than
        # in each entry point — guarantees every log file is self-describing about which
        # model/settings produced it, without relying on each caller to remember to log it.
        from src.config import CONFIG

        self.log(
            "run_config",
            system=system,
            model_name=CONFIG.model_name,
            temperature=CONFIG.temperature,
            run_size=CONFIG.run_size,
            candidates_per_generator=CONFIG.candidates_per_generator,
            max_agent_turns=CONFIG.max_agent_turns,
            disease_context=CONFIG.disease_context,
            # api key deliberately excluded — logs are research data, not secrets storage
        )

    def log(self, event_type: str, **payload: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **payload,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
