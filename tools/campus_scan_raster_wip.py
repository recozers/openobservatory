"""Scan regions for data-centre-like campuses: linear classifier on satellite-embedding features
(50 m pixel + 250 m + 700 m neighbourhood means), evaluated server-side as three weighted bands,
pulled as a small 100 m score raster and grouped into candidate objects locally."""
import sys, json, pickle, time
from pathlib import Path
import ee, numpy as np, pandas as pd
from scipy import ndimage
import os; ee.Initialize(project=os.environ.get('EE_PROJECT') or None); ee.data.setDeadline(900000)
S = str(Path(__file__).resolve().parents[1] / 'results_campus')  # classifier and training features live here
M = pickle.load(open(f'{S}/dc_classifier.pkl', 'rb'))
bands = [f'A{i:02d}' for i in range(64)]
w = dict(zip(M['cols'], M['w'])); b = M['b']
tf = pd.read_csv(f'{S}/train_features.csv')
neg_logit = tf.loc[tf.label == 0, M['cols']].to_numpy() @ np.array(M['w']) + b
pos_logit = tf.loc[tf.label == 1, M['cols']].to_numpy() @ np.array(M['w']) + b
thr = float(np.quantile(neg_logit, 0.80))
print(f'threshold logit {thr:+.2f} = 80th pct of large-roof negatives; data-centre positives above it: {np.mean(pos_logit > thr):.2f}')
year = sys.argv[1] if len(sys.argv) > 1 else '2024'
regions = json.loads(sys.argv[2])
emb = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL').filterDate(f'{year}-01-01', f'{int(year)+1}-01-01').mosaic()
RES = 100
rows = []
for name, (x0, y0, x1, y1) in regions.items():
    t0 = time.time()
    reg = ee.Geometry.Rectangle([x0, y0, x1, y1])
    utm = int((x0 + x1) / 2 + 180) // 6 + 1; crs = f'EPSG:{32600 + utm if (y0 + y1) / 2 >= 0 else 32700 + utm}'
    e = emb.setDefaultProjection(crs, None, 10)
    def lin(suffix):
        return e.select(bands).multiply(ee.Image.constant([w[bb + suffix] for bb in bands])).reduce(ee.Reducer.sum())
    coarse = lambda img: img.reduceResolution(ee.Reducer.mean(), maxPixels=16).reproject(crs, None, 30).reduceResolution(ee.Reducer.mean(), maxPixels=16).reproject(crs, None, RES)
    l_r = coarse(lin('_r')); l_m = coarse(lin('_m')).focal_mean(250, 'circle', 'meters'); l_c = coarse(lin('_c')).focal_mean(700, 'circle', 'meters')
    logit = l_r.add(l_m).add(l_c).add(b).rename('logit')
    try:
        arr = np.array(logit.sampleRectangle(region=reg, defaultValue=-99).get('logit').getInfo(), dtype=float)
    except Exception as ex:
        print(f'{name}: failed {str(ex)[:140]}'); continue
    valid = arr > -90
    hot = (arr > thr) & valid
    lab, n = ndimage.label(hot, structure=np.ones((3, 3)))
    ny, nx = arr.shape
    objs = []
    for k in range(1, n + 1):
        m = lab == k; a_ha = m.sum() * (RES / 100.0) ** 2  # 100 m pixel = 1 ha
        if a_ha < 4: continue
        yy, xx = np.nonzero(m)
        lat = y1 - (yy.mean() + 0.5) / ny * (y1 - y0); lon = x0 + (xx.mean() + 0.5) / nx * (x1 - x0)
        objs.append(dict(region=name, area_ha=round(a_ha, 1), mean_logit=round(float(arr[m].mean()), 2), max_logit=round(float(arr[m].max()), 2), lat=round(lat, 4), lon=round(lon, 4)))
    objs.sort(key=lambda o: -o['max_logit'])
    print(f'== {name}: grid {nx}x{ny} @ {RES} m, {int(valid.sum())} valid px, {int(hot.sum())} hot px, {len(objs)} objects >= 4 ha ({time.time()-t0:.0f}s)')
    for o in objs[:8]:
        print(f"   {o['area_ha']:7.1f} ha  logit mean {o['mean_logit']:+.2f} max {o['max_logit']:+.2f}  at {o['lat']:.4f}, {o['lon']:.4f}")
    rows += objs
pd.DataFrame(rows).to_csv(f'{S}/scan_candidates_{year}.csv', index=False)
