"""Tool schemas (Anthropic tool-use format) and dispatch for the shared retrieval APIs.
Both System A and System B agents draw from this same tool set — architecture is the
only thing allowed to differ between the two systems."""
from typing import Any

from src.retrieval import (
    search_clinical_trials,
    search_literature,
    search_targets,
    search_variant_evidence,
)
from src.schemas import Source

RETRIEVAL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_literature",
        "description": (
            "Search Europe PMC / PubMed for peer-reviewed literature relevant to a query. "
            "Returns real articles with citable source IDs. Use this for evidence about "
            "biomarkers, mechanisms, epidemiology, and clinical findings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, e.g. 'cholangiocarcinoma bile biomarker'"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_gene_targets",
        "description": (
            "Search Open Targets for gene/target, disease, or drug information (associations, "
            "tractability, known biology). Use this for evidence about genes, mutations, or pathways."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free text, e.g. gene symbol or disease name"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_variant_evidence",
        "description": (
            "Search CIViC for curated clinical evidence about specific gene variants in cancer "
            "(e.g. FGFR2 fusions, IDH1 mutations) — diagnostic, prognostic, predictive, or "
            "therapeutic significance."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "gene_or_variant": {"type": "string", "description": "e.g. 'FGFR2' or 'IDH1 R132H'"},
                "disease": {
                    "type": "string",
                    "description": "Disease filter, default 'cholangiocarcinoma'. Pass empty string to remove the filter.",
                    "default": "cholangiocarcinoma",
                },
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["gene_or_variant"],
        },
    },
    {
        "name": "search_clinical_trials",
        "description": "Search ClinicalTrials.gov for trials relevant to a query, e.g. an early-detection biomarker or screening approach.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
]


def dispatch_tool_call(name: str, tool_input: dict[str, Any]) -> list[Source]:
    if name == "search_literature":
        return search_literature(
            query=tool_input["query"], max_results=tool_input.get("max_results", 5)
        )
    if name == "search_gene_targets":
        return search_targets(
            query=tool_input["query"], max_results=tool_input.get("max_results", 5)
        )
    if name == "search_variant_evidence":
        disease = tool_input.get("disease", "cholangiocarcinoma") or None
        return search_variant_evidence(
            gene_or_variant=tool_input.get("gene_or_variant"),
            disease=disease,
            max_results=tool_input.get("max_results", 5),
        )
    if name == "search_clinical_trials":
        return search_clinical_trials(
            query=tool_input["query"], max_results=tool_input.get("max_results", 5)
        )
    raise ValueError(f"Unknown tool: {name}")


SUBMIT_HYPOTHESES_TOOL: dict[str, Any] = {
    "name": "submit_hypotheses",
    "description": (
        "Submit the final list of early-detection hypotheses. Only call this once you have "
        "gathered sufficient evidence via the search tools. Every ID in supporting_evidence "
        "or conflicting_evidence MUST be an exact source ID that was returned to you by a "
        "search tool earlier in this conversation. Do not invent or recall IDs from memory — "
        "any ID that was not actually returned by a tool call will be discarded."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
                        "conflicting_evidence": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reasoning": {"type": "string"},
                    },
                    "required": [
                        "claim",
                        "supporting_evidence",
                        "conflicting_evidence",
                        "confidence",
                        "reasoning",
                    ],
                },
            }
        },
        "required": ["hypotheses"],
    },
}


SUBMIT_ADVERSARIAL_REVIEW_TOOL: dict[str, Any] = {
    "name": "submit_adversarial_review",
    "description": (
        "Submit your adversarial review of the hypothesis. List every source ID you found via "
        "the search tools that conflicts with, weakens, or complicates the claim — even partial "
        "or indirect conflicts. If your search genuinely found nothing that undermines the claim, "
        "say so honestly rather than inventing a weakness."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "additional_conflicting_evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Source IDs, exactly as returned by a search tool in this conversation, that conflict with the claim.",
            },
            "verdict": {
                "type": "string",
                "enum": ["survives", "weakened", "refuted"],
                "description": "Your overall judgment after the adversarial search.",
            },
            "verdict_reasoning": {"type": "string"},
            "revised_confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Your updated confidence in the hypothesis after adversarial review.",
            },
        },
        "required": [
            "additional_conflicting_evidence",
            "verdict",
            "verdict_reasoning",
            "revised_confidence",
        ],
    },
}


SUBMIT_RANKING_TOOL: dict[str, Any] = {
    "name": "submit_ranking",
    "description": (
        "Submit scores for every candidate hypothesis, in the same order they were given to you. "
        "Score grounding, survival, and novelty independently — never let writing quality or "
        "confident tone influence any score."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                            "description": "0-based index matching the candidate order given",
                        },
                        "grounding_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "How well-supported by specific, real, relevant evidence",
                        },
                        "survival_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "How well it held up under adversarial review",
                        },
                        "novelty_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": (
                                "How non-obvious the hypothesis is. Score low for restatements of "
                                "well-established facts (e.g. FGFR2 fusions, IDH1 mutations); high "
                                "for genuinely non-obvious proposals or combinations."
                            ),
                        },
                        "notes": {"type": "string"},
                    },
                    "required": [
                        "index",
                        "grounding_score",
                        "survival_score",
                        "novelty_score",
                        "notes",
                    ],
                },
            }
        },
        "required": ["scores"],
    },
}
