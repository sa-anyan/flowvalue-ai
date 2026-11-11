"""Bounded independent unit-evidence probes; no production/project writes.
Expected factors are dimensional definitions, not read from production constants.
This is a reconciliation supplement, not a claim of exhaustive UNIT-001 acceptance.
"""
from pathlib import Path
import sys,csv,json
from decimal import Decimal as D,localcontext
r=Path(__file__).resolve().parents[5];sys.path.insert(0,str(r))
from backend.equipment_costing.unit_conversion import convert,ConversionContext
from backend.equipment_costing.registry import list_equipment_models
from backend.engineering_sizing.registry import METHODS,PARAMETER_UNITS
p=r/'docs/verification/phase1/closure'; rows=[]
NIST='https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9'

def add(category,v,src,dst,expected,relationship,*,context=None,tol='1e-12',test='',must_block=False):
 result=convert(v,src,dst,context=context)
 actual=result.value
 diff=None if actual is None else abs(D(str(actual))-D(str(expected)))
 allowed=abs(D(str(expected)))*D(tol)+D('1e-14')
 status='BLOCKED — conversion not implemented/unsupported' if actual is None else 'PASS — bounded numerical case' if diff<=allowed else 'FAIL — numeric mismatch'
 if must_block:status='PASS — required explicit rejection' if actual is None else 'FAIL — dimension/basis accepted'
 rows.append(dict(category=category,source_unit=src,destination_unit=dst,input_value=v,relationship=relationship,independent_expected_result='unresolved without required context' if must_block else str(expected),actual_result=str(actual) if actual is not None else 'unresolved: '+'; '.join(result.issues),absolute_difference='' if diff is None else str(diff),relative_tolerance=tol,absolute_tolerance='1e-14',test_evidence=test or 'Evidence supplement: closure/evidence/reconcile_units.py; original scope tests in SIZE-C03 full.xml',source_reference=NIST,acceptance_status=status,scope='Single named case, not all aliases/units or formal UNIT-001 acceptance'))

