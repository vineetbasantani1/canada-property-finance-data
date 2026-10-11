"""Dataset catalogue: what gets downloaded.

StatCan tables are identified by their 8-digit product ID (table 18-10-0205-01 -> 18100205).
Every run writes the official title StatCan returns into data/manifest.json, so a
wrong or retired ID is visible immediately. Use `python fetch_statcan.py --search rent`
to find more tables by keyword.

Provincial coverage: StatCan tables include rows for every province, so Nova Scotia
slices are extracted from the same files (see PROVINCES).
"""

PROVINCES = ["Canada", "Nova Scotia"]

STATCAN_TABLES = {
    # --- Property ---
    "18100205": "New housing price index (monthly)",
    "34100133": "CMHC average rents, areas 10,000+ (annual)",
    "34100127": "CMHC vacancy rates, apartments (annual)",
    "34100135": "CMHC housing starts, under construction and completions (quarterly)",
    "34100292": "Building permits by type of structure (monthly)",
    "46100027": "Canadian Housing Statistics Program: residential property values",
    # --- Household finance & credit ---
    "11100065": "Debt service indicators of households (quarterly)",
    "10100006": "Credit measures, Bank of Canada (monthly)",
    "18100004": "Consumer Price Index, incl. shelter (monthly)",
    # --- Context ---
    "17100009": "Population estimates (quarterly)",
    "17100008": "Components of population growth: immigrants, non-permanent residents, interprovincial (annual)",
    "36100434": "GDP by industry incl. real estate (monthly)",
}

# Provinces kept for cross-province comparisons (New Brunswick excluded by choice)
COMPARISON_PROVINCES = [
    "Newfoundland and Labrador", "Prince Edward Island", "Nova Scotia", "Quebec", "Ontario",
    "Manitoba", "Saskatchewan", "Alberta", "British Columbia",
]

# Tables to also save at province level for every province above (plus Canada).
# Optional column filters keep the files small.
PROVINCE_WIDE = {
    "17100008": {},
    "17100009": {},
    "34100135": {"Type of unit": ["Total units"], "Seasonal adjustment": ["Unadjusted"]},
    "18100004": {"Products and product groups": ["All-items", "Rent", "Shelter"]},
}

# CMHC rental tables kept for every city (outside New Brunswick), for cross-city comparisons
CITY_WIDE = {
    "34100127": {},
    "34100133": {"Type of structure": ["Row and apartment structures of three units and over"],
                 "Type of unit": ["Two bedroom units"]},
}
CITY_EXCLUDE = "New Brunswick"

# Bank of Canada Valet API series (national; rates are not provincial)
BOC_SERIES = {
    "V39079": "Target for the overnight rate",
    "V80691311": "Prime business rate",
    "V80691335": "5-year conventional mortgage rate",
    "BD.CDN.5YR.DQ.YLD": "Government of Canada 5-year bond yield",
    "BD.CDN.10YR.DQ.YLD": "Government of Canada 10-year bond yield",
    "FXUSDCAD": "USD/CAD exchange rate",
}

# Keyword discovery on open-data portals (writes a catalogue, does not bulk-download)
OPEN_DATA_QUERIES = ["housing", "property assessment", "mortgage", "rent", "real estate"]
CKAN_PORTALS = {
    "federal": "https://open.canada.ca/data/api/3/action/package_search",
}
SOCRATA_DOMAINS = {
    "nova_scotia": "data.novascotia.ca",
}
