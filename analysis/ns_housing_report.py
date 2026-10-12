"""Nova Scotia vs Canada housing snapshot.

Reads the files fetched into data/ and writes reports/ns-housing/ with charts
(PNG) and a README.md whose every number is computed here from the data.

Run from the repo root:  python analysis/ns_housing_report.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator

DATA = Path("data")
OUT = Path("reports/ns-housing")
OUT.mkdir(parents=True, exist_ok=True)

# Palette (validated): brand red first, then reference blue. Slot 1 = Nova Scotia, slot 2 = Canada
NS, CA = "#B3141B", "#2a78d6"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
})
SOURCE = "Source: Statistics Canada; Bank of Canada. Analysis: Vineet Basantani"


def statcan(table, **filters):
    """Load a StatCan slice; suppressed values ('..' not available, 'F' unreliable) become NaN."""
    df = pd.read_csv(DATA / "statcan" / f"{table}.csv", low_memory=False)
    for col, val in filters.items():
        df = df[df[col.replace("_", " ")] == val]
    bad = df["STATUS"].isin(["..", "...", "x", "F"]) | (df["VALUE"] == 0)
    df.loc[bad, "VALUE"] = float("nan")
    return df


def finish(fig, ax, name, subtitle):
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=11, va="bottom")
    fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def label_end(ax, s, color, text):
    ax.annotate(f"{text}  {s.iloc[-1]:.1f}%", (s.index[-1], s.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", color=INK, fontsize=10.5, fontweight="bold")
    ax.plot(s.index[-1], s.iloc[-1], "o", ms=7, color=color, mec=SURFACE, mew=2)


# ---------- 1. Rent inflation (CPI rent, 12-month change) ----------
cpi = statcan("18100004")
cpi = cpi[cpi["Products and product groups"].isin(["All-items", "Rent", "Shelter"])]
cpi = cpi.pivot_table(index="REF_DATE", columns=["GEO", "Products and product groups"], values="VALUE")
cpi.index = pd.to_datetime(cpi.index)
latest = cpi.index.max()
yoy = (cpi / cpi.shift(12) - 1) * 100
five = (cpi.loc[latest] / cpi.loc[latest - pd.DateOffset(years=5)] - 1) * 100

fig, ax = plt.subplots(figsize=(10, 5.6))
for geo, color in [("Nova Scotia", NS), ("Canada", CA)]:
    s = yoy[(geo, "Rent")].loc["2019":]
    ax.plot(s.index, s, color=color, lw=2.2, label=geo)
    label_end(ax, s, color, geo)
r_ns, r_ca = yoy[("Nova Scotia", "Rent")].loc[latest], yoy[("Canada", "Rent")].loc[latest]
ratio = r_ns / r_ca if r_ca > 0 else float("nan")
headline = (f"Nova Scotia rents are rising {ratio:.1f}x faster than Canada's" if ratio >= 1.2
            else "Rent inflation: Nova Scotia vs Canada")
ax.set_title(headline, pad=28)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_ylabel("12-month change in rent (CPI)")
ax.legend(frameon=False, loc="upper left")
ax.set_xlim(right=latest + pd.DateOffset(months=14))
finish(fig, ax, "01_rent_inflation.png", f"Rent component of the Consumer Price Index, year-over-year, to {latest:%B %Y}")

# ---------- 2. Halifax 2-bedroom rent and vacancy (two panels, no dual axis) ----------
rent = statcan("34100133", Type_of_structure="Row and apartment structures of three units and over",
               Type_of_unit="Two bedroom units")
rent = rent.pivot_table(index="REF_DATE", columns="GEO", values="VALUE")
vac = statcan("34100127").pivot_table(index="REF_DATE", columns="GEO", values="VALUE")["Halifax, Nova Scotia"]
hfx = rent["Halifax, Nova Scotia"].dropna()
ry = int(hfx.index.max())

fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.2))
h = hfx.loc[2010:]
a1.bar(h.index, h, color=NS, width=0.75)
a1.set_title("Average 2-bedroom rent", fontsize=13)
a1.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
for y in (2015, 2020, ry):
    a1.annotate(f"${h[y]:,.0f}", (y, h[y]), xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9.5, color=INK)
v = vac.loc[2010:]
a2.plot(v.index, v, color=NS, lw=2.2, marker="o", ms=5, mec=SURFACE)
a2.set_title("Apartment vacancy rate", fontsize=13)
a2.yaxis.set_major_formatter(lambda val, _: f"{val:.0f}%")
a2.set_ylim(0, max(4, v.max() + 0.5))
a2.yaxis.set_major_locator(MultipleLocator(1))
for y in (v.idxmin(), v.index.max()):
    a2.annotate(f"{v[y]:.1f}%", (y, v[y]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9.5)
fig.suptitle("Halifax: more vacancies, but rents keep climbing", x=0.01, ha="left", fontsize=15, fontweight="bold")
fig.text(0.01, 0.01, SOURCE + " (CMHC Rental Market Survey via StatCan)", color=INK2, fontsize=8.5)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(OUT / "02_halifax_rent_vacancy.png", dpi=200)
plt.close(fig)

# ---------- 3. Five-year rent growth by NS centre ----------
base = ry - 5
growth = ((rent.loc[ry] / rent.loc[base] - 1) * 100).dropna().sort_values()
growth.index = growth.index.str.replace(", Nova Scotia", "")
fig, ax = plt.subplots(figsize=(10, 0.55 * len(growth) + 1.8))
ax.barh(growth.index, growth, color=NS, height=0.6)
for name, val in growth.items():
    ax.text(val + 0.6, name, f"{val:.0f}%", va="center", fontsize=10, color=INK)
ax.set_title(f"2-bedroom rents, {base} to {ry}: up everywhere in Nova Scotia", pad=28)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.grid(axis="y", visible=False)
ax.set_xlim(0, growth.max() * 1.15)
finish(fig, ax, "03_rent_growth_by_centre.png", "Change in average rent, row and apartment structures of 3+ units (centres with published data)")

# ---------- 4. New housing price index: Halifax vs Canada ----------
nhpi = statcan("18100205", New_housing_price_indexes="Total (house and land)")
nhpi = nhpi.pivot_table(index="REF_DATE", columns="GEO", values="VALUE")
nhpi.index = pd.to_datetime(nhpi.index)
nl = nhpi.index.max()
b0 = nl - pd.DateOffset(years=5)
idx = nhpi.loc[b0:] / nhpi.loc[b0] * 100
fig, ax = plt.subplots(figsize=(10, 5.6))
for geo, color, name in [("Halifax, Nova Scotia", NS, "Halifax"), ("Canada", CA, "Canada")]:
    s = idx[geo]
    ax.plot(s.index, s, color=color, lw=2.2, label=name)
    ax.annotate(f"{name}  {s.iloc[-1] - 100:+.1f}%", (s.index[-1], s.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=10.5, fontweight="bold")
    ax.plot(s.index[-1], s.iloc[-1], "o", ms=7, color=color, mec=SURFACE, mew=2)
ax.axhline(100, color=INK2, lw=1)
ax.set_title("New-home prices: Halifax keeps rising as Canada cools", pad=28)
ax.set_ylabel(f"Index, {b0:%b %Y} = 100")
ax.legend(frameon=False, loc="upper left")
ax.set_xlim(right=nl + pd.DateOffset(months=12))
finish(fig, ax, "04_new_housing_prices.png", "New Housing Price Index, house and land (the Nova Scotia index covers Halifax only)")

# ---------- Numbers for the write-up ----------
boc = pd.read_csv(DATA / "boc" / "boc_rates.csv", parse_dates=["date"])
mort = boc[boc.series == "V80691335"].dropna().set_index("date")["value"]
m_now, m_2021 = mort.iloc[-1], mort.loc["2021-01"].iloc[0]
nh_1y = {g: (nhpi[g].iloc[-1] / nhpi[g].loc[nl - pd.DateOffset(years=1)] - 1) * 100 for g in ["Halifax, Nova Scotia", "Canada"]}
ny = lambda g, k: yoy[(g, k)].loc[latest]  # noqa: E731

summary = pd.DataFrame({
    "Nova Scotia": [ny("Nova Scotia", "Rent"), five[("Nova Scotia", "Rent")], ny("Nova Scotia", "Shelter"), ny("Nova Scotia", "All-items")],
    "Canada": [ny("Canada", "Rent"), five[("Canada", "Rent")], ny("Canada", "Shelter"), ny("Canada", "All-items")],
}, index=["Rent, 12-month change", "Rent, 5-year change", "Shelter, 12-month change", "All-items CPI, 12-month change"])
summary.round(1).to_csv(OUT / "summary.csv")
growth.round(1).rename("rent_growth_pct").to_csv(OUT / "rent_growth_by_centre.csv")

skipped = sorted(set(rent.columns.str.replace(", Nova Scotia", "")) - set(growth.index))
md = f"""# Nova Scotia housing: rents outpace the country

