"""Code-side enforcement of 'real citations only'. The model's claims about what it cited
are never trusted directly — only IDs actually present in the session's source registry
(populated by real tool calls) are kept."""
from src.schemas import DroppedCitation, Hypothesis, RawHypothesis, Source


def validate_hypotheses(
    raw_hypotheses: list[RawHypothesis],
    retrieved_sources: dict[str, Source],
    system: str,
) -> tuple[list[Hypothesis], list[RawHypothesis], list[DroppedCitation]]:
    valid: list[Hypothesis] = []
    dropped_hypotheses: list[RawHypothesis] = []
    dropped_citations: list[DroppedCitation] = []

    for raw in raw_hypotheses:
        kept_supporting = []
        for cid in raw.supporting_evidence:
            if cid in retrieved_sources:
                kept_supporting.append(cid)
            else:
                dropped_citations.append(
                    DroppedCitation(
                        hypothesis_claim=raw.claim,
                        citation_id=cid,
                        role="supporting",
                        reason="ID not found in this session's retrieved sources",
                    )
                )

        kept_conflicting = []
        for cid in raw.conflicting_evidence:
            if cid in retrieved_sources:
                kept_conflicting.append(cid)
            else:
                dropped_citations.append(
                    DroppedCitation(
                        hypothesis_claim=raw.claim,
                        citation_id=cid,
                        role="conflicting",
                        reason="ID not found in this session's retrieved sources",
                    )
                )

        if not kept_supporting:
            dropped_hypotheses.append(raw)
            continue

        valid.append(
            Hypothesis(
                claim=raw.claim,
                supporting_evidence=kept_supporting,
                conflicting_evidence=kept_conflicting,
                confidence=raw.confidence,
                reasoning=raw.reasoning,
                system=system,
            )
        )

    return valid, dropped_hypotheses, dropped_citations
