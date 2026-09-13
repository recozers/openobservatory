# Estimating load from public data: the model

Status: design, 13 Sep 2026. The site currently uses three fixed rules (documented capacity × 0.5–1.0; roofed area ×
density × 0.3–0.9 when an NO₂ plume is active; calibrated NOx flux ÷ emission factor). This document defines the model
those rules are a special case of, so that every evidence source we add moves the estimate in one consistent way,
and so the band on the site is a stated posterior rather than a rule of thumb.

## 1. What is being estimated

IT load in MW per site per quarter, as a 10/50/90 percentile band. Facility load = IT × PUE (site-specific where
documented, otherwise 1.1–1.4 by cooling class). "Utilisation" means IT load ÷ design IT capacity of the halls that
exist. We never claim to observe IT load directly; we observe things that bound it.

## 2. Unit of analysis: the hall

Each hall polygon `h` carries a design IT capacity `D_h` and a construction state `s_h(t)`:

| state | meaning | dated by | validated |
|---|---|---|---|
| S0 pad | earthworks, foundations | Sentinel-2 bare-soil change; Sentinel-1 VV change (cloudy regions); night lights of 24 h construction | S2: Abilene; S1 and lights: pilots running |
| S1 roofed | roof membrane on | Sentinel-2 `roof_on_month` (baseline-relative brightness) | Abilene, 12 halls, ±1 month |
| S2 fitted | rooftop plant installed, roof darkens | Sentinel-2 brightness fall 6–9 months after S1 | Abilene, Colossus |
| S3 energised | substation/yard complete, generators or turbines commissioned | Sentinel-2 yard change; TROPOMI plume test; night lights (pilot) | plume test: Abilene 2.8σ |
| S4 operating | IT load > 0 | only indirectly: NOx flux at self-generating sites, operator or utility disclosure; otherwise inferred from S3 plus elapsed time | Colossus 2 (NOx) |

Transition lags are priors with ranges, not points: S1→S2 6–9 months (Abilene), S2→S4 0–6 months (Abilene; Colossus 1
went from empty shell to 100k GPUs in 122 days, so the lower end is real). A hall that has been in S2 for longer than
the lag range without any S3/S4 evidence keeps the whole 0–1 range on the operating factor: absence of evidence is
recorded, not converted into a claim either way.

`D_h`: documented site IT capacity apportioned by roof area when a document exists; otherwise a density prior in MW/ha
by class (AI training halls at Abilene, Rainier, Prometheus; conventional cloud halls at Prineville; Chinese hub halls
unknown, so the default carries a wide range). Densities are computed in `build_timeline_data.py` from the inventory and
are themselves uncertain by about ±30 %.

## 3. Load model

    IT_site(t) = Σ_h D_h · g(s_h(t)) · u_h(t)

- `g(s)`: 0 for S0–S1; 0–0.2 for S2 (commissioning loads); 0.1–0.6 for S3; 1 for S4.
- `u_h`: utilisation of an operating hall, prior taken from operator disclosures (annual MWh ÷ 8760 ÷ the documented
  figure; `data/operator_disclosures.csv`, `docs/operator_disclosures_notes.md`). Measured so far (13 Sep 2026):

  | site | documented figure | operator-reported average | ratio |
  |---|---|---|---|
  | Meta Luleå | 120 MW grid feed | 30.5 MW (2022), 40.2 MW (2023), 53.5 MW (2024) | 0.25–0.45 |
  | Meta New Albany | 250 MW connection | 90.5 MW (2023), 59.5 MW (2024) | 0.24–0.36 |
  | ORNL Frontier | 21–23 MW at HPL | 11.4 MW (2022), 12.2 MW (2023) | 0.5–0.55 |
  | Meta Prineville | none published | 197 MW (2024), up from 8 MW (2011) | n/a |

  So the site now uses 0.2–0.6 (mid 0.4) of a connection or design figure for cloud campuses, 0.4–0.9 (mid 0.6) of an
  HPL-measured figure for supercomputers, and keeps 0.5–1.0 for AI-training campuses, which have no calibration yet.
  Where an operator reports the year's electricity, the band is that average ±10 %, carried forward for up to 24 months
  at 0.7–1.3 when no newer figure exists. Chinese colocation operators report company-wide utilisation of in-service
  capacity (VNET 70–74 %, GDS 75 %, Chindata 80 % in 2023) but nothing per campus (`docs/cn_operator_disclosures_notes.md`).
