"""What actually drove rent increases? Population growth, building, and rental supply across cities.

For every city with published data, compares the dollar increase in average 2-bedroom rent
(2021 to latest October survey) with:
  - population growth over the same period (demand)
  - new homes per 1,000 residents (supply; completions when published, otherwise starts)
  - growth in the number of rental units (rental supply), when StatCan publishes it
  - the 2021 rent level (control)
Each factor's effect is estimated in one regression so the others are held constant.

Writes reports/real-rent-factors/; every number in the README is computed here.
Run from the repo root:  python analysis/real_rent_factors.py
"""
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CITIES = Path("data/statcan/cities")
OUT = Path("reports/real-rent-factors")
OUT.mkdir(parents=True, exist_ok=True)
FOCUS = "Halifax"
BASE = 2021

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
STD_COLS = {"REF_DATE", "GEO", "DGUID", "UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR",
            "COORDINATE", "VALUE", "STATUS", "SYMBOL", "TERMINATED", "DECIMALS"}


def city_name(geo):
    name = re.sub(r"\s*\((CMA|CA)\)", "", str(geo)).split(",")[0]
    return re.sub(r"\s*-\s*", "-", name).strip()


def load(table, prefer=None):
    """Load a city table, reduce extra dimensions to one value each, return (df, notes)."""
    path = CITIES / f"{table}.csv"
    df = pd.read_csv(path, low_memory=False)
    bad = df["STATUS"].isin(["..", "...", "x", "F"]) if "STATUS" in df else False
    df.loc[bad, "VALUE"] = np.nan
    df = df[df["GEO"].astype(str).str.contains(",", na=False)].copy()
    prefer = prefer or {}
    for col in [c for c in df.columns if c not in STD_COLS]:
        vals = df[col].dropna().unique()
        if len(vals) <= 1:
            continue
        pattern = prefer.get(col, r"^Total|^All ")
        keep = [v for v in vals if re.search(pattern, str(v), re.I)]
        if not keep:
            raise ValueError(f"{table}: can't choose a value for column '{col}' from {list(vals)[:12]}")
        df = df[df[col] == keep[0]]
    df["city"] = df["GEO"].map(city_name)
    df["year"] = df["REF_DATE"].astype(str).str[:4].astype(int)
    return df


def annual_sum(df):
    """Sum monthly/quarterly values to calendar years, keeping only complete years."""
    per = df.groupby(["city", "year"])["VALUE"].agg(["sum", "count"])
    full = per["count"].groupby(level="year").transform("max")
    return per.loc[per["count"] == full, "sum"].unstack()


manifest = json.loads(Path("data/manifest.json").read_text()) if Path("data/manifest.json").exists() else {}
catalog = Path("data/catalog/statcan_candidates.csv")
cands = pd.read_csv(catalog) if catalog.exists() else pd.DataFrame(columns=["target", "chosen", "productId", "title"])


def discovered(target):
    row = cands[(cands["target"] == target) & (cands["chosen"])]
    pid = str(int(row["productId"].iloc[0])) if len(row) else None
    return pid if pid and (CITIES / f"{pid}.csv").exists() else None


# ---------- Rent (outcome) ----------
rent = load("34100133")
rent = rent.groupby(["city", "year"])["VALUE"].mean().unstack()
last = int(rent.columns.max())
d = pd.DataFrame({"rent_2021": rent[BASE], f"rent_{last}": rent[last]})
d["rent_increase"] = d[f"rent_{last}"] - d["rent_2021"]

# ---------- Population (demand) ----------
pop = load("17100148").groupby(["city", "year"])["VALUE"].sum().unstack()
p_last = max(y for y in pop.columns if y <= last)
d["pop_2021"] = pop[BASE]
d["pop_growth_pct"] = (pop[p_last] / pop[BASE] - 1) * 100
d["new_residents"] = pop[p_last] - pop[BASE]