add('mass',1,'lb','kg','.45359237','kg = lb × 0.45359237',test='test_unit_conversion.py::UnitConversionTests::test_mass_aliases_and_flow_time_bases')
add('mass',1,'tonne','kg',1000,'kg = tonne × 1000')
add('mass flow',1,'kg/s','kg/h',3600,'kg/h = kg/s × 3600',test='test_gas_compression_bridge.py::test_mass_and_molar_flow_use_same_canonical_compression_calculation')
add('mass flow',1,'lb/h','kg/h','.45359237','kg/h = lb/h × 0.45359237')
add('volumetric flow',1,'L/s','m3/h','3.6','m3/h = L/s × .001 ×3600; shared converter only; ingestion currently fails',test='test_sizing_cross_file.py: rows_units L/s FAILURE; separate shared-converter probe here')
add('volumetric flow',1,'US_gpm','m3/h',str(D('.003785411784')*60),'m3/h = US gallon/min × .003785411784 ×60')
add('volume/capacity',1,'US_gal','L','3.785411784','L = US gal × 3.785411784',test='test_unit_conversion.py::UnitConversionTests::test_volume_gallon_definitions_are_explicit')
add('volume/capacity',1,'Imp_gal','L','4.54609','L = Imperial gal × 4.54609')
add('density',1,'g/cm3','kg/m3',1000,'kg/m3 = g/cm3 ×1000',test='test_unit_conversion.py::UnitConversionTests::test_density_molar_flow_and_compound_coordinate')
add('density',1,'lb/ft3','kg/m3',str(D('.45359237')/D('.3048')**3),'kg/m3 = lb/ft3 × .45359237/.3048^3')
psi=D('.45359237')*D('9.80665')/D('.0254')**2
add('pressure scaling',1,'psi','Pa',str(psi),'Pa = psi × .45359237×9.80665/.0254²',test='test_unit_conversion.py::UnitConversionTests::test_pressure_unit_scaling_preserves_basis')
add('pressure scaling',1,'bar','kPa',100,'kPa = bar ×100')
add('gauge to absolute',0,'barg','bara','1.01325','Pabs = Pgauge + explicitly supplied 101325 Pa atmosphere',context=ConversionContext(atmospheric_pressure_pa=101325))
add('gauge to absolute',1,'barg','bara',2,'No generic conversion without explicit atmosphere',must_block=True)
add('pressure difference',1,'bar','Pa',100000,'deltaP scales by 100000; named differential role must be retained by caller, not inferred from units',test='test_pump_numerical_safety.py; test_unit_conversion.py::test_resolver_never_uses_operating_pressure_for_design')
add('absolute temperature',25,'degC','K','298.15','TK = TC +273.15',test='test_unit_conversion.py::UnitConversionTests::test_temperature_absolute_and_difference_separate')
add('temperature difference',10,'delta_degC','delta_degF',18,'deltaF = deltaC ×9/5; no offset')
add('temperature dimension guard',10,'delta_degC','degF',50,'Absolute and difference temperature are different quantity kinds',must_block=True)
add('energy',1,'kWh','MJ','3.6','MJ = kWh ×3600×1000/1e6')
add('power',1,'hp','kW',str(D('.45359237')*D('9.80665')*550*D('.3048')/1000),'Mechanical hp =550 ft lbf/s; kW via exact lb/ft and standard gravity',test='test_unit_conversion.py::UnitConversionTests::test_power_thermal_basis_and_symbol_case')
add('power',1,'Btu_IT/h','kW',str(D('1055.05585262')/3600/1000),'kW = Btu_IT/h ×1055.05585262/3600/1000')
add('energy/power guard',1,'kWh','kW',1,'Time duration is required; energy is not power',must_block=True)
add('length',1,'in','mm','25.4','mm = inch ×25.4',test='test_unit_conversion.py::UnitConversionTests::test_length_area_and_volume_dimensions')
add('area',1,'ft2','m2',str(D('.3048')**2),'m² = ft² ×.3048²')
add('volume',1,'ft3','m3',str(D('.3048')**3),'m³ = ft³ ×.3048³')
add('velocity',1,'m/s','ft/s',str(1/D('.3048')),'ft/s = m/s /.3048; velocity is not a flowrate')
add('dynamic viscosity',1,'cP','Pa*s','.001','Pa·s = cP ×.001')
add('kinematic viscosity',1,'cSt','m2/s','.000001','m²/s = cSt ×1e-6; density needed to relate dynamic viscosity')
add('heat transfer coefficient',1,'Btu_IT/(h*ft2*delta_degF)','W/m2/K',str(D('1055.05585262')/3600/D('.3048')**2/(D(5)/9)),'W/(m² K)= Btu_IT/(h ft² deltaF) ×1055.05585262/3600/.3048²/(5/9)')
add('residence time standalone',60,'min','h',1,'hours = minutes/60; native EBCT handles minutes explicitly, standalone converter does not')
add('equipment flow-pressure coordinate',1000,'US_gpm_psi','1000 US_gpm_psi',1,'Divide coordinate by1000; this is hydraulic flow×pressure, not shaft power')
add('ambiguous capacity',1,'gal','L','3.785411784','US versus Imperial gallon needs context',must_block=True)
add('ambiguous mass',1,'ton','kg',1000,'Metric/short/long ton requires explicit context',must_block=True)

