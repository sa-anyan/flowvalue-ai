"""Domain review is prospective, bounded and preserves physical/user inputs."""
import copy
from unittest.mock import patch

import pytest

from backend.blocks.equipment.calculation import calculate_equipment
from backend.equipment_costing.domain_review import candidates, below_floor
from backend.equipment_costing.unit_conversion.bridges.automatic import repair_pricing
from backend.orchestration.store import Store
from backend.tests.test_automatic_equipment_inputs import decision
from backend.tests.test_unit_conversion_bridges import REPORT

CONE = 'openpytea:cone_roof_tank_towler_2010'
CYLINDER = 'openpytea:vertical_cylinder_perry_1996'


def plan(time=1):
    return {'equipment': [{'equipment_key':'e', 'curve_id':CONE, 'quantity':2,
        'matching':{'candidate_model_ids':[CONE,CYLINDER], 'match_status':'ambiguous',
                    'conceptual_validation':'uncertain', 'model_scope':'equipment'},
        'unit_conversion':{'enabled':True, 'origin':'llm_selected_python_equation',
            'model_id':CONE, 'method':'vessel_volume', 'measurement_id':'m',
            'derivations':[], 'unit_context':{'target_gallon_basis':None,'target_ton_basis':None,'atmospheric_pressure_pa':None},
            'inputs':{'density_kg_m3':1000,'residence_time_h':time,'working_fraction':0.8},
            'input_provenance':{'residence_time_h':{'status':'llm_estimate','value':time}}}}]}


class Review:
    model='offline-domain-review'
    calls=0
    def generate(self, **kw):
        self.calls+=1
        assert kw['context']['repair_feedback'][0]['domain_review']
        d=decision();d.update(model_id=CYLINDER,rationale='Provisional vertical cylindrical storage configuration; review material and service. Same purchased-equipment scope. No package installation included.')
        d['unit_context']=copy.deepcopy(plan()['equipment'][0]['unit_conversion']['unit_context'])
        # Changed guesses from the reviewer must not change existing dimensions.
        d['assumptions'][1]['value']=12
        return {'decisions':[d]}


@pytest.mark.parametrize('time, expected_status',[(1,'in_domain_alternative_selected'),(.08,'closer_minimum_floor_selected')])
def test_review_prefers_domain_fit_and_preserves_physical_basis(tmp_path,time,expected_status):
    original=plan(time);before=copy.deepcopy(original)
    total,_=calculate_equipment(REPORT,original)
    assert below_floor(total.equipment[0])
    assert candidates(REPORT,'e',original['equipment'][0])==[CYLINDER]
    reviewer=Review()
    updated,audit=repair_pricing(REPORT,original,total,'',Store(tmp_path/'review.db'),reviewer)
    assert reviewer.calls==1
    row=updated['equipment'][0]
    assert row['curve_id']==CYLINDER
    assert row['quantity']==2
    assert row['unit_conversion']['inputs']==before['equipment'][0]['unit_conversion']['inputs']
    after,_=calculate_equipment(REPORT,updated)
    assert after.equipment[0].amount is not None
    assert after.equipment[0].cost_scope==total.equipment[0].cost_scope
    assert after.equipment[0].parsed_source['domain_selection']['previous_model_id']==CONE
    assert below_floor(after.equipment[0]) == (time==.08)
    assert any(a['status']==expected_status for a in audit)
    assert original==before


@pytest.mark.parametrize('protection',['user_model','user_input','quote','alias'])
def test_explicit_choices_and_inputs_never_enter_floor_review(tmp_path,protection):
    source=plan();r=source['equipment'][0]
    if protection=='user_model':r['model_selection']={'origin':'user','curve_id':CONE}
    if protection=='user_input':r['unit_conversion']['input_provenance']['residence_time_h']['status']='user_input'
    total,_=calculate_equipment(REPORT,source)
    if protection=='quote':r['external_quote']={'amount':10}
    if protection=='alias':r['scope_decision']='alias'
    class Fail:
        def generate(self,**kw):raise AssertionError('Protected input must not call AI')
    updated,_=repair_pricing(REPORT,source,total,'',Store(tmp_path/'review.db'),Fail())
    assert updated==source


def test_unavailable_or_unsuitable_review_keeps_the_existing_price(tmp_path):
    source=plan();total,_=calculate_equipment(REPORT,source)
    class Fail:
        model='offline-unavailable'
        def generate(self,**kw):raise ValueError('Reviewer unavailable')
    updated,audit=repair_pricing(REPORT,source,total,'',Store(tmp_path/'review.db'),Fail())
    assert updated==source
    assert any(a['status']=='minimum_price_floor_retained' for a in audit)


