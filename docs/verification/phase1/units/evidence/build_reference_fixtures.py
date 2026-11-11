"""Independent dimensional reference-fixture generation; no production imports.
Recreates only this ticket's static test fixtures, not historical evidence.
"""
from pathlib import Path
from decimal import Decimal as D
import json
r=Path(__file__).resolve().parents[5]
f=r/'backend/tests/fixtures/unit_acceptance'
f.mkdir(parents=True,exist_ok=True)
rows=[]
def case(src,dst,expected,relation,v=1,dimension='',context=None):
 rows.append(dict(id=f'U{len(rows)+1:03}',value=v,source=src,destination=dst,expected=str(expected),dimension=dimension,relationship=relation,context=context or {},relative_tolerance=1e-12,absolute_tolerance=1e-14))
# Independent definitions; never read the production factors as an oracle.
length={'m':D(1),'cm':D('.01'),'mm':D('.001'),'in':D('.0254'),'ft':D('.3048')}
mass={'kg':D(1),'g':D('.001'),'mg':D('.000001'),'lb':D('.45359237'),'oz':D('.45359237')/16,'tonne':D(1000),'short_ton':D('.45359237')*2000,'long_ton':D('.45359237')*2240}
volume={k+'3':x**3 for k,x in length.items()};volume.update(L=D('.001'),mL=D('.000001'),US_gal=D('.003785411784'),Imp_gal=D('.00454609'))
for src,x in mass.items():case(src,'kg',x,'Mass definition to kg',dimension='M')
for src,x in length.items():case(src,'m',x,'Exact metric/international length definition',dimension='L')
for src,x in length.items():case(src+'2','m2',x*x,'Square the length factor',dimension='L2')
for src,x in volume.items():case(src,'m3',x,'Cube the length factor or stated litre/gallon definition',dimension='L3')
for kind,units,target,dim in [('mass',mass,'kg/h','M/T'),('volume',volume,'m3/h','L3/T')]:
 for src,x in units.items():
  for time,seconds in [('s',1),('min',60),('h',3600),('day',86400)]:
   case(src+'/'+time,target,x*3600/D(seconds),'Numerator factor ×3600/source seconds',dimension=dim)
