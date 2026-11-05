"""Production form contracts feed canonical engines and reject incomplete inputs."""
import copy
import pytest
from backend.revenue.method_forms import build_line, validate_form_line, FORMS
from backend.orchestration.operating_economics import _revenue_project, operating_schedule
from backend.opex.models import Basis
from backend.revenue import calculate_revenue
from backend.tests.test_operating_economics import fixture

CASES=[
 ('product_sales','sold_quantity',dict(quantity=100,rate=20,unit='kg'),2000),
 ('processing_services','processed_quantity',dict(quantity=100,rate=200,unit='tonne'),20000),
 ('capacity_availability','reservation',dict(quantity=400000,rate=.45,unit='kg',period='annual',availability=1),180000),
 ('infrastructure_usage','usage',dict(quantity=1000,rate=5,unit='pallet-day'),5000),
 ('infrastructure_usage','subscription',dict(quantity=10,rate=5,unit='pallet'),600),
 ('environmental_attributes','credits',dict(quantity=200,rate=45,eligibility='Declared eligibility scenario',ownership='Declared owner and transfer rights'),9000),
 ('other_contractual_income','fixed',dict(fixed=50000),50000),
 ('other_contractual_income','variable',dict(quantity=100,rate=10,unit='site'),1000),
]

def inputs(values):
 return dict(name='Synthetic payment',description='Independent test scenario',**values)

@pytest.mark.parametrize('method,subtype,values,expected',CASES)
def test_every_production_form_computes_independent_expected_income(method,subtype,values,expected):
 line=build_line(method,subtype,inputs(values),1)
 validate_form_line(line,1)
 report,config,_=fixture()
 config.update(sales=[],commercial_lines=[line],avoided_costs=[])
 config['financial'].update(operating_years=1,production_ramp=[1])
 hours,ramp=operating_schedule(config)
 result=calculate_revenue(_revenue_project(report,'Synthetic payment',config,Basis(**config['price_basis']),hours,ramp,{}),engineering_scenario=True)
 assert not result.issues
 assert float(result.annual[0].sales_revenue)==expected

@pytest.mark.parametrize('method,subtype,values,expected',CASES)
def test_required_fields_checked_by_backend(method,subtype,values,expected):
 for key in ['name','description']+[f['key'] for f in FORMS[method]['variants'][subtype]['fields'] if f['required']]:
  missing=inputs(values);missing.pop(key)
  with pytest.raises(ValueError,match='required'):
   build_line(method,subtype,missing,1)

@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),-1])
def test_invalid_numbers_are_not_unknown_or_zero(bad):
 with pytest.raises(ValueError):
  build_line('product_sales','sold_quantity',inputs(dict(quantity=bad,rate=20,unit='kg')),1)

def test_additional_fee_requires_distinct_scope():
 values=inputs({**CASES[2][2],'fixed_fee':45000})
 with pytest.raises(ValueError,match='distinct scope'):
  build_line('capacity_availability','reservation',values,1)
 values['fixed_scope']='Separately priced administration service'
 line=build_line('capacity_availability','reservation',values,1)
 assert line['fixed_variable_distinct']

def test_form_tag_does_not_bypass_save_validation():
 line=build_line('product_sales','sold_quantity',inputs(CASES[0][2]),1)
 line['years'][0]['rate']=999
 with pytest.raises(ValueError,match='method-specific form'):
  validate_form_line(line,1)

def test_storage_annual_usage_uses_one_period_even_when_invoiced_monthly():
 line=build_line('infrastructure_usage','usage',inputs(CASES[3][2]),1)
 assert line['years'][0]['periods']==1

def test_method_inputs_cannot_leak_into_another_method():
 with pytest.raises(ValueError,match='do not belong'):
  build_line('other_contractual_income','fixed',inputs(dict(fixed=10,quantity=100)),1)


def test_preview_api_uses_shared_schema_without_saving_or_calling_ai(tmp_path):
 from fastapi.testclient import TestClient
 from unittest.mock import patch
 from backend.api import app as api
 from backend.orchestration.store import Store
 from backend.orchestration.service import new_assessment
 report,config,_=fixture()
 store=Store(tmp_path/'test.db')
 state=new_assessment(store,b'fixture','fixture.xlsx','Process')
 state.update(running=False,plan={'operating_economics':config})
 state=store.put(state,state['revision'])
 with patch.object(api,'store',store),patch('backend.orchestration.provider.EngineeringProvider.generate',side_effect=AssertionError('No AI')):
  client=TestClient(api.app)
  assert client.get('/api/catalogue/revenue-forms').json()==FORMS
  for method,subtype,values,_ in CASES:
   response=client.post(f'/api/assessments/{state["id"]}/revenue-line-preview',json={'revision':state['revision'],'method':method,'subtype':subtype,'inputs':inputs(values)})
   assert response.status_code==200,response.text
   assert response.json()['category']==method
  response=client.post(f'/api/assessments/{state["id"]}/revenue-line-preview',json={'revision':state['revision'],'method':'environmental_attributes','subtype':'credits','inputs':inputs(dict(quantity=1,rate=45))})
  assert response.status_code==422
 assert store.get(state['id'])==state