- Grid-fed halls: `u_h` is not observable from satellites. The band on the site is the prior, and it says so.

## 4. Evidence and how each enters

Each source has a likelihood; the posterior is sampled by Monte Carlo (10,000 draws per site-quarter) and summarised as
10/50/90 percentiles. The `basis` string on each quarter lists which sources entered.

| evidence | what it constrains | likelihood | status |
|---|---|---|---|
| Documented capacity in force (utility contract, permit, operator statement) | upper bound on facility load; `D_h` | hard cap at document value × 1.0; tier A1/A2 recorded | in use |
| Sentinel-2 roof and fit-out dates | `s_h(t)` | state transitions with the lag priors above | in use |
| TROPOMI NOx flux at a self-generating site, calibrated on EPA-monitored plants | on-site generation `G = F / EF` | `F` ± 30 % relative (calibration scatter) × EF lognormal on the site's permitted range; `G` ≤ facility load; equals it where turbines are the only supply | in use (Colossus 2) |
| TROPOMI plume test (sector change ≥ 2.5σ) | S3 reached | shifts `g` to the S3 range from that quarter | in use (Abilene) |
| Operator annual electricity disclosure | mean IT load over the year | ±10 % on MWh, PUE range | collecting |
| Utility / regulator filing (contracted MW, energisation date) | cap and S3 date | hard cap; S3 at energisation | collecting |
| Chinese listed-operator filings (racks in service, utilisation %) | `u_h`, `D_h` for those campuses | company-reported: entered as tier A2 with ±20 % | collecting |
| VIIRS night lights | S0 activity and S3 energisation | pilot: step timing vs known dates | pilot running |
| Winter snow persistence on halls vs control roofs | S4 on/off in cold climates | pilot: known-state halls vs controls | pilot running |
| Sentinel-1 VV backscatter | S0–S1 in cloudy regions | pilot: vs Sentinel-2 dates at Abilene and the Chinese campuses | pilot running |
| Roof or ground temperature | nothing usable: no response to load at 70 m, day or night | excluded (see the overnight report) | closed |

Official national statistics are not in the table. They can be compared against the posterior as a test of the
statistic, never used to move it.

## 5. What the model can and cannot say

- Construction and its pace: to the month, worldwide, from Sentinel-2 alone; Sentinel-1 where clouds block it.
- Whether a self-generating site is running, and how its generation changes month to month: yes, to about 20 %
  relative, 2–3× absolute.
- Whether a grid-fed hall is running: only from S3 evidence plus time, or from disclosures. The band stays wide and
  the site shows it as "presumably running" with the prior.
- Utilisation inside a running grid-fed hall: not observable with any public satellite data we have tested. Disclosures
  and utility filings are the only sources, at annual or contract resolution.

## 6. Calibration inputs and their status

1. Transition lags: Abilene (12 halls), Colossus 1 and 2, Rainier, Fairwater. Done for S1→S2; S2→S4 needs the disclosure
   and filing dates.
2. Utilisation prior: operator per-site electricity disclosures. Done for Meta (per-site MWh 2011–2024), ORNL (Frontier);
   Google publishes per-site PUE and water but not electricity; Microsoft publishes by metro from FY25; the EU registry
   publishes aggregates only. Amazon publishes nothing per site.
3. Emission factors: EPA CAMPD hourly for grid plants (done, five plants); turbine fleets from permits (Colossus 2 MDEQ:
   0.5–1.5 kg/MWh; Abilene TCEQ 0.14 lb/MWh, below detection). Low-stack calibration plants are Astra task A5.
4. Density priors: recomputed from the inventory each build.

## 7. Implementation plan

- `utilmodel.py`: pure functions `hall_state(dates, t)`, `sample_site(halls, evidence, n=10000)`, returning p10/p50/p90
  and the evidence list; no Earth Engine calls.
- `build_timeline_data.py` calls it per quarter and writes `est_lo/est_mid/est_hi` from the percentiles, keeping the
  present JSON shape so the site needs no change; adds `state_by_hall` and `evidence` arrays.
- `tests/test_utilmodel.py`: a roofed-only hall gives 0 to potential with no midpoint; a documented site gives the prior
  band; an NOx flux above 2σ narrows the band to the generation estimate.
- Switch over only after the disclosure table has at least five site-years so the prior is measured, not assumed.
