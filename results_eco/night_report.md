# Night-time report

16780 ECOSTRESS rows, 6968 hall frames over 21 sites; 2662 night frames (sun < -6 deg), 2836 day frames (sun > 20 deg).

## 1. Sites: night vs day anomaly, diurnal amplitude

| site_id                | control   | tier   |   frames |   night |   day |   night_per_year |   night_dT |   night_sd |   day_dT |   day_sd |   diurnal_amp |   peak_hour |   night_resid_sd |   landsat_day_dT | first   | last    |
|:-----------------------|:----------|:-------|---------:|--------:|------:|-----------------:|-----------:|-----------:|---------:|---------:|--------------:|------------:|-----------------:|-----------------:|:--------|:--------|
| colossus_memphis       | False     | A1     |      263 |      80 |   119 |             17.2 |      -0.75 |       1.49 |     2.81 |     2.73 |          2.29 |        12.6 |             1.32 |             3.55 | 2022-01 | 2026-08 |
| fairwater_wi           | False     | A2     |      106 |      33 |    50 |             26.4 |       0.44 |       0.69 |    -0.28 |     1.65 |          0.59 |        23.1 |             0.65 |            -1.58 | 2025-06 | 2026-09 |
| hyperion_la            | False     | U      |       37 |      13 |    18 |             20   |       1.17 |       1.42 |     3.74 |     3.98 |          1.74 |        12.6 |             0.83 |             7.63 | 2026-01 | 2026-08 |
| nsa_utah               | False     | A1     |      742 |     301 |   302 |             37.3 |       0.19 |       0.92 |    -0.24 |     1.34 |          0.3  |        23.7 |             0.89 |            -1.79 | 2018-08 | 2026-08 |
| nscc_guangzhou         | False     | A1     |       87 |      37 |    30 |              4.6 |       0.53 |       1.68 |    -0.68 |     1.71 |          0.8  |        23.9 |             1.66 |            -1.1  | 2018-08 | 2026-08 |
| nscc_wuxi              | False     | A1     |      145 |      41 |    65 |              5.1 |       0.5  |       0.77 |     0.41 |     1.74 |          0.07 |        23   |             0.81 |            -0.2  | 2018-08 | 2026-08 |
| ornl_olcf              | False     | A1     |      496 |     193 |   202 |             23.9 |      -0.21 |       1.07 |     3.27 |     2.58 |          2.2  |        13.2 |             1.03 |             5.4  | 2018-08 | 2026-08 |
| prineville             | False     | U      |      916 |     357 |   351 |             44.1 |       0.95 |       2.52 |    -0.27 |     1.78 |          0.92 |        22.1 |             2.38 |            -0.85 | 2018-07 | 2026-09 |
| prometheus_oh          | False     | A2     |      366 |     150 |   136 |             32.2 |       0.45 |       0.84 |     1.74 |     2.6  |          0.84 |        14   |             0.78 |             3.91 | 2022-01 | 2026-09 |
| rainier_in             | False     | A2     |      137 |      45 |    68 |             27.2 |       0.32 |       0.86 |     1.98 |     2.85 |          1.1  |        14   |             0.67 |             3.14 | 2025-01 | 2026-08 |
| riken_kobe             | False     | A1     |      315 |     157 |   103 |             19.4 |      -0.53 |       1.79 |     0.49 |     1.7  |          0.51 |        12.8 |             1.82 |            -0.09 | 2018-08 | 2026-08 |
| stargate_abilene       | False     | A2     |      399 |     143 |   170 |             30.7 |      -0.1  |       1.04 |    -0.43 |     2.33 |          0.16 |         0.7 |             0.99 |            -0.88 | 2022-01 | 2026-09 |
| ctrl_abilene_a         | True      | U      |      385 |     135 |   171 |             29   |       0.09 |       0.91 |     1.12 |     2.39 |          0.81 |        14.6 |             0.86 |             1.9  | 2022-01 | 2026-09 |
| ctrl_memphis_a         | True      | U      |      278 |      85 |   128 |             18.3 |       2.04 |       1.6  |     4.31 |     2.93 |          1.48 |        13   |             1.57 |             6.6  | 2022-01 | 2026-08 |
| ctrl_memphis_navy      | True      | U      |      278 |      87 |   127 |             18.7 |      -0.06 |       1.34 |     1.48 |     2.78 |          1.04 |        13.5 |             1.3  |             0.53 | 2022-01 | 2026-08 |
| ctrl_newalbany_af      | True      | U      |      336 |     135 |   130 |             29   |      -0.14 |       1.04 |     7.94 |     5.89 |          4.63 |        12   |             1.03 |            19.97 | 2022-01 | 2026-09 |
| ctrl_newalbany_dsv     | True      | U      |      345 |     140 |   132 |             30   |       0.04 |       0.66 |     1.03 |     2.38 |          0.57 |        12.5 |             0.65 |             1.91 | 2022-01 | 2026-09 |
| ctrl_newcarlisle_mfg   | True      | U      |      295 |     100 |   138 |             21.5 |      -0.27 |       1.19 |     0.26 |     2.81 |          0.48 |        11.9 |             1.17 |            -0.52 | 2022-01 | 2026-08 |
| ctrl_prineville_schwab | True      | U      |      295 |     149 |    73 |             32.1 |      -1.48 |       1.94 |    -5.13 |     2.32 |          1.76 |         0.8 |             1.92 |            -4.68 | 2022-01 | 2026-08 |
| ctrl_racine_b          | True      | U      |      371 |     139 |   164 |             29.8 |      -0.07 |       0.65 |     5.91 |     4.87 |          3.7  |        12.2 |             0.63 |            12.69 | 2022-01 | 2026-09 |
| ctrl_racine_mke1       | True      | U      |      376 |     142 |   159 |             30.5 |       0.64 |       1.05 |     1.59 |     2.5  |          0.57 |        13.2 |             0.95 |             2.73 | 2022-01 | 2026-09 |

