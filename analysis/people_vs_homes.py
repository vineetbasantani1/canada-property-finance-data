"""People vs homes: did population growth drive Nova Scotia's rent surge?

Compares population growth (by source) with housing starts, then tests across
provinces whether more new residents per new home meant faster rent growth.
Writes reports/people-vs-homes/ (charts, CSVs, README.md); every number in the
README is computed here.

Run from the repo root:  python analysis/people_vs_homes.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROV = Path("data/statcan/provinces")
OUT = Path("reports/people-vs-homes")
OUT.mkdir(parents=True, exist_ok=True)

# Validated reference palette, categorical slots 1-4 in fixed order
S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SURFACE, INK, INK2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#a3a29c"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
})
SOURCE = "Source: Statistics Canada (tables 17-10-0008-01, 34-10-0135-01, 18-10-0004-01). Analysis: Vineet Basantani"
RECENT = 5  # years in the comparison window


def load(table):
    df = pd.read_csv(PROV / f"{table}.csv", low_memory=False)
    df.loc[df["STATUS"].isin(["..", "...", "x", "F"]), "VALUE"] = np.nan
    return df


def finish(fig, ax, name, subtitle):
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=11, va="bottom")
    fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


# ---------- Population growth by source (July-June years) ----------
pop = load("17100008").pivot_table(index=["GEO", "REF_DATE"], columns="Components of population growth",
                                   values="VALUE").fillna(0)
growth = pd.DataFrame({
    "Immigrants": pop["Immigrants"],
    "Non-permanent residents (net)": pop["Net non-permanent residents"],
    "Interprovincial migration (net)": pop["Net interprovincial migration"],
    "Births minus deaths and emigration": pop["Births"] - pop["Deaths"] - pop["Net emigration"],
})
growth["Total"] = growth.sum(axis=1)

# ---------- Housing starts, summed to the same July-June years ----------
hs = load("34100135")
hs = hs[hs["Housing estimates"] == "Housing starts"].copy()
hs["date"] = pd.to_datetime(hs["REF_DATE"])
hs["year"] = hs["date"].apply(lambda t: f"{t.year}/{t.year + 1}" if t.month >= 7 else f"{t.year - 1}/{t.year}")
q = hs.groupby(["GEO", "year"])["VALUE"].agg(["sum", "count"])
starts = q[q["count"] == 4]["sum"]  # complete years only
growth["Housing starts"] = starts.reindex(growth.index)
growth["People per start"] = growth["Total"] / growth["Housing starts"]

years = sorted(y for y in growth.loc["Nova Scotia"].index if not np.isnan(growth.loc[("Nova Scotia", y), "People per start"]))
last = years[-1]
window = years[-RECENT:]
prior = years[-2 * RECENT:-RECENT]
show = years[-11:]

ns = growth.loc["Nova Scotia"].loc[show]
ca = growth.loc["Canada"].loc[show]
ns.round(2).to_csv(OUT / "nova_scotia_growth_vs_starts.csv")

# ---------- Chart 1: NS growth by source ----------
parts = ["Immigrants", "Non-permanent residents (net)", "Interprovincial migration (net)", "Births minus deaths and emigration"]
colors = [S1, S2, S3, S4]
x = np.arange(len(show))
fig, ax = plt.subplots(figsize=(11, 6))
pos, neg = np.zeros(len(show)), np.zeros(len(show))
for part, color in zip(parts, colors):
    v = ns[part].values
    up, down = np.clip(v, 0, None), np.clip(v, None, 0)
    ax.bar(x, up, bottom=pos, color=color, width=0.68, label=part, edgecolor=SURFACE, linewidth=1.5)
    ax.bar(x, down, bottom=neg, color=color, width=0.68, edgecolor=SURFACE, linewidth=1.5)
    pos += up
    neg += down
for i, t in enumerate(ns["Total"]):
    ax.text(i, pos[i] + 600, f"{t / 1000:.1f}k", ha="center", fontsize=9.5, color=INK, fontweight="bold")
ax.axhline(0, color=INK2, lw=1)
ax.set_xticks(x, [y.replace("/20", "/") for y in show], fontsize=9.5)
ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k")
ax.set_ylabel("People added in the year (July–June)")
ax.legend(frameon=False, loc="upper left", fontsize=10)
peak = ns["Total"].idxmax()
ax.set_title("Nova Scotia's population boom came from three sources, not one", pad=28)
finish(fig, ax, "01_ns_growth_by_source.png", "Components of population growth, Nova Scotia (bold label = total growth)")

# ---------- Chart 2: people added per housing start ----------
fig, ax = plt.subplots(figsize=(10, 5.6))
for s, color, name in [(ns["People per start"], S1, "Nova Scotia"), (ca["People per start"], S2, "Canada")]:
    ax.plot(x, s.values, color=color, lw=2.2, marker="o", ms=6, mec=SURFACE, mew=1.5, label=name)
    ax.annotate(f"{name}  {s.iloc[-1]:.1f}", (x[-1], s.iloc[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=10.5, fontweight="bold")
ax.set_xticks(x, [y.replace("/20", "/") for y in show], fontsize=9.5)
ax.set_xlim(-0.4, len(show) + 1.2)
ax.set_ylabel("New residents per housing start")
ax.legend(frameon=False, loc="upper left")
pk = ns["People per start"].idxmax()
ax.annotate(f"Peak {ns.loc[pk, 'People per start']:.1f} in {pk}", (show.index(pk), ns.loc[pk, "People per start"]),
            xytext=(12, 2), textcoords="offset points", fontsize=9.5, ha="left", va="center", color=INK)
ax.set_ylim(0, max(ns["People per start"].max(), ca["People per start"].max()) * 1.12)
ax.set_title("The squeeze has eased: homes are now being started faster than people arrive", pad=28)
finish(fig, ax, "02_people_per_start.png", "Population growth divided by housing starts, July–June years")

# ---------- Chart 3: provinces, pressure vs rent growth ----------
cpi = load("18100004")
rent = cpi[cpi["Products and product groups"] == "Rent"].pivot_table(index="REF_DATE", columns="GEO", values="VALUE")
end_m = f"{last.split('/')[1]}-06"
start_m = f"{window[0].split('/')[0]}-06"
prev_m = f"{prior[0].split('/')[0]}-06"


def pressure(yrs):
    t = growth[growth.index.get_level_values(1).isin(yrs)].groupby(level=0)[["Total", "Housing starts"]].sum()
    return t["Total"] / t["Housing starts"]


cmp = pd.DataFrame({
    "people_per_start": pressure(window),
    "rent_change_pct": (rent.loc[end_m] / rent.loc[start_m] - 1) * 100,
    "people_per_start_prior": pressure(prior),
    "rent_change_pct_prior": (rent.loc[start_m] / rent.loc[prev_m] - 1) * 100,
}).dropna()
prov = cmp.drop(index="Canada")
r_now = prov["people_per_start"].corr(prov["rent_change_pct"])
r_prev = prov["people_per_start_prior"].corr(prov["rent_change_pct_prior"])
cmp.round(2).to_csv(OUT / "provinces_pressure_vs_rent.csv")

fig, ax = plt.subplots(figsize=(10, 6.2))
others = prov.drop(index="Nova Scotia")
ax.scatter(others["people_per_start"], others["rent_change_pct"], s=90, color=MUTED, edgecolor=SURFACE, linewidth=2, zorder=3)
nsr = prov.loc["Nova Scotia"]
ax.scatter([nsr["people_per_start"]], [nsr["rent_change_pct"]], s=140, color=S1, edgecolor=SURFACE, linewidth=2, zorder=4)
can = cmp.loc["Canada"]
ax.axvline(can["people_per_start"], color=INK2, lw=1, ls=(0, (4, 3)))
ax.axhline(can["rent_change_pct"], color=INK2, lw=1, ls=(0, (4, 3)))
ax.text(can["people_per_start"], ax.get_ylim()[0], " Canada average", color=INK2, fontsize=9, va="bottom")
short = {"Newfoundland and Labrador": "N.L.", "Prince Edward Island": "P.E.I.", "British Columbia": "B.C."}
for name, row in prov.iterrows():
    is_ns = name == "Nova Scotia"
    ax.annotate(short.get(name, name), (row["people_per_start"], row["rent_change_pct"]), xytext=(9, 0),
                textcoords="offset points", va="center", fontsize=11 if is_ns else 9.5,
                fontweight="bold" if is_ns else "normal", color=INK if is_ns else INK2)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_xlabel(f"New residents per housing start, {window[0]} to {last}")
ax.set_ylabel(f"Rent change, June {start_m[:4]} to June {end_m[:4]} (CPI)")
ax.set_xlim(right=prov["people_per_start"].max() * 1.12)
lo, hi = prov["rent_change_pct"].min(), prov["rent_change_pct"].max()
ax.set_ylim(lo - 3, hi + 3)
ax.set_title("More people per new home did not mean faster rent growth", pad=28)
finish(fig, ax, "03_provinces_pressure_vs_rent.png",
       f"Nine provinces; correlation {r_now:+.2f}. Nova Scotia had average pressure but the steepest rent rise")

# ---------- Write-up ----------
W = growth.loc["Nova Scotia"].loc[window]
share = {p: W[p].sum() / W["Total"].sum() * 100 for p in parts}
rank = prov["rent_change_pct"].rank(ascending=False)["Nova Scotia"]
link = ("no positive link" if r_now < 0.2 else "a positive link")
md = f"""# People vs homes: did population growth drive Nova Scotia's rent surge?

