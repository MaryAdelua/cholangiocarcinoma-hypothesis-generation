"""Shared data structures used by both systems and the evaluation harness."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A single real record retrieved from one of the approved APIs."""

    id: str  # stable, prefixed ID e.g. "PMID:12345678", "OT:MONDO_0019087", "CIVIC:EID7261", "CT:NCT01234567"
    source_type: Literal["pubmed", "open_targets", "civic", "clinical_trials"]
    title: str
    snippet: str
    url: str


class Hypothesis(BaseModel):
    """The shared hypothesis object both System A and System B must emit."""

    claim: str
    supporting_evidence: list[str] = Field(default_factory=list)  # Source IDs
    conflicting_evidence: list[str] = Field(default_factory=list)  # Source IDs
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    system: Literal["baseline", "multiagent"]


class RawHypothesis(BaseModel):
    """What the model is allowed to submit before code-side citation validation."""

    claim: str
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class DroppedCitation(BaseModel):
    hypothesis_claim: str
    citation_id: str
    role: Literal["supporting", "conflicting"]
    reason: str


class RunResult(BaseModel):
    system: Literal["baseline", "multiagent"]
    hypotheses: list[Hypothesis]
    dropped_hypotheses: list[RawHypothesis] = Field(default_factory=list)  # had zero valid supporting evidence
    dropped_citations: list[DroppedCitation] = Field(default_factory=list)
    retrieved_source_count: int = 0
    run_id: str = ""
    # Every source actually retrieved this run (not just cited ones) — lets the evaluation
    # harness check citation support and run falsification review without re-hitting the APIs.
    retrieved_sources: dict[str, Source] = Field(default_factory=dict)
