"""Independent constants only. Does not import FlowValue conversion code."""
from decimal import Decimal as D, getcontext
from pathlib import Path
import json
getcontext().prec=45
r=Path(__file__).resolve().parents[6]
ft=D('0.3048');btu=D('1055.05585262'); th=D('1054.350')
factors={'m/s':('velocity',D(1),'m/s'),'m/h':('velocity',D(1)/3600,'m/s'),'ft/s':('velocity',ft,'m/s'),'ft/min':('velocity',ft/60,'m/s'),'s':('time',D(1),'s'),'min':('time',D(60),'s'),'h':('time',D(3600),'s'),'day':('time',D(86400),'s'),'W/m2/K':('heat_transfer_coefficient',D(1),'W/m2/K'),'kW/m2/K':('heat_transfer_coefficient',D(1000),'W/m2/K'),'Btu_IT/(h*ft2*delta_degF)':('heat_transfer_coefficient',btu/(3600*ft**2*(D(5)/9)),'W/m2/K'),'Btu_th/(h*ft2*delta_degF)':('heat_transfer_coefficient',th/(3600*ft**2*(D(5)/9)),'W/m2/K')}
refs=[]
for s,(q,f,t) in factors.items():
 for x in [0,1,17.25]:
  refs.append({'id':s+'-'+str(x),'quantity':q,'value':x,'source':s,'target':t,'factor':str(f),'expected':str(D(str(x))*f),'relative_tolerance':5e-7 if 'Btu_th' in s else 2e-12,'absolute_tolerance':1e-13,'basis':'NIST displayed thermochemical-Btu precision; half last place propagated' if 'Btu_th' in s else 'Exact length/time/prefix/temperature-interval definitions; conventional Btu_IT'})
(r/'backend/tests/fixtures/unit003/conversions.json').write_text(json.dumps(refs,indent=2)+'\n')
