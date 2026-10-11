"""What drove rent growth? Testing two explanations across Canadian cities.

1. No slack: cities that entered the boom with very low vacancy saw faster rent growth.
2. Catch-up: cities that started with cheaper rents saw faster rent growth.

Uses CMHC Rental Market Survey data (via StatCan) for every city with published
figures in both tables. Writes reports/what-drives-rent/ (charts, CSV, README.md);
every number in the README is computed here.

Run from the repo root:  python analysis/what_drives_rent.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CITIES = Path("data/statcan/cities")
OUT = Path("reports/what-drives-rent")
OUT.mkdir(parents=True, exist_ok=True)

S1 = "#2a78d6"
SURFACE, INK, INK2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#a3a29c"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
})
SOURCE = ("Source: CMHC Rental Market Survey via Statistics Canada (tables 34-10-0127-01, 34-10-0133-01). "
          "Analysis: Vineet Basantani")
FOCUS = "Halifax"


def load(table):
    df = pd.read_csv(CITIES / f"{table}.csv", low_memory=False)
    bad = df["STATUS"].isin(["..", "...", "x", "F"]) | (df["VALUE"] == 0)
    df.loc[bad, "VALUE"] = np.nan
    df = df[df["GEO"].str.contains(",", na=False)]  # cities only, not national totals
    df["REF_DATE"] = df["REF_DATE"].astype(int)
    return df


vac = load("34100127").pivot_table(index="GEO", columns="REF_DATE", values="VALUE")
rent = load("34100133").pivot_table(index="GEO", columns="REF_DATE", values="VALUE")

last = int(min(vac.columns.max(), rent.columns.max()))
base = 2021
pre = [y for y in (2019, 2020, 2021) if y in vac.columns]

d = pd.DataFrame({
    "vacancy_going_in": vac[pre].mean(axis=1),
    "rent_2021": rent[base],
    f"rent_{last}": rent[last],
}).dropna()
d["rent_growth_pct"] = (d[f"rent_{last}"] / d["rent_2021"] - 1) * 100
d.index = d.index.str.split(",").str[0].str.strip()
d = d[~d.index.duplicated()].sort_values("rent_growth_pct", ascending=False)
d.round(2).to_csv(OUT / "cities.csv")
n = len(d)


def fit(x, y):
    slope, intercept = np.polyfit(x, y, 1)
    return slope, intercept, np.corrcoef(x, y)[0, 1]


s_v, i_v, r_v = fit(d["vacancy_going_in"], d["rent_growth_pct"])
s_r, i_r, r_r = fit(d["rent_2021"], d["rent_growth_pct"])
X = np.column_stack([np.ones(n), d["vacancy_going_in"], d["rent_2021"]])
beta, *_ = np.linalg.lstsq(X, d["rent_growth_pct"].values, rcond=None)
pred = X @ beta
r2_both = 1 - ((d["rent_growth_pct"] - pred) ** 2).sum() / ((d["rent_growth_pct"] - d["rent_growth_pct"].mean()) ** 2).sum()


def scatter(xcol, slope, intercept, r, xlabel, title, subtitle, name, xfmt):
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    others = d.drop(index=FOCUS, errors="ignore")
    ax.scatter(others[xcol], others["rent_growth_pct"], s=70, color=MUTED, edgecolor=SURFACE, linewidth=1.8, zorder=3)
    xs = np.linspace(d[xcol].min(), d[xcol].max(), 50)
    ax.plot(xs, slope * xs + intercept, color=INK2, lw=1.2, ls=(0, (5, 3)), zorder=2)
    # label the focus city and the extremes, not every point
    pick = set(d["rent_growth_pct"].nlargest(3).index) | set(d["rent_growth_pct"].nsmallest(2).index) \
        | set(d[xcol].nlargest(2).index) | set(d[xcol].nsmallest(2).index)
    for city in pick - {FOCUS}:
        row = d.loc[city]
        ax.annotate(city, (row[xcol], row["rent_growth_pct"]), xytext=(7, 0), textcoords="offset points",
                    va="center", fontsize=9, color=INK2)
    if FOCUS in d.index:
        f = d.loc[FOCUS]
        ax.scatter([f[xcol]], [f["rent_growth_pct"]], s=130, color=S1, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.annotate(f"{FOCUS}  {f['rent_growth_pct']:.0f}%", (f[xcol], f["rent_growth_pct"]), xytext=(9, 0),
                    textcoords="offset points", va="center", fontsize=11, fontweight="bold")
    ax.xaxis.set_major_formatter(xfmt)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"2-bedroom rent growth, {base}–{last}")
    ax.set_title(title, pad=28)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=11, va="bottom")
    fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=8)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def strength(r):
    a = abs(r)
    return "strong" if a >= 0.6 else "moderate" if a >= 0.4 else "weak" if a >= 0.2 else "no clear"


pre_label = f"{pre[0]}–{pre[-1]}"
v_title = ("Cities with fewer empty apartments saw bigger rent increases" if r_v <= -0.3
           else "Vacancy going in vs. rent growth")
scatter("vacancy_going_in", s_v, i_v, r_v, f"Average apartment vacancy rate, {pre_label} (before the boom)",
        v_title, f"{n} cities; correlation {r_v:+.2f} ({strength(r_v)}). Dashed line = trend",
        "01_vacancy_vs_rent_growth.png", lambda v, _: f"{v:g}%")
r_title = ("Cheaper cities caught up: lower starting rents, faster increases" if r_r <= -0.3
           else "Starting rent vs. rent growth")
scatter("rent_2021", s_r, i_r, r_r, f"Average 2-bedroom rent, {base}",
        r_title, f"{n} cities; correlation {r_r:+.2f} ({strength(r_r)}). Dashed line = trend",
        "02_starting_rent_vs_growth.png", lambda v, _: f"${v:,.0f}")

# ---------- Write-up ----------
f = d.loc[FOCUS] if FOCUS in d.index else None
med = d.median()
rank = int(d["rent_growth_pct"].rank(ascending=False)[FOCUS]) if f is not None else None
vac_rank = int(d["vacancy_going_in"].rank()[FOCUS]) if f is not None else None
lines = []
if f is not None:
    lines.append(f"- **{FOCUS}'s 2-bedroom rent grew {f['rent_growth_pct']:.1f}%** from {base} to {last} "
                 f"(${f['rent_2021']:,.0f} to ${f[f'rent_{last}']:,.0f}), #{rank} of {n} cities; the median city grew {med['rent_growth_pct']:.1f}%.")
    lines.append(f"- **{FOCUS} went in with {f['vacancy_going_in']:.1f}% vacancy** ({pre_label} average), against a median of "
                 f"{med['vacancy_going_in']:.1f}%; #{vac_rank} tightest of {n}.")
lines.append(f"- **Vacancy going in vs. rent growth: correlation {r_v:+.2f}** ({strength(r_v)}). On the trend line, each "
             f"1-point-lower vacancy rate goes with {abs(s_v):.1f} points {'more' if s_v < 0 else 'less'} rent growth.")
lines.append(f"- **Starting rent vs. rent growth: correlation {r_r:+.2f}** ({strength(r_r)}). Each $100 lower starting rent "
             f"goes with {abs(s_r) * 100:.1f} points {'more' if s_r < 0 else 'less'} rent growth.")
lines.append(f"- **Together the two factors account for {r2_both * 100:.0f}% of the variation** in rent growth across cities (R²).")

md = f"""# What drove rent growth? Tight markets and catch-up

