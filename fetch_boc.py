"""Download Bank of Canada rate series from the Valet API."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from sources import BOC_SERIES

VALET = "https://www.bankofcanada.ca/valet"
OUT = Path("data/boc")
MANIFEST = Path("data/manifest.json")


def main():
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)
    frames, failures = [], []
    for sid, label in BOC_SERIES.items():
        try:
            r = requests.get(f"{VALET}/observations/{sid}/json", timeout=60)
            r.raise_for_status()
            j = r.json()
            obs = j["observations"]
            df = pd.DataFrame({
                "date": [o["d"] for o in obs],
                "value": [float(o[sid]["v"]) if o.get(sid, {}).get("v") not in (None, "") else None for o in obs],
            })
            df["series"] = sid
            frames.append(df)
            manifest[f"boc:{sid}"] = {
                "title": j["seriesDetail"][sid]["label"],
                "expected": label,
                "rows": len(df),
                "latest_period": df["date"].max(),
                "source": f"{VALET}/observations/{sid}",
                "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            print(f"OK  {sid}  {manifest[f'boc:{sid}']['title']}  ({len(df):,} obs)")
        except Exception as e:
            failures.append(sid)
            print(f"ERR {sid}  {e}")
    if frames:
        pd.concat(frames).to_csv(OUT / "boc_rates.csv", index=False)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return failures


if __name__ == "__main__":
    main()
