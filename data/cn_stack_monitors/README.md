# China stack-monitor source audit

`shengle_2019.csv` through `shengle_2025.csv` contain **annual reported emissions**, nine records per year:
SO2, NOx and particulate mass for unit 1, unit 2 and the whole plant. Units are metric tonnes. The whole-plant
rows overlap the unit rows; do not sum all three scopes. These files contain **no hourly or daily readings**.

The annual reports and 2026 monitoring plan are retained in `sources/`, with hashes and original download URLs
in `../cn_stack_monitor_sources.json`. PDF page numbers are one-based physical pages. 2023 was read from the
scanned PDF, page 15. Other annual mass figures appear in section V. The portal's 2019 listing title includes
“测试”; the PDF itself is the 2019 company report. That metadata anomaly remains noted on every 2019 row.

The 2024 NOx report says unit 1 = 282.47 t, unit 2 = 319.13 t and total = 606.6 t. The units sum to **601.60 t**.
All original values remain, flagged `source_total_mismatch`; no value was silently repaired.

`shengle_auto_access_response.json` is the response to one public automatic-monitor query for August 2026.
It is an access result, not a reading. The server requires a CAPTCHA. No CAPTCHA was solved or bypassed.
The listed 2018 annual-report attachment returned “file does not exist (not yet synchronised)”, so no 2018
observations were created. Missing readings, outlet IDs and flow rates are not zeros.

Run `python tools/cn_stack_monitors.py` to check report hashes, periods, units, duplicates, arithmetic and flags.
See `../../docs/cn_stack_monitors.md` for the eleven-hub attribution and nine-region access audit.
