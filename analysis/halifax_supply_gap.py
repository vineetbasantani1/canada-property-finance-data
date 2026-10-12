"""Halifax's supply gap: new residents vs finished homes, and the construction pipeline.

Uses StatCan 17-10-0148-01 (population by CMA, July 1) and 34-10-0154-01 (CMHC monthly housing
starts, under construction and completions by CMA). Years run July–June so population growth and
completions cover the same twelve months. Writes reports/halifax-supply-gap/; every number in
the README is computed here.

Run from the repo root:  python analysis/halifax_supply_gap.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CITIES = Path("data/statcan/cities")
OUT = Path("reports/halifax-supply-gap")
OUT.mkdir(parents=True, exist_ok=True)
CITY = "Halifax"
PRE = (2016, 2019)   # pre-boom benchmark years (July-June years starting in these years)
BOOM = (2021, 2023)

S1, S2 = "#B3141B", "#2a78d6"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
})
SOURCE = ("Source: Statistics Canada tables 17-10-0148-01 (population) and 34-10-0154-01 (CMHC housing data). "
          "Analysis: Vineet Basantani")

# ---------- Data ----------
h = pd.read_csv(CITIES / "34100154.csv", low_memory=False)
h = h[h["GEO"].str.startswith(CITY)].copy()
h["date"] = pd.to_datetime(h["REF_DATE"])
h["year"] = h["date"].apply(lambda t: t.year if t.month >= 7 else t.year - 1)  # July-June year
monthly = h.pivot_table(index="date", columns="Housing estimates", values="VALUE")
months = h.groupby("year")["REF_DATE"].nunique()
full_years = months[months == 12].index
yr = h[h["year"].isin(full_years)].groupby(["year", "Housing estimates"])["VALUE"].sum().unstack()

pop = pd.read_csv(CITIES / "17100148.csv", low_memory=False)
pop = pop[pop["GEO"].str.startswith(CITY)].set_index("REF_DATE")["VALUE"].sort_index()
new_res = (pop.shift(-1) - pop).dropna()  # July 1 of year to July 1 of next year

d = pd.DataFrame({"new_residents": new_res, "homes_completed": yr["Housing completions"],
                  "homes_started": yr["Housing starts"]}).dropna()
d = d.loc[2014:]
d["residents_per_home"] = d["new_residents"] / d["homes_completed"]
d.index = [f"{y}/{str(y + 1)[2:]}" for y in d.index]
d.round(2).to_csv(OUT / "halifax_residents_vs_homes.csv")


def window(a, b):
    return d.loc[f"{a}/{str(a + 1)[2:]}":f"{b}/{str(b + 1)[2:]}"]


pre, boom = window(*PRE), window(*BOOM)
pre_ratio = pre["new_residents"].sum() / pre["homes_completed"].sum()
boom_ratio = boom["new_residents"].sum() / boom["homes_completed"].sum()
needed = boom["new_residents"].sum() / pre_ratio
shortfall = needed - boom["homes_completed"].sum()

uc = monthly["Housing under construction"].dropna()
uc_peak_date, uc_peak = uc.idxmax(), uc.max()
uc_2021 = uc.loc["2021-12-01"]
uc_last_date, uc_last = uc.index[-1], uc.iloc[-1]
first_year = int(h["date"].dt.year.min())
starts_all = h[h["year"].isin(full_years)].groupby(["year", "Housing estimates"])["VALUE"].sum().unstack()
rec_start_year = int(starts_all["Housing starts"].idxmax())
rec_starts = starts_all["Housing starts"].max()
latest_year = int(max(full_years))
latest_comp = starts_all.loc[latest_year, "Housing completions"]
prev_comp = starts_all.loc[latest_year - 1, "Housing completions"]
label = lambda y: f"{y}/{str(y + 1)[2:]}"  # noqa: E731

# ---------- Chart 1: new residents vs homes completed ----------
fig, ax = plt.subplots(figsize=(11, 6))
x = np.arange(len(d))
w = 0.38
ax.bar(x - w / 2 - 0.01, d["new_residents"], w, color=S1, label="New residents")
ax.bar(x + w / 2 + 0.01, d["homes_completed"], w, color=S2, label="Homes completed")
peak = d["new_residents"].idxmax()
pi = list(d.index).index(peak)
ax.annotate(f"{d.loc[peak, 'new_residents']:,.0f} people\n{d.loc[peak, 'homes_completed']:,.0f} homes",
            (pi, d.loc[peak, "new_residents"]), xytext=(0, 6), textcoords="offset points", ha="center",
            fontsize=10, fontweight="bold")
ax.set_ylim(0, d["new_residents"].max() * 1.15)
ax.set_xticks(x, d.index, fontsize=9.5)
ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:g}k" if v else "0")
ax.set_ylabel("Per year (July–June)")
ax.legend(frameon=False, loc="upper left")
ax.grid(axis="x", visible=False)
ax.set_title(f"{CITY}: people arrived far faster than homes were finished", pad=28)
ax.text(0, 1.02, f"{label(BOOM[0])} to {label(BOOM[1])}: {boom_ratio:.1f} new residents per completed home, "
        f"vs {pre_ratio:.1f} in {label(PRE[0])}–{label(PRE[1])}", transform=ax.transAxes, color=INK2, fontsize=11, va="bottom")
fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "01_residents_vs_homes.png", dpi=200)
plt.close(fig)

# ---------- Chart 2: homes under construction ----------
fig, ax = plt.subplots(figsize=(11, 5.6))
u = uc.loc["2010":]
ax.plot(u.index, u.values, color=S1, lw=2.2)
ax.fill_between(u.index, u.values, color=S1, alpha=0.08, lw=0)
ax.plot([uc_2021_date := pd.Timestamp("2021-12-01")], [uc_2021], "o", ms=7, color=S1, mec=SURFACE, mew=2)
ax.annotate(f"Dec 2021: {uc_2021:,.0f}", (uc_2021_date, uc_2021), xytext=(-10, 14), textcoords="offset points",
            ha="right", fontsize=10)
ax.plot([uc_peak_date], [uc_peak], "o", ms=7, color=S1, mec=SURFACE, mew=2)
ax.annotate(f"Record {uc_peak:,.0f}\n{uc_peak_date:%b %Y}", (uc_peak_date, uc_peak), xytext=(-16, 6),
            textcoords="offset points", ha="right", va="bottom", fontsize=10, fontweight="bold")
ax.set_ylim(0, uc_peak * 1.15)
ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k" if v else "0")
ax.set_ylabel("Homes under construction")
ax.set_title(f"{CITY} is building at record levels, but homes take years to finish", pad=28)
ax.text(0, 1.02, f"Homes started but not yet completed, monthly. Highest since the series began in {first_year}",
        transform=ax.transAxes, color=INK2, fontsize=11, va="bottom")
fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "02_under_construction.png", dpi=200)
plt.close(fig)

# ---------- Write-up ----------
md = f"""# {CITY}'s supply gap: people arrived faster than homes were finished