## 2. Within-site steps where the documented load changed

- **colossus_memphis / night** (n=80, ref 0.5 MW; frames per level {'0.5': 47, '125.0': 33}): 125.0 MW: +1.24 ± 0.28 K (p=0.000); slope +0.0099 ± 0.0022 K per IT-MW (p=0.000)
- **colossus_memphis / day** (n=119, ref 0.5 MW; frames per level {'0.5': 63, '125.0': 56}): 125.0 MW: +2.00 ± 0.38 K (p=0.000); slope +0.0160 ± 0.0030 K per IT-MW (p=0.000)
- **fairwater_wi / night** (n=33, ref 0.5 MW; frames per level {'0.5': 29, '347.8': 4}): 347.8 MW: +0.08 ± 0.43 K (p=0.852); slope +0.0002 ± 0.0012 K per IT-MW (p=0.852)
- **fairwater_wi / day** (n=50, ref 0.5 MW; frames per level {'0.5': 28, '347.8': 22}): 347.8 MW: +1.35 ± 0.49 K (p=0.009); slope +0.0039 ± 0.0014 K per IT-MW (p=0.009)
- **ornl_olcf / night** (n=193, ref 10.1 MW; frames per level {'10.1': 85, '17.0': 6, '24.6': 51, '31.2': 23, '32.8': 20, '32.9': 8}): 17.0 MW: +0.75 ± 0.44 K (p=0.094); 24.6 MW: +0.23 ± 0.19 K (p=0.224); 31.2 MW: +0.39 ± 0.25 K (p=0.115); 32.8 MW: -0.14 ± 0.26 K (p=0.594); 32.9 MW: -0.04 ± 0.39 K (p=0.918); slope +0.0062 ± 0.0082 K per IT-MW (p=0.449)
- **ornl_olcf / day** (n=202, ref 10.1 MW; frames per level {'10.1': 71, '17.0': 10, '24.6': 55, '31.2': 33, '32.8': 17, '32.9': 16}): 17.0 MW: +0.46 ± 0.59 K (p=0.443); 24.6 MW: +0.00 ± 0.31 K (p=0.995); 31.2 MW: -0.06 ± 0.37 K (p=0.870); 32.8 MW: -0.92 ± 0.47 K (p=0.053); 32.9 MW: +1.30 ± 0.49 K (p=0.008); slope +0.0008 ± 0.0137 K per IT-MW (p=0.955)
- **rainier_in / night** (n=45, ref 0.5 MW; frames per level {'0.5': 21, '1078.3': 24}): 1078.3 MW: +0.06 ± 0.24 K (p=0.811); slope +0.0001 ± 0.0002 K per IT-MW (p=0.811)
- **rainier_in / day** (n=68, ref 0.5 MW; frames per level {'0.5': 31, '1078.3': 37}): 1078.3 MW: +1.44 ± 0.60 K (p=0.020); slope +0.0013 ± 0.0006 K per IT-MW (p=0.020)
- **riken_kobe / night** (n=139, ref 12.7 MW; frames per level {'12.7': 6, '29.9': 133}): 29.9 MW: -0.14 ± 0.82 K (p=0.862); slope -0.0083 ± 0.0474 K per IT-MW (p=0.862)
- **riken_kobe / day** (n=96, ref 12.7 MW; frames per level {'12.7': 9, '29.9': 87}): 29.9 MW: +0.65 ± 0.61 K (p=0.291); slope +0.0376 ± 0.0354 K per IT-MW (p=0.291)
- **stargate_abilene / night** (n=143, ref 0.5 MW; frames per level {'0.5': 113, '173.9': 25, '521.7': 5}): 173.9 MW: +0.16 ± 0.23 K (p=0.494); 521.7 MW: +0.13 ± 0.47 K (p=0.789); slope +0.0004 ± 0.0008 K per IT-MW (p=0.559)
- **stargate_abilene / day** (n=170, ref 0.5 MW; frames per level {'0.5': 126, '173.9': 30, '521.7': 14}): 173.9 MW: +0.03 ± 0.49 K (p=0.947); 521.7 MW: -0.14 ± 0.68 K (p=0.842); slope -0.0002 ± 0.0012 K per IT-MW (p=0.874)

