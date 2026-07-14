"""Single shared config for both systems. Do not fork model/temperature per-system —
the brief requires the baseline and every multi-agent role to run on identical settings."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    model_name: str = "claude-sonnet-5"
    temperature: float = 1.0
    run_size: int = 50  # final hypotheses per system
    max_agent_turns: int = 15  # tool-use loop cap per agent call
    candidates_per_generator: int = 25  # multiagent: 3 generators x 25 = 75 candidates before ranking trims to run_size
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    disease_context: str = "cholangiocarcinoma"


CONFIG = Config()