*Data to {latest:%B %Y} (CPI), {nl:%B %Y} (new-home prices) and {ry} (CMHC rental survey).
Generated by [`analysis/ns_housing_report.py`](../../analysis/ns_housing_report.py) from the files in [`data/`](../../data).*

## Key findings

- **Rent inflation in Nova Scotia is {ny('Nova Scotia','Rent'):.1f}%**, against {ny('Canada','Rent'):.1f}% for Canada
  (12 months to {latest:%B %Y}). Over five years NS rents are up {five[('Nova Scotia','Rent')]:.1f}%, against {five[('Canada','Rent')]:.1f}% nationally.
- **Overall NS inflation is {ny('Nova Scotia','All-items'):.1f}%**, against {ny('Canada','All-items'):.1f}% for Canada, with shelter at {ny('Nova Scotia','Shelter'):.1f}%.
- **A Halifax 2-bedroom averaged ${hfx[ry]:,.0f}/month in {ry}**, up {(hfx[ry]/hfx[base]-1)*100:.0f}% from ${hfx[base]:,.0f} in {base},
  even though vacancy rose from a low of {v.min():.1f}% to {v.iloc[-1]:.1f}%.
- **Every Nova Scotia centre with published data saw 2-bedroom rents rise {growth.min():.0f}%–{growth.max():.0f}% over five years.**
- **New-home prices: Halifax {nh_1y['Halifax, Nova Scotia']:+.1f}% over the past year, Canada {nh_1y['Canada']:+.1f}%.**
  Over five years Halifax is {idx['Halifax, Nova Scotia'].iloc[-1]-100:+.1f}% and Canada {idx['Canada'].iloc[-1]-100:+.1f}%.