# ---------- New homes (supply) ----------
supply_note = None
starts_pid = "34100154" if (CITIES / "34100154.csv").exists() else discovered("city_housing_starts")
if starts_pid:
    hs_raw = pd.read_csv(CITIES / f"{starts_pid}.csv", low_memory=False)
    est_col = next((c for c in hs_raw.columns if "estimate" in c.lower()), None)
    measure = "starts"
    if est_col and hs_raw[est_col].str.contains("completion", case=False, na=False).any():
        measure = "completions"
    prefer = {est_col: measure} if est_col else {}
    hs = annual_sum(load(starts_pid, prefer))
    years = [y for y in range(BASE, last) if y in hs.columns]
    d["new_homes"] = hs[years].sum(axis=1)
    d["homes_per_1000"] = d["new_homes"] / d["pop_2021"] * 1000
    supply_note = (f"housing {measure} in calendar years {years[0]}–{years[-1]} "
                   f"(StatCan {starts_pid[:2]}-{starts_pid[2:4]}-{starts_pid[4:]}-01)")

# ---------- Rental units (rental supply) ----------
rental_note = None
rpid = discovered("rental_units")
if rpid:
    try:
        ru = load(rpid).groupby(["city", "year"])["VALUE"].sum().unstack()
        r_last = max(y for y in ru.columns if y <= last)
        d["rental_units_growth_pct"] = (ru[r_last] / ru[BASE] - 1) * 100
        rental_note = f"rental units {BASE}–{r_last}, StatCan table {rpid} ({cands.loc[cands['productId'] == int(rpid), 'title'].iloc[0]})"
    except Exception as e:  # rental data is optional
        print(f"Skipping rental units: {e}")

factors = {
    "pop_growth_pct": "Population growth (%)",
    "homes_per_1000": "New homes per 1,000 residents",
    "rental_units_growth_pct": "Growth in rental units (%)",
    "rent_2021": f"Starting rent ({BASE})",
}
factors = {k: v for k, v in factors.items() if k in d}
d = d.dropna(subset=["rent_increase", *factors])
d = d[~d.index.duplicated()]
n = len(d)
if n < 12:
    raise SystemExit(f"Only {n} cities matched across tables; check city names. Rent cities: {sorted(rent.index)[:10]}...")
d.round(2).sort_values("rent_increase", ascending=False).to_csv(OUT / "cities.csv")
print(f"{n} cities matched")

# ---------- Regression: standardized effects with 95% intervals ----------
y = d["rent_increase"].values
Z = (d[list(factors)] - d[list(factors)].mean()) / d[list(factors)].std()
X = np.column_stack([np.ones(n), Z.values])
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
resid = y - X @ beta
dof = n - X.shape[1]
sigma2 = resid @ resid / dof
se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
tcrit = next(v for k, v in [(60, 2.000), (40, 2.021), (30, 2.042), (25, 2.060), (20, 2.086), (15, 2.131), (10, 2.228), (0, 2.5)] if dof >= k)
r2 = 1 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))
effects = pd.DataFrame({"label": list(factors.values()), "effect": beta[1:], "low": beta[1:] - tcrit * se[1:],
                        "high": beta[1:] + tcrit * se[1:]}, index=list(factors))
effects["clear"] = (effects["low"] > 0) | (effects["high"] < 0)
effects.round(1).to_csv(OUT / "effects.csv")
d["predicted_increase"] = X @ beta
corr = {k: d[k].corr(d["rent_increase"]) for k in factors}

SOURCE = "Source: CMHC Rental Market Survey and Statistics Canada population estimates. Analysis: Vineet Basantani"