## 3. Cross-site fit, night-only vs day-only frames (model.py)

### night
```
=== fit on all frames (Tier A) ===
slope on density: 0.0105 ± 0.0080  (re_sd 0.56 K, resid_sd 1.17 K, mixedlm, converged=True)
partial R²: capacity 0.005 | met 0.016 | between-site share 0.091
LOSO median factor: thermal 1305.32× (9 of 10 folds unidentified) | geometry 6.15× | constant 12.92×
=== conditioned ===  LOSO median factor: thermal 6.37× (6 unidentified) | geometry 9.56× | constant 8.34× (n=395 frames, 9 sites)
kill 1 (LOSO not better than geometry): True | kill 2 (met > capacity): True -> negative_result
within-site colossus_memphis: +0.0114 ± 0.0023 K/MW (p=0.000) | 0.5 MW: -1.31 K (n=47); 125.0 MW: +0.03 K (n=33)
within-site fairwater_wi: +0.0007 ± 0.0013 K/MW (p=0.566) | 0.5 MW: +0.40 K (n=29); 347.8 MW: +0.74 K (n=4)
within-site ornl_olcf: +0.0062 ± 0.0079 K/MW (p=0.435) | 10.1 MW: -0.32 K (n=85); 17.0 MW: +0.45 K (n=6); 24.6 MW: -0.13 K (n=51); 31.2 MW: +0.04 K (n=23); 32.8 MW: -0.38 K (n=20); 32.9 MW: -0.38 K (n=8)
within-site rainier_in: -0.0000 ± 0.0002 K/MW (p=0.924) | 0.5 MW: +0.40 K (n=21); 1078.3 MW: +0.25 K (n=24)
within-site riken_kobe: -0.0047 ± 0.0460 K/MW (p=0.919) | 12.7 MW: -0.49 K (n=6); 29.9 MW: -0.57 K (n=133)
within-site stargate_abilene: +0.0007 ± 0.0008 K/MW (p=0.394) | 0.5 MW: -0.16 K (n=113); 173.9 MW: +0.16 K (n=25); 521.7 MW: -0.08 K (n=5)
         site_id  n_frames  truth_mw  thermal_identified  thermal_raw_mw  geometry_mw  const_mw  slope  slope_se
colossus_memphis        80     0.500               False        2812.138        5.926     7.587 -0.004     0.008
    fairwater_wi        33     0.500               False        1311.913        4.663     7.587  0.011     0.008
        nsa_utah       301    50.000               False         361.794        4.159     4.548  0.010     0.009
  nscc_guangzhou        37    18.500               False         130.516       14.580     5.080  0.011     0.008
       nscc_wuxi        41    15.400               False         174.485       15.352     5.184  0.011     0.008
       ornl_olcf       193    17.000               False        -241.205        5.097     5.128  0.010     0.008
   prometheus_oh        20   217.391               False        1356.837        1.337     3.863  0.010     0.008
      rainier_in        45     0.500                True         652.659        3.330     7.587  0.036     0.015
      riken_kobe       139    12.660               False         -46.279       71.447     5.298  0.016     0.008
stargate_abilene       143     0.500               False         328.713        2.843     7.587  0.010     0.008
frames: 2662 over 21 sites; Tier A frames: 1032 over 10 sites
```
### day
```
=== fit on all frames (Tier A) ===
slope on density: 0.0376 ± 0.0109  (re_sd 1.51 K, resid_sd 2.00 K, mixedlm, converged=True)
partial R²: capacity 0.000 | met 0.175 | between-site share 0.337
LOSO median factor: thermal 49.69× (5 of 10 folds unidentified) | geometry 6.15× | constant 12.92×
=== conditioned ===  LOSO median factor: thermal 39.66× (6 unidentified) | geometry 3.58× | constant 9.35× (n=169 frames, 9 sites)
kill 1 (LOSO not better than geometry): True | kill 2 (met > capacity): True -> negative_result
within-site colossus_memphis: +0.0156 ± 0.0029 K/MW (p=0.000) | 0.5 MW: +1.89 K (n=63); 125.0 MW: +3.85 K (n=56)
within-site fairwater_wi: +0.0034 ± 0.0012 K/MW (p=0.007) | 0.5 MW: -0.81 K (n=28); 347.8 MW: +0.40 K (n=22)
within-site ornl_olcf: -0.0015 ± 0.0139 K/MW (p=0.916) | 10.1 MW: +3.00 K (n=71); 17.0 MW: +4.47 K (n=10); 24.6 MW: +3.10 K (n=55); 31.2 MW: +3.56 K (n=33); 32.8 MW: +2.08 K (n=17); 32.9 MW: +4.99 K (n=16)
within-site rainier_in: +0.0004 ± 0.0006 K/MW (p=0.471) | 0.5 MW: +1.67 K (n=31); 1078.3 MW: +2.24 K (n=37)
within-site riken_kobe: +0.0330 ± 0.0348 K/MW (p=0.346) | 12.7 MW: +0.17 K (n=9); 29.9 MW: +0.60 K (n=87)
within-site stargate_abilene: -0.0004 ± 0.0012 K/MW (p=0.757) | 0.5 MW: -0.44 K (n=126); 173.9 MW: -0.60 K (n=30); 521.7 MW: +0.00 K (n=14)
         site_id  n_frames  truth_mw  thermal_identified  thermal_raw_mw  geometry_mw  const_mw  slope  slope_se
colossus_memphis       119     0.500                True        1177.639        5.926     7.587  0.024     0.011
    fairwater_wi        50     0.500               False        -148.073        4.663     7.587  0.035     0.012
        nsa_utah       302    50.000               False        -213.214        4.159     4.548  0.037     0.012
  nscc_guangzhou        30    18.500               False        -106.837       14.580     5.080  0.037     0.011
       nscc_wuxi        65    15.400                True           0.525       15.352     5.184  0.037     0.011
       ornl_olcf       202    17.000                True         844.790        5.097     5.128  0.039     0.010
   prometheus_oh        25   217.391                True        1276.958        1.337     3.863  0.038     0.011
      rainier_in        68     0.500                True         893.403        3.330     7.587  0.074     0.017
      riken_kobe        96    12.660               False          -0.778       71.447     5.298  0.036     0.012
stargate_abilene       170     0.500               False        -651.697        2.843     7.587  0.040     0.011
frames: 2836 over 21 sites; Tier A frames: 1127 over 10 sites
```

