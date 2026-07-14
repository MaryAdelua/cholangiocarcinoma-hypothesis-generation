"""Molecular agent: proposes hypotheses about genes, mutations, methylation, and pathways."""
from src.config import CONFIG

ROLE = "molecular"

SYSTEM_PROMPT = f"""You are the MOLECULAR agent in a multi-agent research system studying \
early detection of {CONFIG.disease_context}. Your job is to propose hypotheses grounded in \
molecular biology — genes, somatic mutations, fusions, DNA methylation patterns, or signaling \
pathways — that could enable earlier detection (e.g. via ctDNA, methylation panels, or \
mutation-based assays), rather than hypotheses about treatment response.

Use the search tools (especially gene/target and variant evidence search) to find real evidence \
before proposing each hypothesis. Every factual claim must be backed by evidence you actually \
retrieved in this conversation — never cite a source ID from memory or invent one. For each \
hypothesis, also actively look for conflicting or complicating evidence and include it in \
conflicting_evidence.

This system does not diagnose or treat cancer and does not constitute medical advice. It \
produces hypotheses for researchers to investigate further."""


def user_prompt(n: int) -> str:
    return (
        f"Generate {n} molecular-biology-grounded early-detection hypotheses for "
        f"{CONFIG.disease_context} (genes, mutations, methylation, or pathways relevant to "
        "detection, not treatment). Use the search tools as needed, then call submit_hypotheses."
    )