*CMHC Rental Market Survey (October each year), {n} cities with published data in both tables.
Generated by [`analysis/what_drives_rent.py`](../../analysis/what_drives_rent.py).*

The [people vs homes](../people-vs-homes/README.md) report found that population pressure doesn't explain why
Nova Scotia's rents rose fastest. This report tests two other explanations across Canadian cities:

1. **No slack:** did cities with fewer empty apartments *before* the boom see bigger rent increases?
2. **Catch-up:** did cities with cheaper rents see bigger increases as they converged on pricier markets?

## Key findings

{chr(10).join(lines)}

![Vacancy vs rent growth](01_vacancy_vs_rent_growth.png)

![Starting rent vs rent growth](02_starting_rent_vs_growth.png)

## Notes on method

- **Rent growth:** average 2-bedroom rent, row and apartment structures of 3+ units (34-10-0133-01), {base} to {last}.
  This covers all tenants, including long-term ones whose rent rises slowly.
- **Vacancy going in:** average apartment vacancy rate over {pre_label} (34-10-0127-01), before the population boom.
- **Cities:** every census metropolitan area with published figures for all three measures; suppressed values are excluded.
  Full list in [`cities.csv`](cities.csv).
- Correlation is not causation. Both factors can share causes, and city-level averages hide neighbourhood differences.
"""
(OUT / "README.md").write_text(md)
print(md)
