"""Compare saved tall-coal and provisional gas calibration data, without publishing a new factor.

    python tools/compare_stack_calibration.py

EPA hours are local standard time. Report both the historical 19/20 local
selection and UTC 19/20 converted to local standard time. The latter remains
an overpass-time proxy; daily satellite timestamps are not stored in profiles.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from no2_flux_quarterly import CAL_PLANTS, plateau_series
from no2_flux import MW_NO2, NOX_NO2

CANDIDATES = {'forney_gas': (55480, -6), 'fort_myers_gas': (612, -5), 'midland_gas': (10745, -5)}


def main():
    records, missing = [], []
    annual = pd.read_json(ROOT / 'results_no2/campd_annual_screen_2023.json')
    for key, (fid, offset) in ({k: (v, -6) for k, v in CAL_PLANTS.items()} | CANDIDATES).items():
        campd_path = ROOT / 'data/campd' / f'{fid}_2023.csv'
        flux_path = ROOT / 'results_no2' / f'flux_{key}_2023.csv'
        if not campd_path.exists() or not flux_path.exists() or campd_path.stat().st_size < 10:
            missing.append(key)
            continue
        df = pd.read_csv(campd_path)
        df['noxMass'] = pd.to_numeric(df.noxMass, errors='coerce')
        if df.duplicated(['date', 'hour', 'unitId']).any():
            raise ValueError(f'Duplicate unit-hours: {key}')
        expected = annual[annual.facilityId == fid].noxMass.sum()
        total = df.noxMass.sum() / 2000
        if key in CANDIDATES and not np.isclose(total, expected, rtol=.001, atol=.1):
            raise ValueError(f'{key}: hourly total {total} does not reconcile to annual {expected}')
        truth = df.groupby(['date','hour']).noxMass.sum().reset_index()
        satellite = plateau_series(flux_path) * NOX_NO2 * MW_NO2 * 3600
        for window, hours in [('legacy_local_19_20', [19,20]), ('utc_19_20_proxy_in_local_standard_time', [19+offset,20+offset])]:
            hourly = truth[truth.hour.isin(hours)].groupby('date').noxMass.agg(['mean','count'])
            hourly = hourly[hourly['count'] == len(hours)]
            hourly.index = pd.to_datetime(hourly.index)
            joined = pd.concat([satellite.rename('sat'), (hourly['mean']*.45359237).rename('truth')], axis=1).dropna()
            sat, ground = joined.sat.mean(), joined.truth.mean()
            se = joined.sat.std() / np.sqrt(len(joined))
            records.append(dict(plant=key, facility_id=fid, stack_class='gas_turbine_candidate_unverified_height' if key in CANDIDATES else 'tall_coal_reference',
                                time_window=window, campd_local_hours='|'.join(map(str,hours)), days=len(joined),
                                annual_nox_short_tons=total, truth_kgh=ground, satellite_kgh=sat, satellite_se=se,
                                factor=ground/sat if sat > 0 else None,
                                factor_se=abs(ground*se/(sat*sat)) if sat > 0 else None,
                                used_by_existing_production=key not in CANDIDATES and window=='legacy_local_19_20'))
    pd.DataFrame(records).to_csv(ROOT / 'results_no2/calibration_stack_comparison.csv', index=False)
    print(pd.DataFrame(records).round(3).to_string(index=False))
    print('Missing:', missing, file=sys.stderr)
    if missing:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
