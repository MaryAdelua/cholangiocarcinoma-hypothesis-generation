"""Europe PMC (covers PubMed) literature search."""
import httpx

from src.schemas import Source

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def search_literature(query: str, max_results: int = 5) -> list[Source]:
    params = {
        "query": query,
        "format": "json",
        "pageSize": max_results,
        "resultType": "core",
    }
    resp = httpx.get(BASE_URL, params=params, timeout=20.0)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("resultList", {}).get("result", [])

    sources = []
    for r in results:
        pmid = r.get("pmid")
        pmcid = r.get("pmcid")
        if pmid:
            source_id = f"PMID:{pmid}"
        elif pmcid:
            source_id = f"PMCID:{pmcid}"
        else:
            source_id = f"{r.get('source', 'EPMC')}:{r.get('id')}"

        title = r.get("title", "")
        abstract = r.get("abstractText", "")
        snippet = abstract[:800] if abstract else title

        if pmid:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        elif pmcid:
            url = f"https://europepmc.org/article/PMC/{pmcid}"
        else:
            url = f"https://europepmc.org/article/{r.get('source', '')}/{r.get('id', '')}"

        sources.append(
            Source(
                id=source_id,
                source_type="pubmed",
                title=title,
                snippet=snippet,
                url=url,
            )
        )
    return sources