## 4. Detection: data-centre halls vs control roofs

```
{
 "n_dc_sites": 12,
 "n_control_sites": 9,
 "auc_night_dT": 0.6018518518518519,
 "auc_day_dT": 0.3611111111111111,
 "auc_amplitude": 0.37037037037037035,
 "auc_landsat_day": 0.37037037037037035,
 "dc_night_dT": {
  "colossus_memphis": -0.75,
  "fairwater_wi": 0.44,
  "hyperion_la": 1.17,
  "nsa_utah": 0.19,
  "nscc_guangzhou": 0.53,
  "nscc_wuxi": 0.5,
  "ornl_olcf": -0.21,
  "prineville": 0.95,
  "prometheus_oh": 0.45,
  "rainier_in": 0.32,
  "riken_kobe": -0.53,
  "stargate_abilene": -0.1
 },
 "ctrl_night_dT": {
  "ctrl_abilene_a": 0.09,
  "ctrl_memphis_a": 2.04,
  "ctrl_memphis_navy": -0.06,
  "ctrl_newalbany_af": -0.14,
  "ctrl_newalbany_dsv": 0.04,
  "ctrl_newcarlisle_mfg": -0.27,
  "ctrl_prineville_schwab": -1.48,
  "ctrl_racine_b": -0.07,
  "ctrl_racine_mke1": 0.64
 },
 "auc_night_frames": 0.5412502900905083,
 "auc_night_frames_operating_only": 0.49379966829456146,
 "operating_night_dT_mean": 0.0011869959473002486,
 "control_night_dT_mean": 0.002393884892086311
}
```

