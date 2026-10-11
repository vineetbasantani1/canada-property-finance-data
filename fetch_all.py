import sys

import discover_open_data
import fetch_boc
import fetch_statcan
from sources import STATCAN_TABLES

failed = fetch_statcan.main(list(STATCAN_TABLES)) + fetch_boc.main()
discover_open_data.main()
# Fail the run only if nothing came down at all
sys.exit(1 if len(failed) == len(STATCAN_TABLES) + len(fetch_boc.BOC_SERIES) else 0)
