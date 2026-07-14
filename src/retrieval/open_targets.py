"""Open Targets Platform GraphQL search (genes, diseases, drug targets)."""
import httpx

from src.schemas import Source

BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"

QUERY = """
query search($q: String!, $size: Int!) {
  search(queryString: $q, entityNames: ["target", "disease", "drug"], page: {index: 0, size: $size}) {
    total
    hits {
      id
      entity
      name
      description
    }
  }
}
"""


def search_targets(query: str, max_results: int = 5) -> list[Source]:
    resp = httpx.post(
        BASE_URL,
        json={"query": QUERY, "variables": {"q": query, "size": max_results}},
        timeout=20.0,
    )
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("data", {}).get("search", {}).get("hits", [])

    sources = []
    for h in hits:
        entity = h.get("entity", "target")
        hit_id = h.get("id", "")
        name = h.get("name", "")
        description = h.get("description") or ""
        url = f"https://platform.opentargets.org/{entity}/{hit_id}"

        sources.append(
            Source(
                id=f"OT:{hit_id}",
                source_type="open_targets",
                title=f"{name} ({entity})",
                snippet=description[:800] if description else name,
                url=url,
            )
        )
    return sources
