"""ClinicalTrials.gov API v2 search."""
import httpx

from src.schemas import Source

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


def search_clinical_trials(query: str, max_results: int = 5) -> list[Source]:
    params = {"query.term": query, "pageSize": max_results}
    resp = httpx.get(BASE_URL, params=params, timeout=20.0)
    resp.raise_for_status()
    data = resp.json()
    studies = data.get("studies", [])

    sources = []
    for s in studies:
        protocol = s.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        desc = protocol.get("descriptionModule", {})
        nct_id = ident.get("nctId", "")
        title = ident.get("briefTitle", "")
        summary = desc.get("briefSummary", "")

        sources.append(
            Source(
                id=f"CT:{nct_id}",
                source_type="clinical_trials",
                title=title,
                snippet=summary[:800] if summary else title,
                url=f"https://clinicaltrials.gov/study/{nct_id}",
            )
        )
    return sources