*Population: July 1 estimates by census metropolitan area. Homes: CMHC completions, starts and units under
construction. Years run July–June so both cover the same months.
Generated by [`analysis/halifax_supply_gap.py`](../../analysis/halifax_supply_gap.py).*

## Key findings

- **From {label(BOOM[0])} to {label(BOOM[1])}, {CITY} gained {boom['new_residents'].sum():,.0f} residents but completed
  {boom['homes_completed'].sum():,.0f} homes**: {boom_ratio:.1f} new residents per finished home.
- **Before the boom ({label(PRE[0])}–{label(PRE[1])}) the ratio was {pre_ratio:.1f}.** Keeping that pace through the boom
  would have needed about {needed:,.0f} completed homes, roughly **{round(shortfall, -2):,.0f} more** than were finished.
- **Building did ramp up.** Housing starts hit {rec_starts:,.0f} in {label(rec_start_year)}, the most in any year since {first_year}.
- **But homes take years to finish.** Units under construction reached a record **{uc_peak:,.0f}** in {uc_peak_date:%B %Y},
  up from {uc_2021:,.0f} in December 2021. Completions in {label(latest_year)} were {latest_comp:,.0f}, down from {prev_comp:,.0f}
  the year before.
- **Population growth has slowed.** {CITY} added {d['new_residents'].iloc[-1]:,.0f} residents in {d.index[-1]}, against a peak of
  {d['new_residents'].max():,.0f} in {d['new_residents'].idxmax()}. If the record number of homes under construction is
  finished while growth stays slower, the gap would narrow.

![Residents vs homes](01_residents_vs_homes.png)

![Under construction](02_under_construction.png)

## Year by year

| Year (July–June) | New residents | Homes completed | Residents per home |
|---|---:|---:|---:|
""" + "\n".join(f"| {i} | {r.new_residents:,.0f} | {r.homes_completed:,.0f} | {r.residents_per_home:.1f} |"
               for i, r in d.iterrows()) + f"""

## Notes on method

- **New residents** = change in the July 1 population estimate for the Halifax census metropolitan area (2021 boundaries).
- **Homes** count all completed dwellings (houses, apartments, condos), not only rentals.
- **The {pre_ratio:.1f} benchmark** is {CITY}'s own pre-boom pace, not a target. Not every new resident needs a new home:
  a typical home holds more than two people, and newcomers sometimes move into existing homes.
- Latest under-construction figure: {uc_last:,.0f} ({uc_last_date:%B %Y}).
"""
(OUT / "README.md").write_text(md)
print(md)
