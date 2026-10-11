# Canada Property & Finance Data

Open-data pipeline and analysis of Canadian housing, property and household-finance
indicators, with a focus on **Nova Scotia** alongside national figures.

Author: Vineet Basantani

## What it collects

| Source | Content |
|---|---|
| Statistics Canada (WDS API) | New housing prices, CMHC rents, vacancy rates, housing starts, building permits, property values (CHSP), household debt service, credit, CPI/shelter, population, GDP by industry |
| Bank of Canada (Valet API) | Policy rate, prime rate, 5-year mortgage rate, 5- and 10-year bond yields, USD/CAD |
| open.canada.ca + data.novascotia.ca | Catalogue of further housing/property/mortgage datasets to pull |

The full list with table IDs is in [`sources.py`](sources.py).

## Layout

```
data/
  raw/statcan/<id>.csv.gz      full national tables
  raw/boc/boc_rates.csv        interest-rate and FX series
  provincial/<id>_ns.csv       Canada / Nova Scotia / NS-city rows only
  catalog/open_data_catalog.csv
  manifest.json                official title, row count, latest period, source link per dataset
```

## Running

The data refreshes every Monday via GitHub Actions (`.github/workflows/fetch-data.yml`),
and can be triggered by hand from the **Actions** tab → *Fetch data* → *Run workflow*.

Locally:

```bash
pip install -r requirements.txt
python fetch_all.py
python fetch_statcan.py --search "mortgage"   # find more StatCan tables
```

Check `data/manifest.json` after each run: the `title` field is what StatCan / the Bank
of Canada call each dataset, so any ID that points somewhere unexpected is easy to spot.

## Licence

Data: Statistics Canada Open Licence, Bank of Canada terms of use, Open Government Licence – Canada
and Nova Scotia. Code: MIT.
