import sys, math, json, numpy as np
from dig import Chart
PDF = sys.argv[1]
def interp(guide, x):
    xs = sorted(guide); lx = math.log10(x)
    if x <= xs[0]: a, b = xs[0], xs[1]
    elif x >= xs[-1]: a, b = xs[-2], xs[-1]
    else:
        a = max(k for k in xs if k <= x); b = min(k for k in xs if k > x)
        if a == x: return guide[a]
    s = (math.log10(guide[b]) - math.log10(guide[a])) / (math.log10(b) - math.log10(a))
    return 10 ** (math.log10(guide[a]) + s * (lx - math.log10(a)))
SPEC = {
 "G296-122": (46, (0,3), (0,3), {1:1.4,2:1.65,4:2.1,10:2.8,20:3.8,40:5.6,100:11,200:18,400:30}, [1,1.5,2,3,5,7,10,15,20,30,50,100,150,200,300]),
 "G296-123": (46, (0,3), (0,3), {8:4.5,10:4.9,20:5.6,40:6.6,60:7.9}, [8,10,15,20,30,40,50]),
 "G296-124-mixed": (46, (0,3), (0,3), {1:4.7,10:28,100:170,300:450}, [1,2,5,10,20,50,100,200]),
 "G296-124-axial": (46, (0,3), (0,3), {1:3.2,10:19,100:115,350:350}, [1,2,5,10,20,50,100,200]),
 "G290-104": (40, (1,4), (0,3), {10:2.5,100:22,1000:205,4000:800}, [10,15,20,30,50,100,200,300,500,1000,2000,3000,4000]),
 "G303-141": (53, (0,3), (0,3), {1:5.2,10:27,70:110}, [1,1.5,2,3,5,7,10,15,20,30,50,70]),
 "G303-143": (53, (0,3), (0,3), {1:4.3,10:13.9,35:26}, [1,1.5,2,3,5,7,10,15,20,30]),
 "G303-144": (53, (0,3), (0,3), {1:1.0,10:5.1,20:9}, [1,1.5,2,3,5,7,10,15,20]),
 "G279-066": (29, (0,3), (0,3), {1:1.15,10:5.6,100:38,160:65}, [1,1.5,2,3,5,7,10,15,20,30,50,70,100,150]),
}
charts = {}; out = {}
for cid, (page, xd, yd, guide, xs) in SPEC.items():
    key = (page, xd, yd)
    c = charts.setdefault(key, Chart(PDF, page, xd, yd))
    pts = []
    for x in xs:
        v, n = c.trace(x, interp(guide, x), window=0.12)
        if v is not None and n >= 5: pts.append((x, round(v, 3)))
    lx = [math.log10(p[0]) for p in pts]; ly = [math.log10(p[1]) for p in pts]
    slope = np.polyfit(lx, ly, 1)[0] if len(pts) > 1 else None
    out[cid] = {"page": page, "points": pts, "fitted_slope": None if slope is None else round(float(slope), 3)}
    print(cid, "slope", out[cid]["fitted_slope"]); print("   ", pts)
json.dump(out, open("digitised.json", "w"), indent=1)
