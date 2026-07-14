"""CIViC GraphQL search for clinical evidence on gene variants."""
import httpx

from src.schemas import Source

BASE_URL = "https://civicdb.org/api/graphql"

QUERY = """
query evidence($moleProfile: String, $disease: String, $n: Int) {
  evidenceItems(molecularProfileName: $moleProfile, diseaseName: $disease, first: $n, status: ACCEPTED) {
    totalCount
    nodes {
      id
      name
      description
      evidenceLevel
      evidenceType
      significance
      evidenceDirection
      molecularProfile { name }
      disease { name }
      source { citationId sourceType }
    }
  }
}
"""


def search_variant_evidence(
    gene_or_variant: str | None = None,
    disease: str | None = "cholangiocarcinoma",
    max_results: int = 5,
) -> list[Source]:
    variables = {"moleProfile": gene_or_variant, "disease": disease, "n": max_results}
    resp = httpx.post(BASE_URL, json={"query": QUERY, "variables": variables}, timeout=20.0)
    resp.raise_for_status()
    data = resp.json()
    nodes = data.get("data", {}).get("evidenceItems", {}).get("nodes", [])

    sources = []
    for n in nodes:
        eid = n["id"]
        name = n.get("name", f"EID{eid}")
        mp = (n.get("molecularProfile") or {}).get("name", "")
        disease_name = (n.get("disease") or {}).get("name", "")
        description = n.get("description", "")
        level = n.get("evidenceLevel", "")
        etype = n.get("evidenceType", "")
        significance = n.get("significance", "")
        direction = n.get("evidenceDirection", "")

        title = f"{mp} — {disease_name} ({etype}, level {level}, {direction} {significance})"
        snippet = description[:800] if description else title

        sources.append(
            Source(
                id=f"CIVIC:{name}",
                source_type="civic",
                title=title,
                snippet=snippet,
                url=f"https://civicdb.org/evidence/{eid}/summary",
            )
        )
    return sources
