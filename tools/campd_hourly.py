"""Fetch EPA Clean Air Markets hourly unit-level emissions for a facility-year (EPA_API_KEY from api.data.gov).
    python tools/campd_hourly.py <facilityId> <year>   -> data/campd/<facilityId>_<year>.csv
"""
import os, sys, time, requests, pandas as pd
def fetch(fac, year, key):
    h = {"x-api-key": key}; rows = []
    for m in range(1, 13):
        start = f"{year}-{m:02d}-01"; end = (pd.Timestamp(start) + pd.offsets.MonthEnd(0)).strftime("%Y-%m-%d"); page = 1
        while True:
            r = requests.get("https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/hourly",
                             params={"beginDate": start, "endDate": end, "facilityId": fac, "page": page, "perPage": 500}, headers=h, timeout=120)
            if r.status_code != 200:
                print("status", r.status_code, r.text[:120], file=sys.stderr); break
            items = r.json(); items = items.get("items", items) if isinstance(items, dict) else items
            rows += items
            if len(items) < 500: break
            page += 1; time.sleep(0.15)
    return pd.DataFrame(rows)
if __name__ == "__main__":
    fac, year = int(sys.argv[1]), int(sys.argv[2])
    df = fetch(fac, year, os.environ["EPA_API_KEY"]); os.makedirs("data/campd", exist_ok=True)
    df.to_csv(f"data/campd/{fac}_{year}.csv", index=False); print(f"{fac} {year}: {len(df)} unit-hours", file=sys.stderr)