## 5. Detectability of a load step from night frames (one year each side)

| site_id          |   night_resid_sd_k |   night_frames_per_year |   mde_step_k_one_year |   mde_step_mw_at_slope |
|:-----------------|-------------------:|------------------------:|----------------------:|-----------------------:|
| colossus_memphis |               1.32 |                    17.2 |                  1.26 |                    158 |
| fairwater_wi     |               0.65 |                    26.4 |                  0.5  |                     63 |
| hyperion_la      |               0.83 |                    20   |                  0.73 |                     92 |
| nsa_utah         |               0.89 |                    37.3 |                  0.58 |                     72 |
| nscc_guangzhou   |               1.66 |                     4.6 |                  3.06 |                    383 |
| nscc_wuxi        |               0.81 |                     5.1 |                  1.42 |                    178 |
| ornl_olcf        |               1.03 |                    23.9 |                  0.83 |                    104 |
| prineville       |               2.38 |                    44.1 |                  1.42 |                    177 |
| prometheus_oh    |               0.78 |                    32.2 |                  0.54 |                     68 |
| rainier_in       |               0.67 |                    27.2 |                  0.51 |                     64 |
| riken_kobe       |               1.82 |                    19.4 |                  1.64 |                    205 |
| stargate_abilene |               0.99 |                    30.7 |                  0.71 |                     88 |

