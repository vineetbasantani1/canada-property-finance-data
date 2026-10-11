# Canada Property & Finance Data

Open-data pipeline and analysis of Canadian housing, property and household-finance
indicators, with a focus on **Nova Scotia** alongside national figures.

Author: Vineet Basantani

## Reports

- [Halifax's supply gap: people arrived faster than homes were finished](reports/halifax-supply-gap/README.md) — new residents vs completed homes each year, and the record construction pipeline
- [What actually drove rent increases?](reports/real-rent-factors/README.md) — population growth, new building and rental supply tested together across cities, with rent change in dollars
- [What drove rent growth? Tight markets and catch-up](reports/what-drives-rent/README.md) — tests across Canadian cities whether low vacancy before the boom, or cheap starting rents, predicted faster rent growth
- [People vs homes: did population growth drive Nova Scotia's rent surge?](reports/people-vs-homes/README.md) — population growth by source vs housing starts, and a nine-province test of whether more people per new home meant faster rent growth
- [Nova Scotia housing: rents outpace the country](reports/ns-housing/README.md) — rent inflation, Halifax rents and vacancy, rent growth across NS centres, new-home prices (refreshed weekly)

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
  statcan/<id>.csv             Canada, Nova Scotia and NS-city rows of each table
                               (.csv.gz if over 40 MB; full national tables are not stored)
  statcan/provinces/<id>.csv   province-level rows for cross-province comparisons
                               (population, population growth, housing completions, rent CPI)
  boc/boc_rates.csv            interest-rate and FX series
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