psi=D('.45359237')*D('9.80665')/D('.0254')**2
pressure={'Pa':D(1),'kPa':D(1000),'MPa':D(1000000),'bar':D(100000),'mbar':D(100),'psi':psi,'atm':D(101325),'Torr':D(101325)/760,'mmHg':D('133.322387415')}
for src,x in pressure.items():case(src,'Pa',x,'Stated pressure-unit definition; role not inferred',dimension='M/L/T2')
for src,base in [('barg',D(100000)),('bara',D(100000)),('psig',psi),('psia',psi),('kPag',D(1000)),('kPaa',D(1000))]:case(src,'Pa',base,'Scale only; preserve explicit gauge/absolute basis',dimension='M/L/T2')
case('barg','bara','1.01325','Pabs=Pgauge+explicit101325Pa',v=0,dimension='pressure gauge→absolute',context={'atmospheric_pressure_pa':101325})
case('psia','psig',0,'Pgauge=Pabs-explicit atmosphere',v=float(D(101325)/psi),dimension='pressure absolute→gauge',context={'atmospheric_pressure_pa':101325})
for src,dst,val,expected,relation in [('degC','K',25,'298.15','TK=TC+273.15'),('K','degC',300,'26.85','TC=TK-273.15'),('degF','K',32,'273.15','TK=(TF+459.67)*5/9'),('degC','degF',100,212,'TF=TC*9/5+32'),('delta_degF','delta_K',18,10,'Temperature interval scales5/9; no offset'),('delta_degC','delta_degF',10,18,'Temperature interval scales9/5'),('degR','K',9,5,'Rankine scales5/9')]:case(src,dst,expected,relation,v=val,dimension='temperature difference' if src.startswith('delta') else 'temperature')
energy={'J':D(1),'kJ':D(1000),'MJ':D(10)**6,'GJ':D(10)**9,'kWh':D(3600000),'Btu_IT':D('1055.05585262'),'Btu_th':D('1054.35026444')}
for src,x in energy.items():case(src,'J',x,'Energy definition to joule',dimension='M L2/T2')
for src,x in {'W':D(1),'kW':D(1000),'MW':D(1000000),'mW':D('.001'),'hp':550*D('.3048')*D('.45359237')*D('9.80665'),'metric_hp':75*D('9.80665'),'refrigeration_ton':12000*D('1055.05585262')/3600}.items():case(src,'kW',x/1000,'Watt definition or mechanical/thermal convention',dimension='M L2/T3')
case('kWh/day','kW',1,'24 kWh divided by86400s =1kW; time supplied in source unit',v=24,dimension='power')
for src,x in {'kg/m3':D(1),'g/cm3':D(1000),'lb/ft3':D('.45359237')/D('.3048')**3}.items():case(src,'kg/m3',x,'Mass/volume factor ratio',dimension='M/L3')
case('cfm','m3/h',D('.3048')**3*60,'ft3/min ×60h/min',dimension='L3/T')
case('US_gpm','m3/h',D('.003785411784')*60,'US gal/min ×60min/h',dimension='L3/T')
case('Imp_gpm','m3/h',D('.00454609')*60,'Imperial gal/min ×60min/h',dimension='L3/T')
case('1000 US_gpm_psi','US_gpm_psi',1000,'Explicit bounded coordinate scale',dimension='flow_pressure_product')
case('1000 ft2','m2',1000*D('.3048')**2,'1000 ×square-foot factor',dimension='L2')
case('1000 gal','m3',1000*D('.003785411784'),'Explicit source US gallon basis',dimension='L3',context={'input_gallon_basis':'US'})
case('ton/h','kg/h',1000,'Explicit metric source ton',dimension='M/T',context={'input_ton_basis':'metric'})
case('scfm','Sm3/h',D('.3048')**3*60,'Only scale volume/time at explicitly identical gas references',dimension='standard-volume-flow',context={'input_gas_reference':'same dry gas composition;300K;100000Pa;Z1','target_gas_reference':'same dry gas composition;300K;100000Pa;Z1'})
case('kmol/h','mol/s',D(1000)/3600,'Molar amount and time factors; not mass without MW',dimension='amount/T')
# Explicit independently asserted spellings: not taken from production alias dictionaries.
aliasgroups={
'kg':['kilogram','kilograms'],'g':['gram','grams'],'lb':['lbs','lbm','pound','pounds'],
 'm':['metre','metres','meter','meters'],'cm':['centimetre','centimeter'],'mm':['millimetre','millimeter'],
 'in':['inch','inches'],'ft':['foot','feet'],'m2':['m²','m^2','sq m'],'ft2':['ft²','ft^2','sq ft'],
 'm3':['m³','m^3','cu m'],'ft3':['ft³','ft^3'],'L':['l','litre','liter','litres','liters'],
 'mL':['ml','millilitre','milliliter'],'US_gal':['US gal','gal_US','US gallon','US gallons'],
 'Imp_gal':['Imperial gal','gal_Imp','imperial gallon','UK gallons'],'degC':['°C','C','celsius','degrees Celsius'],
 'degF':['°F','F','fahrenheit','degrees Fahrenheit'],'K':['kelvin','kelvins'],
 'delta_degC':['delta_C','delta_°C'],'delta_degF':['delta_F','delta_°F'],
 'bara':['bar_abs','bar_absolute'],'barg':['bar_gauge'],'psia':['psi_abs','psi_absolute'],'psig':['psi_gauge'],
 'kg/h':['kg/hr','kg/hour','kilograms per hour'],'m3/h':['m³/h','m^3/hr','m3/hour'],
 'L/min':['L/minute','litres per minute'],'kW':['kJ/s']}
aliases=[]
for dst,labels in aliasgroups.items():
 for label in labels:aliases.append(dict(id='A%03d'%(len(aliases)+1),source=label,destination=dst,expected='1',relationship='Explicit synonymous unit spelling, same physical coordinate'))
(f/'references.json').write_text(json.dumps(rows,indent=2)+'\n');(f/'aliases.json').write_text(json.dumps(aliases,indent=2)+'\n')
print('Independent conversion cases',len(rows),'explicit alias cases',len(aliases))
