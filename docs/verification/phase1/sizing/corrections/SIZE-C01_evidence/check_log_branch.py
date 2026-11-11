"""Independent continuity experiment across finite-ratio/log-difference branch.
Run from repository root with the recorded verification Python interpreter.
Mathematical stress values are not physically approved pressure conditions.
"""
import json
import math
import sys
from decimal import Decimal, localcontext
from pathlib import Path

root=Path(__file__).resolve().parents[6]
sys.path.insert(0,str(root))
from backend.engineering_sizing import calculate

pin=1e-200
pout=sys.float_info.max*pin
pressures=[pout]
for _ in range(3):
    pressures.insert(0,math.nextafter(pressures[0],0.))
    pressures.append(math.nextafter(pressures[-1],math.inf))
rows=[]
for out in pressures:
    params=dict(molecular_weight_kg_kmol=28,temperature_k=300,
                absolute_pressure_bar=pin,discharge_pressure_bar=out,
                heat_capacity_ratio=1.4,efficiency=.75,compressibility_z=1)
    with localcontext() as ctx:
        ctx.prec=100
        k=Decimal.from_float(1.4)
        ratio=Decimal.from_float(out)/Decimal.from_float(pin)
        t2=Decimal(300)*(ratio.ln()*(k-1)/k).exp()
        expected=float(Decimal('8.31446261815324')/28*k/(k-1)*(t2-300)/Decimal('.75'))
    actual=calculate('gas_compression',3600,params)[0]
    rel=abs(actual-expected)/expected
    assert rel<=5e-12
    rows.append(dict(pin=pin,pout=out,branch='log1p' if math.isfinite((out-pin)/pin) else 'log_difference',expected=expected,actual=actual,relative_error=rel))
assert {x['branch'] for x in rows}=={'log1p','log_difference'}
assert max(x['actual'] for x in rows)/min(x['actual'] for x in rows)-1<5e-12
Path(__file__).with_name('log_branch_continuity.json').write_text(json.dumps(rows,indent=2)+'\n')
print('7 independent branch-continuity comparisons passed')