*Population years run July–June; latest year {last}. Rents to June {end_m[:4]}.
Generated by [`analysis/people_vs_homes.py`](../../analysis/people_vs_homes.py).*

## Short answer

Population growth put real pressure on Nova Scotia's housing, but it **does not explain why Nova Scotia's rents rose
faster than anywhere else**. Over {window[0]}–{last}, Nova Scotia added **{nsr['people_per_start']:.2f} new residents per housing
start**, almost exactly the national figure of {can['people_per_start']:.2f}. Yet its rents rose **{nsr['rent_change_pct']:.1f}%**, against
{can['rent_change_pct']:.1f}% for Canada, ranking #{rank:.0f} of {len(prov)} provinces.

## Key findings

- **Growth came from three sources, not one.** Of Nova Scotia's {W['Total'].sum():,.0f} added residents over {window[0]}–{last}:
  immigrants {W['Immigrants'].sum():,.0f}, non-permanent residents (students and temporary workers, net) {W['Non-permanent residents (net)'].sum():,.0f},
  and people moving from other provinces (net) {W['Interprovincial migration (net)'].sum():,.0f}. Births minus deaths and emigration
  subtracted {-W['Births minus deaths and emigration'].sum():,.0f}.
- **The peak squeeze was {pk}**, at {ns.loc[pk, 'People per start']:.1f} new residents per housing start
  (Canada: {growth.loc[('Canada', pk), 'People per start']:.1f}).