def finish(fig, ax, name, subtitle, size=8):
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=11, va="bottom")
    fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=size)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def scatter(xcol, xlabel, title, name, xfmt):
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    others = d.drop(index=FOCUS, errors="ignore")
    ax.scatter(others[xcol], others["rent_increase"], s=70, color=MUTED, edgecolor=SURFACE, linewidth=1.8, zorder=3)
    slope, icept = np.polyfit(d[xcol], d["rent_increase"], 1)
    xs = np.linspace(d[xcol].min(), d[xcol].max(), 50)
    ax.plot(xs, slope * xs + icept, color=INK2, lw=1.2, ls=(0, (5, 3)), zorder=2)
    pick = set(d["rent_increase"].nlargest(4).index) | set(d["rent_increase"].nsmallest(2).index) \
        | set(d[xcol].nlargest(2).index) | set(d[xcol].nsmallest(1).index)
    for city in pick - {FOCUS}:
        r = d.loc[city]
        ax.annotate(city, (r[xcol], r["rent_increase"]), xytext=(7, 0), textcoords="offset points", va="center", fontsize=9, color=INK2)
    if FOCUS in d.index:
        f = d.loc[FOCUS]
        ax.scatter([f[xcol]], [f["rent_increase"]], s=130, color=S1, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.annotate(f"{FOCUS}  +${f['rent_increase']:,.0f}", (f[xcol], f["rent_increase"]), xytext=(9, 0),
                    textcoords="offset points", va="center", fontsize=11, fontweight="bold")
    ax.xaxis.set_major_formatter(xfmt)
    ax.yaxis.set_major_formatter(lambda v, _: f"+${v:,.0f}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(f"Increase in average 2-bedroom rent, {BASE}–{last} ($/month)")
    ax.set_title(title, pad=28)
    finish(fig, ax, name, f"{n} cities; correlation {corr[xcol]:+.2f}. Dashed line = trend")


def strength(r):
    a = abs(r)
    return "strong" if a >= 0.6 else "moderate" if a >= 0.4 else "weak" if a >= 0.2 else "no clear"


pg = corr["pop_growth_pct"]
scatter("pop_growth_pct", f"Population growth, {BASE}–{p_last}",
        "Cities that grew faster saw bigger rent increases" if pg >= 0.3 else "Population growth vs. rent increases",
        "01_population_vs_rent.png", lambda v, _: f"{v:g}%")
if "homes_per_1000" in d:
    hc = corr["homes_per_1000"]
    scatter("homes_per_1000", f"New homes per 1,000 residents ({supply_note.split(' (')[0]})",
            "More building went with smaller rent increases" if hc <= -0.3 else "New building vs. rent increases",
            "02_building_vs_rent.png", lambda v, _: f"{v:g}")

# Effects chart
fig, ax = plt.subplots(figsize=(10, 1.1 * len(effects) + 2.2))
e = effects.iloc[::-1]
ypos = np.arange(len(e))
for i, (_, row) in enumerate(e.iterrows()):
    color = S1 if row["clear"] else MUTED
    ax.plot([row["low"], row["high"]], [i, i], color=color, lw=2.2, solid_capstyle="round")
    ax.scatter([row["effect"]], [i], s=90, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.annotate(f"{row['effect']:+.0f} $/mo", (row["effect"], i), xytext=(0, 11), textcoords="offset points",
                ha="center", fontsize=10, fontweight="bold" if row["clear"] else "normal")
ax.axvline(0, color=INK2, lw=1)
ax.set_yticks(ypos, e["label"])
ax.set_ylim(-0.6, len(e) - 0.3)
ax.grid(axis="y", visible=False)
ax.xaxis.set_major_formatter(lambda v, _: f"{v:+.0f}" if v else "0")
ax.set_xlabel("Change in rent increase ($/month) for a typical difference between cities (1 standard deviation)")
fig.text(0.01, 0.975, "What mattered most, holding the other factors equal", fontsize=15, fontweight="bold", va="top")
fig.text(0.01, 0.975 - 0.42 / fig.get_figheight(), f"{n} cities. Dot = estimate, line = 95% range, blue = clearly not zero. "
         f"Model explains {r2 * 100:.0f}% of the differences", fontsize=11, color=INK2, va="top")
fig.text(0.01, 0.01, SOURCE, color=INK2, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1 - 0.8 / fig.get_figheight()))
fig.savefig(OUT / "03_what_mattered.png", dpi=200)
plt.close(fig)

# ---------- Write-up ----------
f = d.loc[FOCUS] if FOCUS in d.index else None
med = d.median(numeric_only=True)
eff_lines = []
for k, row in effects.iterrows():
    sd = d[k].std()
    unit = {"pop_growth_pct": f"{sd:.1f} points more population growth", "homes_per_1000": f"{sd:.1f} more new homes per 1,000 residents",
            "rental_units_growth_pct": f"{sd:.1f} points more rental-unit growth", "rent_2021": f"${sd:,.0f} higher starting rent"}[k]
    verdict = "a clear effect" if row["clear"] else "not clearly different from zero"
    eff_lines.append(f"- **{row['label']}:** {unit} went with **{row['effect']:+,.0f} $/month** in rent increase "
                     f"(95% range {row['low']:+,.0f} to {row['high']:+,.0f}): {verdict}.")
top = effects.assign(a=effects["effect"].abs()).sort_values("a", ascending=False)
top_clear = top[top["clear"]]
headline = (f"{top_clear['label'].iloc[0].split(' (')[0]} mattered most" if len(top_clear)
            else "No single factor stands out")

focus_lines = []
if f is not None:
    focus_lines.append(f"- **{FOCUS}: rent +${f['rent_increase']:,.0f}/month** (${f['rent_2021']:,.0f} to ${f[f'rent_{last}']:,.0f}), "
                       f"#{int(d['rent_increase'].rank(ascending=False)[FOCUS])} of {n}; median city +${med['rent_increase']:,.0f}.")
    focus_lines.append(f"- **{FOCUS}'s population grew {f['pop_growth_pct']:.1f}%** ({BASE}–{p_last}), "
                       f"#{int(d['pop_growth_pct'].rank(ascending=False)[FOCUS])} of {n}; median {med['pop_growth_pct']:.1f}%.")
    if "homes_per_1000" in d:
        focus_lines.append(f"- **{FOCUS} added {f['homes_per_1000']:.0f} new homes per 1,000 residents**, "
                           f"#{int(d['homes_per_1000'].rank(ascending=False)[FOCUS])} of {n}; median {med['homes_per_1000']:.0f}.")
    focus_lines.append(f"- **The model predicts +${f['predicted_increase']:,.0f}/month for {FOCUS}**; the actual was "
                       f"+${f['rent_increase']:,.0f}.")

charts = "![Population vs rent](01_population_vs_rent.png)\n\n"
if "homes_per_1000" in d:
    charts += "![Building vs rent](02_building_vs_rent.png)\n\n"
charts += "![What mattered](03_what_mattered.png)"

md = f"""# What actually drove rent increases? {headline}

*{n} cities, CMHC October rental survey {BASE}–{last}. Rent change is measured in **dollars per month**, so cheaper
cities don't look faster just because they started lower.
Generated by [`analysis/real_rent_factors.py`](../../analysis/real_rent_factors.py).*

## The factors, tested together

Each factor's effect is estimated with the others held constant (one regression across all {n} cities).
Together they explain **{r2 * 100:.0f}%** of the differences in rent increases between cities.

{chr(10).join(eff_lines)}

## {FOCUS}

{chr(10).join(focus_lines)}

{charts}

## Notes on method

- **Rent increase:** average 2-bedroom rent, row and apartment structures of 3+ units (34-10-0133-01), October {BASE} to October {last}.
- **Population growth:** July 1 estimates by census metropolitan area, 2021 boundaries (17-10-0148-01), {BASE} to {p_last}.
- **New homes:** {supply_note or 'not available in this run'}, per 1,000 residents in {BASE}. Homes started near the end of the
  window may not be finished yet.
- **Rental units:** {rental_note or 'StatCan did not publish a matching city-level table in this run, so this factor is left out'}.
- **Effects** are per one standard deviation of each factor (a typical difference between two cities), with 95% ranges.
  With {n} cities, ranges are wide; a factor "not clearly different from zero" may still matter, the data just can't show it.
- Correlation is not causation: a city can attract people *and* raise rents for a shared reason, such as job growth.
"""
(OUT / "README.md").write_text(md)
print(md)
