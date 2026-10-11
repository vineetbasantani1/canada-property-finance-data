"""Catalogue finance/property datasets on federal (CKAN) and Nova Scotia (Socrata) portals.

Writes data/catalog/open_data_catalog.csv so you can pick datasets worth pulling.
"""
from pathlib import Path

import pandas as pd
import requests

from sources import CKAN_PORTALS, OPEN_DATA_QUERIES, SOCRATA_DOMAINS

OUT = Path("data/catalog")


def ckan(name, url, q):
    r = requests.get(url, params={"q": q, "rows": 50}, timeout=60)
    r.raise_for_status()
    for p in r.json()["result"]["results"]:
        yield {
            "portal": name, "query": q, "title": p.get("title"),
            "org": (p.get("organization") or {}).get("title"),
            "updated": p.get("metadata_modified"),
            "formats": ",".join(sorted({(x.get("format") or "").upper() for x in p.get("resources", [])})),
            "url": f"https://open.canada.ca/data/en/dataset/{p['id']}",
        }


def socrata(name, domain, q):
    r = requests.get("https://api.us.socrata.com/api/catalog/v1",
                     params={"domains": domain, "q": q, "limit": 50}, timeout=60)
    r.raise_for_status()
    for item in r.json()["results"]:
        res = item["resource"]
        yield {
            "portal": name, "query": q, "title": res.get("name"),
            "org": res.get("attribution"), "updated": res.get("updatedAt"),
            "formats": res.get("type"), "url": item.get("permalink"),
        }


def main():
    rows = []
    for q in OPEN_DATA_QUERIES:
        for name, url in CKAN_PORTALS.items():
            try:
                rows += list(ckan(name, url, q))
            except Exception as e:
                print(f"ERR {name} '{q}': {e}")
        for name, dom in SOCRATA_DOMAINS.items():
            try:
                rows += list(socrata(name, dom, q))
            except Exception as e:
                print(f"ERR {name} '{q}': {e}")
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).drop_duplicates(subset=["url"])
    df.to_csv(OUT / "open_data_catalog.csv", index=False)
    print(f"Catalogued {len(df)} datasets")


if __name__ == "__main__":
    main()
