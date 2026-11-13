const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const Module=require('node:module');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const src=path.join(__dirname,'..','src');
const resolve=Module._resolveFilename;
Module._resolveFilename=function(request,...rest){
 if(request.startsWith('@/')){const base=path.join(src,request.slice(2));for(const ext of ['.ts','.tsx'])if(fs.existsSync(base+ext))return base+ext;}
 return resolve.call(this,request,...rest);
};
require.extensions['.css']=()=>{};
const compile=(module,file,jsx)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,...(jsx?{jsx:ts.JsxEmit.ReactJSX}:{})}}).outputText,file);
require.extensions['.ts']=(m,f)=>compile(m,f,false);
require.extensions['.tsx']=(m,f)=>compile(m,f,true);
const lib=require('../src/lib/guided-flow.ts');
const {FanChart,LineChart}=require('../src/blocks/guided/charts.tsx');

test('stages advance in the founder order and runs map to backend stages',()=>{
 assert.deepEqual(lib.stageIds,['entry','equipment','capex','opex','revenue','financial']);
 assert.equal(lib.nextStage('entry'),'equipment');
 assert.equal(lib.nextStage('financial'),null);
 assert.equal(lib.forwardRun('entry'),'equipment');
 assert.equal(lib.forwardRun('equipment'),'capex');
 assert.equal(lib.forwardRun('revenue'),'financial');
 assert.equal(lib.direction('capex','equipment'),'back');
 assert.equal(lib.direction('entry','financial'),'forward');
 assert.equal(lib.isStage('nope'),false);
});

test('missing amounts are never shown as zero, and zero stays zero',()=>{
 assert.equal(lib.money(null),'Not calculated');
 assert.equal(lib.money(undefined,'Unpriced'),'Unpriced');
 assert.equal(lib.money('0'),'0');
 assert.equal(lib.compact(''),'—');
 assert.equal(lib.num(true),null);
 assert.deepEqual(lib.strings(['a',{b:1},null,2]),['a','{"b":1}','2']);
});

test('user model selection is recorded so AI reruns cannot replace it',()=>{
 assert.deepEqual(lib.userModelSelection('G303-144'),{curve_id:'G303-144',model_selection:{origin:'user',curve_id:'G303-144'}});
 assert.deepEqual(lib.userModelSelection(null),{curve_id:null,model_selection:null});
});

test('equipment edits patch one row, including confirmed physical sub-assets, without mutation',()=>{
 const plan=[{equipment_key:'a',curve_id:'x'},{equipment_key:'p',physical_assets:[{asset_id:'1',size:2},{asset_id:'2',size:3}]}];
 const frozen=JSON.stringify(plan);
 const next=lib.patchEquipment(plan,'a',{size:5});
 assert.equal(next.find(r=>r.equipment_key==='a').size,5);
 const child=lib.patchEquipment(plan,'p::2',{size:9,equipment_key:'ignored'});
 assert.deepEqual(child.find(r=>r.equipment_key==='p').physical_assets.map(c=>c.size),[2,9]);
 assert.equal(lib.equipmentMapping(child,'p::2').size,9);
 assert.equal(JSON.stringify(plan),frozen);
 assert.equal(lib.patchEquipment(plan,'new',{size:1}).at(-1).equipment_key,'new');
});

test('equipment cards copy Python costs and keep unpriced items unpriced',()=>{
 const state={
  parsed:{report:{entities:[{key:'e1',identifier:'T-1',kind:'equipment',values:[{property:'type',normalized_value:'Tank'}]},{key:'e2',identifier:'P-1',kind:'equipment',values:[]},{key:'s',identifier:'S-1',kind:'material'}]}},
  results:{stages:{equipment:{result:{equipment:[{parsed_source:{equipment_key:'e1'},equipment_tag:'T-1',curve_id:'G1',equipment_cost:'1200',quantity:2,calculation:{estimate:{size:3.14159,size_unit:'m3',currency:'USD'}}}]}}}},
 };
 const plan=[{equipment_key:'e1',curve_id:'G1',model_selection:{origin:'user',curve_id:'G1'}},{equipment_key:'e2',matching_attempt:{match_method:'none'}}];
 const cards=lib.equipmentCards(state,plan,[{id:'G1',equipment:'Tanks',configuration:'Storage',input_requirements:[{name:'size',target_unit:'m3',required:true},{name:'pressure',required:false}]}]);
 assert.equal(cards.length,2);
 assert.equal(cards[0].cost,1200);
 assert.equal(cards[0].status,'priced');
 assert.equal(cards[0].modelOrigin,'user');
 assert.equal(cards[0].size,'3.142 m3');
 assert.equal(cards[0].requiredInputs[0].value,3.14159);
 assert.equal(cards[0].requiredInputs[1].required,false);
 assert.equal(cards[1].cost,null);
 assert.equal(cards[1].status,'unmatched');
});

