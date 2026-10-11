"""Download StatCan tables via the Web Data Service (WDS) API.

Each full table is streamed to a temp file and read in chunks, keeping only the
Canada and Nova Scotia rows, so memory stays flat even for multi-GB tables.

Usage:
  python fetch_statcan.py              # every table in sources.py
  python fetch_statcan.py 18100205     # one table
  python fetch_statcan.py --search rent
"""
import json
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from sources import PROVINCES, STATCAN_TABLES

WDS = "https://www150.statcan.gc.ca/t1/wds/rest"
OUT = Path("data/statcan")
MANIFEST = Path("data/manifest.json")
HEADERS = {"User-Agent": "canada-property-finance-data (open research)"}
NS_PATTERN = r"Nova Scotia|Halifax|New Glasgow|Sydney|Truro|Kentville"
CHUNK = 200_000
GZIP_OVER_MB = 40  # keep committed files well under GitHub's 100 MB limit


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


def stream_zip(pid, dest):
    r = requests.get(f"{WDS}/getFullTableDownloadCSV/{pid}/en", headers=HEADERS, timeout=60)
    r.raise_for_status()
    with requests.get(r.json()["object"], headers=HEADERS, stream=True, timeout=600) as z:
        z.raise_for_status()
        with open(dest, "wb") as f:
            for block in z.iter_content(1 << 20):
                f.write(block)


def fetch(pid):
    OUT.mkdir(parents=True, exist_ok=True)
    total, latest, parts = 0, None, []
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / f"{pid}.zip"
        stream_zip(pid, zpath)
        print(f"    downloaded {zpath.stat().st_size / 1e6:,.0f} MB", flush=True)
        with zipfile.ZipFile(zpath) as zf, zf.open(f"{pid}.csv") as fh:
            for chunk in pd.read_csv(fh, chunksize=CHUNK, dtype=str):
                total += len(chunk)
                if "REF_DATE" in chunk:
                    m = chunk["REF_DATE"].max()
                    latest = m if latest is None or m > latest else latest
                if "GEO" in chunk:
                    keep = chunk["GEO"].isin(PROVINCES) | chunk["GEO"].str.contains(NS_PATTERN, na=False)
                    parts.append(chunk[keep])
    df = pd.concat(parts) if parts else pd.DataFrame()
    path = OUT / f"{pid}.csv"
    df.to_csv(path, index=False)
    if path.stat().st_size > GZIP_OVER_MB * 1e6:
        df.to_csv(OUT / f"{pid}.csv.gz", index=False, compression="gzip")
        path.unlink()
        path = OUT / f"{pid}.csv.gz"
    return total, len(df), latest, path


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
        print(f"... {pid}", flush=True)
        try:
            title = table_title(pid)
            total, kept, latest, path = fetch(pid)
            manifest[f"statcan:{pid}"] = {
                "title": title,
                "expected": STATCAN_TABLES.get(pid, ""),
                "national_rows": total,
                "canada_ns_rows": kept,
                "latest_period": latest,
                "file": str(path),
                "source": f"https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid={pid}01",
                "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            print(f"OK  {pid}  {title}  ({total:,} rows scanned, {kept:,} kept)", flush=True)
        except Exception as e:  # keep going; report at end
            failures.append(pid)
            print(f"ERR {pid}  {e}", flush=True)
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