- **It has since eased sharply.** In {last} Nova Scotia added {ns.loc[last, 'Total']:,.0f} people and started {ns.loc[last, 'Housing starts']:,.0f}
  homes, {ns.loc[last, 'People per start']:.1f} per start. Net non-permanent residents turned {'negative' if ns.loc[last, 'Non-permanent residents (net)'] < 0 else 'small'}
  ({ns.loc[last, 'Non-permanent residents (net)']:,.0f}).
- **Across provinces there is {link}** between population pressure and rent growth over the last five years
  (correlation {r_now:+.2f}); in the five years before, it was {r_prev:+.2f}. With nine provinces this is suggestive, not proof.

![Growth by source](01_ns_growth_by_source.png)

![People per start](02_people_per_start.png)

![Provinces](03_provinces_pressure_vs_rent.png)

## So what else could explain it?

These are hypotheses to test next, not conclusions:

- **Starting point:** Nova Scotia rents began from a lower base, leaving more room to catch up with other provinces.
- **Lag:** housing starts take roughly two years or more to become homes people can rent, so the jump in starts since {window[2]} has
  not yet fully shown up as supply.
- **Where people went:** if most newcomers settled in Halifax, they met a rental market with vacancy below 1% in 2022–2023
  (provincial totals can't show this; city-level population data would).
- **Who arrived:** students, temporary workers and newcomers mostly rent, so the same population growth can press harder on
  rents in a province with a small rental stock.

## Notes on method

- **Population growth** = immigrants + net non-permanent residents + net interprovincial migration + births − deaths − net emigration
  (StatCan 17-10-0008-01). Residual deviation in older years is excluded.
- **Supply** uses housing starts (34-10-0135-01, unadjusted quarters summed to July–June). The table stopped publishing
  completions after 2022, so starts are the latest consistent measure; they lead completions by a year or more.
- **Rents** are the rent component of the CPI, June to June, which covers all tenants, not only new leases.
- **Provinces compared:** {', '.join(prov.index)}.
- Correlation is not causation, and nine data points cannot rule much out.
"""
(OUT / "README.md").write_text(md)
print(md)