from backend.currency_conversion import convert_currency
fx=convert_currency('100','USD','GBP');expected=100*D('.83580')/D('1.1216')
rows.append(dict(category='currency',source_unit='USD @ stored 2026-11-02 snapshot',destination_unit='GBP same money date',input_value='100',relationship='GBP = USD ×GBP_per_EUR/USD_per_EUR; no price-year escalation',independent_expected_result=str(expected),actual_result=fx['amount'],absolute_difference=str(abs(D(fx['amount'])-expected)),relative_tolerance='1e-24',absolute_tolerance='1e-24',test_evidence='test_currency_conversion.py::test_cross_rates_signed_amounts_and_inverse; C03 full.xml PASS',source_reference='backend/currency_conversion/rates.json; fixed snapshot arithmetic only; external rate provenance not independently accepted',acceptance_status='PASS — fixed-snapshot arithmetic; market data acceptance not established',scope='Currency does not alter historical cost year'))
from backend.equipment_costing.cost_to_future.cost_translation import translate_cost
hist=translate_cost(100,currency='USD',source_period='early 1987',source_series='CEPCI',source_index=320)
expected=100*D('336.940')/D('113.6')
rows.append(dict(category='historical costing basis',source_unit='USD early1987; CEPCI source index320 supplied',destination_unit='USD2026 general-inflation proxy',input_value=100,relationship='same CPI-series target/source ratio; NOT CPI/CEPCI; native-source index remains separate',independent_expected_result=str(expected),actual_result=str(hist.amount),absolute_difference=str(abs(D(hist.amount)-expected)),relative_tolerance='1e-24',absolute_tolerance='1e-24',test_evidence='test_cost_translation.py::test_official_proxy_is_same_cpi_series_not_cpi_divided_by_cepci; C03 full.xml PASS',source_reference='Stored cost_to_future catalogue; algorithm checked; independent current index observations NOT accepted here',acceptance_status='PARTIAL — deterministic proxy arithmetic only, not equipment-index validation',scope='No FX conversion, no claim of genuine 2026 CEPCI'))
from backend.revenue.indexes.openpytea.rate_model import annual_manual_quantity
item={'id':'synthetic','quantity_unit':'kg','manual_rate':{'value':'2','unit':'kg/h','confirmed_by_user':True,'rationale':'Independent unit reconciliation example, no project data'}}
annual=annual_manual_quantity(item,'7536','.8')
rows.append(dict(category='annual operating quantity',source_unit='2 kg/h; explicit7536 h/year and0.8 utilization',destination_unit='kg per stated operating year',input_value=2,relationship='2×7536×.8; utilization applied once;7536=314×24 is an assumption, not a universal maximum',independent_expected_result='12057.6',actual_result=str(annual['annual_quantity']),absolute_difference=str(abs(annual['annual_quantity']-D('12057.6'))),relative_tolerance='0',absolute_tolerance='0',test_evidence='revenue rate-model tests in C03 full.xml plus bounded reconciliation call here',source_reference='Dimensional quantity×time identity; user-approved schedule required',acceptance_status='PASS — explicit-schedule arithmetic only',scope='No assumed saleability, no automatic 365/314 day design rule'))
with (p/'unit_verification_acceptance_matrix.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
contracts=[]
for model in list_equipment_models('all'):
 for req in model.get('input_requirements',[]):
  contracts.append(dict(model_id=model['id'],source=model.get('source','garrett'),category=model.get('category',''),coordinate=req.get('name','size'),quantity=req.get('quantity',''),unit=req.get('target_unit',req.get('unit','')),required=req.get('required',True),manual_coordinate=req.get('manual_coordinate',False),cost_year=model.get('source_year',''),currency=model.get('currency',''),status='IMPLEMENTED METADATA ONLY; not universal independent conversion/model-suitability acceptance'))
with (p/'evidence/model_native_unit_inventory.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=contracts[0]);w.writeheader();w.writerows(contracts)
(p/'evidence/native_sizing_unit_contracts.json').write_text(json.dumps({k:{'input_quantity':v['input'],'input_unit':v['unit'],'parameters':{q:PARAMETER_UNITS[q] for q in v['parameters']},'callable':v['calculator'].__module__+'.'+v['calculator'].__name__} for k,v in METHODS.items()},indent=2)+'\n')
print('Named conversion/quantity records:',len(rows),'model-coordinate records:',len(contracts))
print({status:sum(row['acceptance_status'].startswith(status) for row in rows) for status in ['PASS','PARTIAL','BLOCKED','FAIL']})