- **The posted 5-year conventional mortgage rate is {m_now:.2f}%** ({mort.index[-1]:%b %d, %Y}), against {m_2021:.2f}% in January 2021.

![Rent inflation](01_rent_inflation.png)

![Halifax rent and vacancy](02_halifax_rent_vacancy.png)

![Rent growth by centre](03_rent_growth_by_centre.png)

![New housing prices](04_new_housing_prices.png)

## Summary table

| Measure | Nova Scotia | Canada |
|---|---:|---:|
""" + "\n".join(f"| {i} | {r['Nova Scotia']:.1f}% | {r['Canada']:.1f}% |" for i, r in summary.iterrows()) + f"""

## Notes on method

- **Sources:** StatCan tables 18-10-0004-01 (CPI), 34-10-0133-01 (CMHC average rents), 34-10-0127-01 (CMHC vacancy rates),
  18-10-0205-01 (New Housing Price Index); Bank of Canada series V80691335 (5-year conventional mortgage rate).
- **Suppressed values:** StatCan marks some figures as not available (`..`) or too unreliable to publish (`F`); these are treated as missing,
  not zero. Centres without both {base} and {ry} figures are left out of the growth chart{(' (' + ', '.join(skipped) + ')') if skipped else ''}.
- **Rents** are for row and apartment structures of three or more units, from CMHC's annual October survey.
- **New-home prices:** StatCan's Nova Scotia New Housing Price Index covers Halifax only.
- **Mortgage rate** is the banks' posted rate; most borrowers pay less after discounts.
"""
(OUT / "README.md").write_text(md)
print(md)