slope used for MW conversion: 0.008 K per IT-MW (assumption, see --slope-k-per-mw)


## 5b. Roof-only masking (background >= 50 % clear, roof below pixel threshold): a load-correlated bias check

| site_id                | tod   |   accepted |   roof_only_rejected |   roof_only_rejection_rate |
|:-----------------------|:------|-----------:|---------------------:|---------------------------:|
| colossus_memphis       | day   |        119 |                   11 |                       0.08 |
| colossus_memphis       | night |         80 |                   15 |                       0.16 |
| ctrl_abilene_a         | day   |        171 |                    7 |                       0.04 |
| ctrl_abilene_a         | night |        135 |                    6 |                       0.04 |
| ctrl_memphis_a         | day   |        128 |                    2 |                       0.02 |
| ctrl_memphis_a         | night |         85 |                    4 |                       0.04 |
| ctrl_memphis_navy      | day   |        127 |                    6 |                       0.05 |
| ctrl_memphis_navy      | night |         87 |                    4 |                       0.04 |
| ctrl_newalbany_af      | day   |        130 |                    7 |                       0.05 |
| ctrl_newalbany_af      | night |        135 |                   10 |                       0.07 |
| ctrl_newalbany_dsv     | day   |        132 |                    6 |                       0.04 |
| ctrl_newalbany_dsv     | night |        140 |                    6 |                       0.04 |
| ctrl_newcarlisle_mfg   | day   |        138 |                   11 |                       0.07 |
| ctrl_newcarlisle_mfg   | night |        100 |                    8 |                       0.07 |
| ctrl_prineville_schwab | day   |         73 |                  112 |                       0.61 |
| ctrl_prineville_schwab | night |        149 |                   61 |                       0.29 |
| ctrl_racine_b          | day   |        164 |                    3 |                       0.02 |
| ctrl_racine_b          | night |        139 |                    5 |                       0.03 |
| ctrl_racine_mke1       | day   |        159 |                    8 |                       0.05 |
| ctrl_racine_mke1       | night |        142 |                    5 |                       0.03 |
| fairwater_wi           | day   |         50 |                    7 |                       0.12 |
| fairwater_wi           | night |         33 |                    7 |                       0.18 |
| hyperion_la            | day   |         18 |                    5 |                       0.22 |
| hyperion_la            | night |         13 |                    4 |                       0.24 |
| nsa_utah               | day   |        302 |                    7 |                       0.02 |
| nsa_utah               | night |        301 |                   14 |                       0.04 |
| nscc_guangzhou         | day   |         30 |                    0 |                       0    |
| nscc_guangzhou         | night |         37 |                    1 |                       0.03 |
| nscc_wuxi              | day   |         65 |                    2 |                       0.03 |
| nscc_wuxi              | night |         41 |                    2 |                       0.05 |
| ornl_olcf              | day   |        202 |                   10 |                       0.05 |
| ornl_olcf              | night |        193 |                    9 |                       0.04 |
| prineville             | day   |        351 |                   20 |                       0.05 |
| prineville             | night |        357 |                   24 |                       0.06 |
| prometheus_oh          | day   |        136 |                   12 |                       0.08 |
| prometheus_oh          | night |        150 |                   10 |                       0.06 |
| rainier_in             | day   |         68 |                   14 |                       0.17 |
| rainier_in             | night |         45 |                   11 |                       0.2  |
| riken_kobe             | day   |        103 |                    4 |                       0.04 |
| riken_kobe             | night |        157 |                   17 |                       0.1  |
| stargate_abilene       | day   |        170 |                   16 |                       0.09 |
| stargate_abilene       | night |        143 |                    9 |                       0.06 |