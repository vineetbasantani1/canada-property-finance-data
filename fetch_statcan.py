"""Download full StatCan tables via the Web Data Service (WDS) API.

Usage:
  python fetch_statcan.py              # download every table in sources.py
  python fetch_statcan.py 18100205     # one table
  python fetch_statcan.py --search rent
"""
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from sources import PROVINCES, STATCAN_TABLES

WDS = "https://www150.statcan.gc.ca/t1/wds/rest"
RAW = Path("data/raw/statcan")
PROV = Path("data/provincial")
MANIFEST = Path("data/manifest.json")
HEADERS = {"User-Agent": "canada-property-finance-data (open research)"}


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def save_manifest(m):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True))


def table_title(pid):
    r = requests.post(f"{WDS}/getCubeMetadata", json=[{"productId": int(pid)}], headers=HEADERS, timeout=60)
    r.raise_for_status()
    obj = r.json()[0]
    if obj.get("status") != "SUCCESS":
        raise ValueError(f"table {pid} not found")
    return obj["object"]["cubeTitleEn"]


def download(pid):
    r = requests.get(f"{WDS}/getFullTableDownloadCSV/{pid}/en", headers=HEADERS, timeout=60)
    r.raise_for_status()
    url = r.json()["object"]
    z = requests.get(url, headers=HEADERS, timeout=600)
    z.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
        name = f"{pid}.csv"
        df = pd.read_csv(zf.open(name), low_memory=False)
    RAW.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW / f"{pid}.csv.gz", index=False, compression="gzip")
    return df


def provincial_slice(pid, df):
    if "GEO" not in df.columns:
        return 0
    mask = df["GEO"].isin(PROVINCES) | df["GEO"].str.contains(
        r"Nova Scotia|New Brunswick|Halifax|Moncton|Saint John|Fredericton|New Glasgow", na=False)
    sub = df[mask]
    PROV.mkdir(parents=True, exist_ok=True)
    sub.to_csv(PROV / f"{pid}_ns_nb.csv", index=False)
    return len(sub)


def search(term):
    r = requests.get(f"{WDS}/getAllCubesListLite", headers=HEADERS, timeout=120)
    r.raise_for_status()
    for c in r.json():
        if term.lower() in c["cubeTitleEn"].lower():
            print(c["productId"], c["cubeTitleEn"], c.get("cubeEndDate", ""))


def main(pids):
    manifest = load_manifest()
    failures = []
    for pid in pids:
        try:
            title = table_title(pid)
            df = download(pid)
            n = provincial_slice(pid, df)
            manifest[f"statcan:{pid}"] = {
                "title": title,
                "expected": STATCAN_TABLES.get(pid, ""),
                "rows": len(df),
                "ns_nb_rows": n,
                "latest_period": str(df["REF_DATE"].max()) if "REF_DATE" in df else None,
                "source": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}01",
                "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            print(f"OK  {pid}  {title}  ({len(df):,} rows, {n:,} NS/NB)")
        except Exception as e:  # keep going; report at end
            failures.append(pid)
            print(f"ERR {pid}  {e}")
    save_manifest(manifest)
    if failures:
        print("Failed:", ", ".join(failures))
    return failures


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--search"]:
        search(" ".join(args[1:]))
    else:
        main(args or list(STATCAN_TABLES))
