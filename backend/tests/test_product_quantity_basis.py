import pytest
from backend.revenue.product_basis import quantity_unit,product_observation

def test_explicit_tonne_quote_resolves_legacy_t():
 assert quantity_unit({'quantity_unit':'t','context_quote':'Sell at $20/tonne of dry biomass'})=='tonne'

def test_unspecified_ton_is_not_guessed():
 with pytest.raises(ValueError,match='Specify tonne'):
  quantity_unit({'quantity_unit':'t','context_quote':'Sell biomass'})

def test_component_basis_reads_biomass_not_carried_water():
 def value(prop,component,amount):return {'property':prop,'component':component,'normalized_value':amount,'normalized_unit':'kg/h','status':'source_supported'}
 report={'entities':[{'key':'s14','identifier':'14','values':[value('mass_flow',None,900),value('component_mass_flow','Water',900),value('component_mass_flow','Biomass',100)]}]}
 item={'stream_key':'s14','quantity_unit':'t','context_quote':'Sell for $20/tonne based on the 100 kg/h biomass component of Stream 14. Exclude the water carried with the biomass.'}
 assert product_observation(report,item)['normalized_value']==100
 item['context_quote']='Sell the whole stream for $20/tonne'
 assert product_observation(report,item)['normalized_value']==900