def test_no_alternative_and_already_in_range_need_no_extra_review(tmp_path):
    for source in (plan(),plan(time=20)):
        source['equipment'][0]['matching']['candidate_model_ids']=[CONE]
        total,_=calculate_equipment(REPORT,source)
        reviewer=Review()
        updated,_=repair_pricing(REPORT,source,total,'',Store(tmp_path/'review.db'),reviewer)
        assert reviewer.calls==0 and updated==source


def test_category_scope_and_coordinate_guards_reject_incompatible_candidates():
    from backend.equipment_costing.domain_review import model_contract
    source=plan()['equipment'][0]
    actual=model_contract
    for changed in ({'cost_scope':'installed_package'},{'category':'Heat exchangers'},{'source':'different_library'}):
        def contract(model_id):
            model,requirement,unit=actual(model_id)
            return ({**model,**changed} if model_id==CYLINDER else model),requirement,unit
        with patch('backend.equipment_costing.domain_review.model_contract',side_effect=contract):
            assert candidates(REPORT,'e',source)==[]


def test_review_rejects_unoffered_model_and_preserves_price(tmp_path):
    source=plan();total,_=calculate_equipment(REPORT,source)
    wrong=copy.deepcopy(source['equipment'][0]);wrong['curve_id']='openpytea:clarifier_steel_seider_2013'
    wrong['unit_conversion']['model_id']=wrong['curve_id']
    with patch('backend.equipment_costing.unit_conversion.bridges.automatic.resolve',return_value=({'equipment':[wrong]},[])):
        updated,audit=repair_pricing(REPORT,source,total,'',Store(tmp_path/'review.db'),Review())
    assert updated==source
    assert any(a['status']=='minimum_price_floor_retained' for a in audit)


def test_changed_physical_inputs_are_rejected_even_if_model_is_in_domain(tmp_path):
    source=plan();total,_=calculate_equipment(REPORT,source)
    wrong=copy.deepcopy(source['equipment'][0]);wrong['curve_id']=CYLINDER
    wrong['unit_conversion']['model_id']=CYLINDER
    wrong['unit_conversion']['inputs']['residence_time_h']=3
    with patch('backend.equipment_costing.unit_conversion.bridges.automatic.resolve',return_value=({'equipment':[wrong]},[])):
        updated,audit=repair_pricing(REPORT,source,total,'',Store(tmp_path/'review.db'),Review())
    assert updated==source
    assert any(a['status']=='minimum_price_floor_retained' for a in audit)


def test_unknown_coordinate_and_secondary_domain_fail_closed():
    from backend.equipment_costing.domain_review import model_contract, evaluate
    source=plan()['equipment'][0];actual=model_contract
    def wrong_quantity(model_id):
        model,requirement,unit=actual(model_id)
        return model,({**requirement,'quantity':'power'} if model_id==CYLINDER else requirement),unit
    with patch('backend.equipment_costing.domain_review.model_contract',side_effect=wrong_quantity):
        assert candidates(REPORT,'e',source)==[]
    actual_evaluate=evaluate
    def second_dimension(*args,**kwargs):
        result=actual_evaluate(*args,**kwargs)
        if args[2]['model_id']==CYLINDER:result['second_size']=999
        return result
    with patch('backend.equipment_costing.domain_review.evaluate',side_effect=second_dimension):
        assert candidates(REPORT,'e',source)==[]


def test_above_range_alternative_is_not_treated_as_a_floor_candidate():
    from backend.equipment_costing.domain_review import model_contract
    source=plan()['equipment'][0];actual=model_contract
    def contract(model_id):
        model,requirement,unit=actual(model_id)
        return ({**model,'capacity_limits':['0.01','0.1']} if model_id==CYLINDER else model),requirement,unit
    with patch('backend.equipment_costing.domain_review.model_contract',side_effect=contract):
        assert candidates(REPORT,'e',source)==[]


def test_changed_quantity_cannot_be_accepted_as_a_domain_repair(tmp_path):
    source=plan();total,_=calculate_equipment(REPORT,source)
    wrong=copy.deepcopy(source['equipment'][0]);wrong['curve_id']=CYLINDER;wrong['quantity']=1
    wrong['unit_conversion']['model_id']=CYLINDER
    with patch('backend.equipment_costing.unit_conversion.bridges.automatic.resolve',return_value=({'equipment':[wrong]},[])):
        updated,_=repair_pricing(REPORT,source,total,'',Store(tmp_path/'review.db'),Review())
    assert updated==source
