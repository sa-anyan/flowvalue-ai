"""Design experiment only: method-specific forms feed existing revenue engines.

Not registered in production. Tests establish whether the proposed form contracts
prevent the known loose-input failures before changing the live drawer.
"""
from dataclasses import replace
import pytest
from backend.tests.test_revenue_mece import line, project
from backend.tests.test_revenue import a
from backend.revenue import calculate_revenue

FIELDS = {
 'product_sales': ('quantity_sold','unit_price','unit'),
 'processing_services': ('quantity_processed','tariff','unit'),
 'capacity_availability': ('reserved_capacity','reservation_rate','capacity_unit','rate_period','availability'),
 'infrastructure_usage': ('billable_usage','usage_rate','usage_unit'),
 'environmental_attributes': ('credits_sold','credit_price','eligibility_basis'),
 'other_contractual_income': ('annual_payment',),
}

def prototype(method, values):
    for field in FIELDS[method]:
        if values.get(field) is None or values.get(field) == '':
            raise ValueError('Required: '+field)
    if values.get('fixed_fee') and not values.get('fixed_scope_description'):
        raise ValueError('Separate fixed-fee scope must be confirmed')
    period='per_unit'; availability=1; fixed=0; eligibility=''
    if method=='product_sales':
        quantity,rate,unit=values['quantity_sold'],values['unit_price'],values['unit']
    elif method=='processing_services':
        quantity,rate,unit=values['quantity_processed'],values['tariff'],values['unit']
    elif method=='capacity_availability':
        quantity,rate,unit=values['reserved_capacity'],values['reservation_rate'],values['capacity_unit']
        period,availability=values['rate_period'],values['availability']
        if period not in ('annual','monthly'):
            raise ValueError('Capacity requires a declared reservation period')
    elif method=='infrastructure_usage':
        quantity,rate,unit=values['billable_usage'],values['usage_rate'],values['usage_unit']
    elif method=='environmental_attributes':
        quantity,rate,unit=values['credits_sold'],values['credit_price'],'credit'
        eligibility=values['eligibility_basis']
    else:
        quantity,rate,unit,fixed=0,0,'payment',values['annual_payment']
    fixed+=values.get('fixed_fee',0)
    original=line(method)
    suffix={'per_unit':'','annual':'/year','monthly':'/month'}[period]
    year=replace(original.years[0],quantity=a(quantity,unit),minimum_quantity=a(0,unit),
                 rate=a(rate,'GBP/'+unit+suffix),fixed_payment=a(fixed,'GBP/year'),
                 availability=a(availability),periods=12 if period=='monthly' else 1)
    return replace(original,quantity_unit=unit,rate_period=period,years=(year,),
                   eligibility_basis=eligibility,fixed_variable_distinct=bool(values.get('fixed_scope_description')))

CASES=[
 ('product_sales',dict(quantity_sold=100,unit_price=20,unit='kg'),2000),
 ('processing_services',dict(quantity_processed=100,tariff=200,unit='tonne'),20000),
 ('capacity_availability',dict(reserved_capacity=400000,reservation_rate=.45,capacity_unit='kg',rate_period='annual',availability=1),180000),
 ('infrastructure_usage',dict(billable_usage=1000,usage_rate=5,usage_unit='pallet-day'),5000),
 ('environmental_attributes',dict(credits_sold=200,credit_price=45,eligibility_basis='Explicit scenario eligibility and ownership'),9000),
 ('other_contractual_income',dict(annual_payment=50000),50000),
]

@pytest.mark.parametrize('method,values,expected',CASES)
def test_method_form_routes_to_existing_engine_with_independent_expected_amount(method,values,expected):
    result=calculate_revenue(project(prototype(method,values)))
    assert not result.issues
    assert float(result.annual[0].sales_revenue)==expected

@pytest.mark.parametrize('method,values,expected',CASES)
def test_each_required_field_is_checked_before_calculation(method,values,expected):
    for field in FIELDS[method]:
        missing=dict(values);missing.pop(field)
        with pytest.raises(ValueError,match=field):
            prototype(method,missing)

def test_storage_billed_monthly_does_not_multiply_annual_pallet_days_by_twelve():
    payment=prototype('infrastructure_usage',CASES[3][1])
    assert payment.years[0].periods==1
    assert calculate_revenue(project(payment)).annual[0].sales_revenue==5000

def test_monthly_reserved_capacity_uses_twelve_periods():
    values=dict(reserved_capacity=100,reservation_rate=2,capacity_unit='m3',rate_period='monthly',availability=.9)
    assert calculate_revenue(project(prototype('capacity_availability',values))).annual[0].sales_revenue==2160

def test_throughput_cannot_replace_contracted_capacity():
    with pytest.raises(ValueError,match='reserved_capacity'):
        prototype('capacity_availability',dict(quantity_processed=100,reservation_rate=2,capacity_unit='kg',rate_period='annual',availability=1))

def test_capacity_fixed_fee_requires_separate_scope():
    values={**CASES[2][1],'fixed_fee':45000}
    with pytest.raises(ValueError,match='scope'):
        prototype('capacity_availability',values)
    values['fixed_scope_description']='Distinct separately agreed administration service'
    result=calculate_revenue(project(prototype('capacity_availability',values)))
    assert not result.issues
    assert result.annual[0].sales_revenue==225000
