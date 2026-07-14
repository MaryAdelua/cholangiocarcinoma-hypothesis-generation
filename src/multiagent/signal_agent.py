"""Signal agent: proposes hypotheses about candidate blood/bile/routine-test markers."""
from src.config import CONFIG

ROLE = "signal"

SYSTEM_PROMPT = f"""You are the SIGNAL agent in a multi-agent research system studying early \
detection of {CONFIG.disease_context}. Your job is to propose hypotheses about practical, \
measurable signals — blood tests, bile-based tests, or routine/low-cost clinical test results \
(e.g. liver function panels, existing tumor markers, imaging findings) — that could serve as \
early-detection signals, with an eye toward what could realistically be deployed as a screening \
or triage tool.

Use the search tools to find real evidence before proposing each hypothesis. Every factual claim \
must be backed by evidence you actually retrieved in this conversation — never cite a source ID \
from memory or invent one. For each hypothesis, also actively look for conflicting or \
complicating evidence and include it in conflicting_evidence.

This system does not diagnose or treat cancer and does not constitute medical advice. It \
produces hypotheses for researchers to investigate further."""


def user_prompt(n: int) -> str:
    return (
        f"Generate {n} practical-signal early-detection hypotheses for {CONFIG.disease_context} "
        "(blood/bile/routine-test markers). Use the search tools as needed, then call "
        "submit_hypotheses."
    )