test('CAPEX lines label their origin and editability from plan and register',()=>{
 const result={lines:[{id:'piping',amount:'10',fraction:'0.2',base:'purchased_equipment',status:'source_factor'},{id:'land',amount:'0',status:'excluded'},{id:'equipment_installation',amount:null,status:'embedded'},{id:'contingency',amount:'5',fraction:'0.1',status:'source_factor'}]};
 const plan={factor_selection:'minimum',selected_factors:{contingency:0.1},exclusions:{land:'owned'},overrides:{}};
 const factors=[{id:'piping',minimum:'.15',maximum:'.70',stage:'direct'},{id:'equipment_installation',additive:false}];
 const register=[{path:'capex.selected_factors.contingency',origin:'ai_proposal'}];
 const lines=lib.capexLines(result,plan,factors,register);
 const by=Object.fromEntries(lines.map(l=>[l.id,l]));
 assert.equal(by.piping.origin,'Source range · Minimum');
 assert.equal(by.piping.min,0.15);
 assert.equal(by.land.origin,'Removed by you');
 assert.equal(by.land.excluded,true);
 assert.equal(by.equipment_installation.editable,false);
 assert.equal(by.contingency.origin,'Selected by AI · provisional');
});

test('financial metrics read the ledger list and stay pending when undefined',()=>{
 const metrics=lib.metricMap({metrics:[['project_npv',{value:'1500000'}],['project_irr',{value:'0.125'}],['project_payback',{value:null,status:'not_recovered'}]]});
 assert.equal(lib.metricText(metrics.get('project_npv'),'money'),'1.5m');
 assert.equal(lib.metricText(metrics.get('project_irr'),'percent'),'12.5%');
 assert.equal(lib.metricText(metrics.get('project_payback'),'years'),'Not reached');
 assert.equal(lib.metricText(undefined,'money'),'Pending');
});

test('Monte Carlo bands come only from backend percentiles',()=>{
 const summary={cash_flow:[{year:1,fcff:{p10:-5,p50:1,p90:4}},{year:2,fcff:{p10:-1,p50:2,p90:6}}]};
 const bands=lib.cashBands(summary);
 assert.deepEqual(bands[0],{year:'1',p10:-5,p50:1,p90:4});
 assert.deepEqual(lib.availablePercentiles({p10:1,p50:2,p90:3,histogram:[]}),['p10','p50','p90']);
 const html=renderToStaticMarkup(React.createElement(FanChart,{title:'fan',rows:bands}));
 assert.match(html,/80% band \(P10–P90\)/);
 assert.doesNotMatch(html,/50% band|90% band/);
 const full=renderToStaticMarkup(React.createElement(FanChart,{title:'fan',rows:[{year:1,p5:-9,p10:-5,p25:-2,p50:1,p75:3,p90:4,p95:8},{year:2,p5:-3,p10:-1,p25:0,p50:2,p75:4,p90:6,p95:9}]}));
 assert.match(full,/50% band \(P25–P75\)/);
 assert.match(full,/90% band \(P5–P95\)/);
 assert.doesNotMatch(full,/NaN|Infinity/);
});

test('charts leave gaps for missing years and render nothing invented',()=>{
 const html=renderToStaticMarkup(React.createElement(LineChart,{title:'t',labels:['Y1','Y2','Y3'],series:[{label:'Cash',values:[1,null,3],tone:'a'}]}));
 assert.doesNotMatch(html,/NaN/);
 const empty=renderToStaticMarkup(React.createElement(LineChart,{title:'t',labels:[],series:[{label:'Cash',values:[],tone:'a'}]}));
 assert.match(empty,/No saved values/);
});

test('guided CSS honours reduced motion',()=>{
 const css=fs.readFileSync(path.join(src,'blocks/guided/guided.css'),'utf8');
 assert.match(css,/@media \(prefers-reduced-motion: reduce\)[^}]*animation: none !important/);
});

test('OPEX headline never shows 0 while categories are pending',()=>{
 const factors=[{id:'raw_materials'},{id:'maintenance'},{id:'administration'},{id:'other_manufacturing',required:false}];
 const none=lib.opexProgress([],factors);
 assert.deepEqual(none,{priced:0,total:3});
 const empty=lib.opexHeadline({complete:false,known_cash_opex_subtotal:'0'},none);
 assert.equal(empty.value,'Pending');
 assert.equal(empty.label,'Pending — 0 of 3 categories priced');
 const some=lib.opexProgress([{category:'maintenance',amount:'1200'},{category:'administration',amount:null}],factors);
 assert.deepEqual(some,{priced:1,total:3});
 const partial=lib.opexHeadline({complete:false,known_cash_opex_subtotal:'1200'},some);
 assert.match(partial.label,/1 of 3 categories priced/);
 assert.equal(partial.note,'Partial subtotal of priced lines only');
 const done=lib.opexHeadline({complete:true,first_year_cash_opex:'5000'},{priced:3,total:3});
 assert.equal(done.label,'Annual cash OPEX · year 1');
 assert.equal(done.note,'');
});

test('only reference defaults are offered for review, with source and range',()=>{
 const config={
  garrett_factors:{
   maintenance:{fraction:0.06,origin:'reference_default',source:'Garrett',page:'p.52',low:'.02',high:'.10',value_basis:'midpoint'},
   supervision:{fraction:0.2,origin:'user'},
  },
  energy:[{id:'e1',name:'EL-1 electricity',origin:'reference_default',tariff_per_kwh:null,rationale:'55.5 kWh/kg × H2 flow'}],
  materials:[{id:'m1',name:'User feed',origin:'user',unit_price:1}],
 };
 const rows=lib.opexProposals(config);
 assert.deepEqual(rows.map(r=>r.id),['maintenance','e1']);
 assert.equal(rows[0].source,'Garrett, p.52');
 assert.match(rows[0].detail,/midpoint of 2\.0%–10\.0%/);
 assert.equal(rows[1].value,'price needed');
});
