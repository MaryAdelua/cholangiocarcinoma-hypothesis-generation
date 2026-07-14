"""Pure aggregation: turns per-hypothesis judge/falsification results plus each system's
RunResult into the four brief-mandated metrics, with simple uncertainty (Wilson intervals —
appropriate and conservative for small n, not a fancier method that would overstate precision).
No LLM calls happen in this file."""
from typing import Any, Literal

from pydantic import BaseModel

from src.schemas import RunResult


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Simple, standard, and reasonable at
    small n (unlike the normal approximation, which can go out of [0,1])."""
    if n == 0:
        return (0.0, 0.0)
    phat = successes / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    margin = (z * ((phat * (1 - phat) / n + z**2 / (4 * n**2)) ** 0.5)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


class ProportionStat(BaseModel):
    successes: int
    n: int
    rate: float
    ci_low: float
    ci_high: float

    @classmethod
    def compute(cls, successes: int, n: int) -> "ProportionStat":
        rate = successes / n if n else 0.0
        lo, hi = wilson_interval(successes, n)
        return cls(successes=successes, n=n, rate=rate, ci_low=lo, ci_high=hi)

    def as_str(self) -> str:
        if self.n == 0:
            return "n/a (n=0)"
        return f"{self.successes}/{self.n} ({self.rate:.0%}) [{self.ci_low:.0%}–{self.ci_high:.0%}]"


class SystemEvaluation(BaseModel):
    system: Literal["baseline", "multiagent"]
    n_hypotheses: int

    # (1) citation validity
    hallucinated_citation_rate: ProportionStat  # from raw generation, code-enforced
    citation_support: ProportionStat  # judge: supporting citations rated "yes"
    citation_support_counts: dict[str, int]  # yes / partially / no

    # (2) falsification survival
    falsification_survival: ProportionStat  # verdict == "survives"
    falsification_verdict_counts: dict[str, int]  # survives / weakened / refuted / unknown

    # (3) novelty vs. triviality
    novelty: ProportionStat  # judge: non_obvious

    # (4) grounding depth
    grounding_depth_avg: float  # avg valid supporting sources per hypothesis


def hallucinated_citation_stat(run_result: RunResult) -> ProportionStat:
    """Fraction of ALL citations the model attempted during generation (before code-side
    validation) that turned out not to exist in the run's real retrieved sources."""
    dropped = len(run_result.dropped_citations)
    kept = sum(
        len(h.supporting_evidence) + len(h.conflicting_evidence) for h in run_result.hypotheses
    )
    total_attempted = dropped + kept
    return ProportionStat.compute(dropped, total_attempted)


def grounding_depth(run_result: RunResult) -> float:
    if not run_result.hypotheses:
        return 0.0
    return sum(len(h.supporting_evidence) for h in run_result.hypotheses) / len(
        run_result.hypotheses
    )


def aggregate_system_evaluation(
    system: Literal["baseline", "multiagent"],
    run_result: RunResult,
    judge_results: list[dict[str, Any]],
    falsification_results: list[dict[str, Any]],
) -> SystemEvaluation:
    n = len(run_result.hypotheses)

    support_counts = {"yes": 0, "partially": 0, "no": 0}
    for jr in judge_results:
        for check in jr.get("citation_checks", []):
            if not isinstance(check, dict):
                continue
            verdict = check.get("supports_claim", "no")
            support_counts[verdict] = support_counts.get(verdict, 0) + 1
    total_checks = sum(support_counts.values())
    citation_support = ProportionStat.compute(support_counts["yes"], total_checks)

    novelty_counts = {"non_obvious": 0, "trivial_restatement": 0}
    for jr in judge_results:
        nov = jr.get("novelty", "trivial_restatement")
        novelty_counts[nov] = novelty_counts.get(nov, 0) + 1
    novelty = ProportionStat.compute(novelty_counts["non_obvious"], len(judge_results))

    verdict_counts = {"survives": 0, "weakened": 0, "refuted": 0, "unknown": 0}
    for fr in falsification_results:
        v = fr.get("verdict", "unknown")
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    falsification_survival = ProportionStat.compute(
        verdict_counts["survives"], len(falsification_results)
    )

    return SystemEvaluation(
        system=system,
        n_hypotheses=n,
        hallucinated_citation_rate=hallucinated_citation_stat(run_result),
        citation_support=citation_support,
        citation_support_counts=support_counts,
        falsification_survival=falsification_survival,
        falsification_verdict_counts=verdict_counts,
        novelty=novelty,
        grounding_depth_avg=grounding_depth(run_result),
    )


def render_comparison_table(evaluations: list[SystemEvaluation]) -> str:
    by_system = {e.system: e for e in evaluations}
    order = [s for s in ("baseline", "multiagent") if s in by_system]
    headers = [f"{s} (n={by_system[s].n_hypotheses})" for s in order]

    rows = [
        ("Hallucinated citation rate (generation-time)",
         [by_system[s].hallucinated_citation_rate.as_str() for s in order]),
        ("Citation support rate (independent judge, supporting cites)",
         [by_system[s].citation_support.as_str() for s in order]),
        ("Falsification survival (independent adversarial search)",
         [by_system[s].falsification_survival.as_str() for s in order]),
        ("Novelty rate (non-obvious vs. restatement)",
         [by_system[s].novelty.as_str() for s in order]),
        ("Grounding depth (avg valid supporting sources/hypothesis)",
         [f"{by_system[s].grounding_depth_avg:.2f}" for s in order]),
    ]

    lines = ["| Metric | " + " | ".join(headers) + " |"]
    lines.append("|---" * (len(headers) + 1) + "|")
    for label, values in rows:
        lines.append(f"| {label} | " + " | ".join(values) + " |")

    lines.append("")
    lines.append(
        f"n={by_system[order[0]].n_hypotheses} hypotheses per system in this run. "
        "Intervals are 95% Wilson score intervals — wide at this sample size. Treat this "
        "as a small pilot comparison, not a definitive result; do not over-interpret gaps "
        "that fall within each other's interval."
    )
    return "\n".join(lines)


class HypothesisEvaluation(BaseModel):
    """Full per-hypothesis evaluation detail, blind judge + independent falsification —
    kept alongside the aggregate table since the aggregate numbers are the research data
    but the per-hypothesis reasoning is what makes them inspectable."""

    system: Literal["baseline", "multiagent"]
    claim: str
    citation_checks: list[dict[str, Any]]
    novelty: str
    novelty_reasoning: str
    falsification_verdict: str
    falsification_reasoning: str
    new_conflicting_evidence: list[str]


class EvaluationReport(BaseModel):
    run_ids: dict[str, str]
    system_evaluations: list[SystemEvaluation]
    per_hypothesis: list[HypothesisEvaluation]
    comparison_table_markdown: str
