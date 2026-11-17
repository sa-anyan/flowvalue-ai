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
 if(request.startsWith('.')&&rest[0]?.filename&&!path.extname(request)){const base=path.resolve(path.dirname(rest[0].filename),request);for(const ext of ['.ts','.tsx'])if(fs.existsSync(base+ext))return base+ext;}
 if(request.startsWith('@/')){const base=path.join(src,request.slice(2));for(const ext of ['.ts','.tsx'])if(fs.existsSync(base+ext))return base+ext;}
 return resolve.call(this,request,...rest);
};
require.extensions['.css']=()=>{};
const compile=(module,file,jsx)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,...(jsx?{jsx:ts.JsxEmit.ReactJSX}:{})}}).outputText,file);
require.extensions['.ts']=(m,f)=>compile(m,f,false);
require.extensions['.tsx']=(m,f)=>compile(m,f,true);
const lib=require('../src/lib/guided-flow.ts');
test('Unsaved revenue blocks leaving when Cancel is chosen and allows explicit discard',()=>{
 const {allowRevenueLeave,unsavedRevenueMessage}=require('../src/lib/unsaved-revenue.ts');
 let prompts=0;
 assert.equal(allowRevenueLeave(false,()=>{throw Error('Pristine forms must not prompt');}),true);
 assert.equal(allowRevenueLeave(true,message=>{prompts++;assert.equal(message,unsavedRevenueMessage);return false;}),false);
 assert.equal(allowRevenueLeave(true,()=>{prompts++;return true;}),true);
 assert.equal(prompts,2);
});
test('Revenue dirty tracking includes stream, component, price, units and operating schedule',()=>{
 const {revenueDraftSignature}=require('../src/lib/unsaved-revenue.ts');
 const sale={name:'Water',stream_key:'water-stream',component:'Water',unit_price:'0.2',quantity_unit:'m3'};
 const saved=revenueDraftSignature([sale],'USD','314','24');
 assert.equal(saved,revenueDraftSignature([{...sale}],'USD','314','24'));
 for(const patch of [{name:'Treated water'},{stream_key:'other'},{component:''},{unit_price:'0'},{quantity_unit:'kg'}])
  assert.notEqual(saved,revenueDraftSignature([{...sale,...patch}],'USD','314','24'));
 assert.notEqual(saved,revenueDraftSignature([sale],'GBP','314','24'));
 assert.notEqual(saved,revenueDraftSignature([sale],'USD','330','24'));
 assert.notEqual(saved,revenueDraftSignature([sale],'USD','314','12'));
 assert.notEqual(saved,revenueDraftSignature([],'USD','314','24'));
 // A newer edit remains dirty against the exact snapshot submitted by Save.
 const submitted=revenueDraftSignature([{...sale,unit_price:'0.3'}],'USD','314','24');
 const typedWhileSaving=revenueDraftSignature([{...sale,unit_price:'0.4'}],'USD','314','24');
 assert.notEqual(submitted,typedWhileSaving);
});
test('Reset clears FlowValue history while preserving theme and unrelated data',()=>{
 const {clearFlowValueHistory,freshEntryUrl}=require('../src/lib/reset-history.ts');
 const storage=(entries)=>{
  const values=new Map(Object.entries(entries));
  return {get length(){return values.size},key:i=>Array.from(values.keys())[i]??null,
   getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
 };
 const local=storage({'flowvalue-assessment':'old','flowvalue-pinned-charts':'{}','flowvalue-currency':'GBP','flowvalue-theme':'dark','auth-token':'keep'});
 const session=storage({'flowvalue-draft':'old','other-app':'keep'});
 clearFlowValueHistory(local,session);
 assert.equal(local.getItem('flowvalue-assessment'),null);
 assert.equal(local.getItem('flowvalue-pinned-charts'),null);
 assert.equal(local.getItem('flowvalue-currency'),null);
 assert.equal(local.getItem('flowvalue-theme'),'dark');
 assert.equal(local.getItem('auth-token'),'keep');
 assert.equal(session.getItem('flowvalue-draft'),null);
 assert.equal(session.getItem('other-app'),'keep');
 assert.ok(local.getItem('flowvalue-reset-at'));
 const {assessmentFromUrl}=require('../src/lib/assessment-navigation.ts');
 assert.equal(assessmentFromUrl(freshEntryUrl,'a'.repeat(32)),'');
});
test('Revenue shows the Python 100% annual baseline instead of a year-one forecast',()=>{
 const {RevenuePlayground}=require('../src/blocks/guided/revenue-playground.tsx');
 const result={basis:{currency:'USD',price_period:'2026'},annual:[{year:1,sales_revenue:200}],full_operation:{annual:[{year:1,sales_revenue:1000}],commercial:[{year:1,line_id:'fee',revenue:1000,quantity:500,quantity_unit:'m3'}]}};
 const state={id:'test',plan:{operating_economics:{commercial_lines:[{id:'fee',name:'Treatment',years:[{rate:2}],quantity_unit:'m3'}]}},results:{stages:{revenue:{result}}}};
 const html=renderToStaticMarkup(React.createElement(RevenuePlayground,{hook:{state,aiEnabled:false}}));
 assert.match(html,/100% annual revenue/);assert.match(html,/1k/);assert.match(html,/500/);
 assert.doesNotMatch(html,/Sales revenue · operating year 1|Unpriced — not counted as zero/);
 assert.match(html,/>Edit<\/button>/);
});
test('editing a revenue line opens its saved price, stream, units and approval',()=>{
 const {RevenueLineEditor}=require('../src/blocks/guided/revenue-playground.tsx');
 const existing={id:'fee-original',name:'Treatment fee',category:'processing_services',stream_key:'waste',quantity_unit:'m3',price_basis:{currency:'USD',price_period:'2026'},years:[{year:1,rate:.02},{year:2,rate:.02}]};
 const state={id:'test',revision:42,revenue_approval:{fingerprint:'approved'},plan:{operating_economics:{commercial_lines:[existing],operating:{days_per_year:314,hours_per_day:24}}},effective_report:{entities:[{key:'waste',identifier:'S-1',kind:'material',values:[{property:'volume_flow',normalized_value:125,normalized_unit:'m3/h'}]}]}};
 const html=renderToStaticMarkup(React.createElement(RevenueLineEditor,{state,existing,onClose:()=>{},props:{hook:{state,id:'test'}}}));
 assert.match(html,/Edit Treatment fee/);assert.match(html,/value="0.02"/);assert.match(html,/value="m3"/);
 assert.match(html,/selected="" value="waste"|value="waste" selected=""/);
 assert.match(html,/Save &amp; recalculate/);assert.match(html,/checked=""/);
});
test('OPEX recalculation watches Revenue outputs but does not repeat for polling revisions',()=>{
 const state={id:'test',revision:1,stage_runs:{capex:{output_hash:'capital'},revenue:{output_hash:'old'}}};
 const first=lib.opexDependencyStamp(state);
 assert.equal(lib.opexDependencyStamp({...state,revision:2}),first);
 assert.notEqual(lib.opexDependencyStamp({...state,stage_runs:{...state.stage_runs,revenue:{output_hash:'new'}}}),first);
});
test('OPEX explains root dependencies once instead of cascading engine diagnostics',()=>{
 const q=lib.opexQuestions(['garrett:administration: Missing named calculation base: annual_revenue','garrett:royalties: Missing named calculation base: annual_revenue','garrett:supervision: Missing category base: operating_labor','Missing assumption or explicit exclusion: supervision','Missing assumption or explicit exclusion: operating_labor']);
 assert.equal(q.length,2);
 assert.match(q[0],/resolved once Revenue is reconciled and OPEX is recalculated/);
 assert.match(q[0],/subtotal excludes these allowances/);
 assert.match(q[1],/staffing estimate/);
 assert.deepEqual(lib.opexQuestions(['Missing assumption or explicit exclusion: maintenance']),['Review the maintenance allowance.']);
});
test('AI price filling a previously accepted blank stays visible for review',()=>{
 const rows=lib.opexProposals({materials:[{id:'acid',name:'Acid',origin:'user',unit_price:0.4,quantity_unit:'kg',ai_price_proposal:{origin:'ai',rationale:'Unverified preliminary price'}}]});
 assert.equal(rows.length,1);assert.equal(rows[0].by,'ai');assert.equal(rows[0].editKey,'unit_price');
 assert.match(rows[0].detail,/Unverified/);
});
test('OPEX decimal prices remain editable while evidence and invalid values stay text',()=>{
 assert.equal(lib.opexInputValue('0.125',true),true);
 assert.equal(lib.opexInputValue('0',true),true);
 assert.equal(lib.opexInputValue(null,true),true);
 for(const value of ['', 'NaN', 'Infinity', true, {amount:10}])assert.equal(lib.opexInputValue(value,true),false);
 assert.equal(lib.opexInputValue('123',false),false);
});
test('additional-expense review edits the annual allowance consumed by Python',()=>{
 const proposals=lib.opexProposals({additional_expenses:[{id:'waste',name:'Waste',annual_allowance:'1500',origin:'reference_default',status:'proposed'}]});
 assert.equal(proposals[0].editKey,'annual_allowance');
 assert.match(proposals[0].value,/1,500/);
});
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
 const register=[{path:'capex.selected_factors.contingency',origin:'ai_proposal'},{path:'capex.exclusions.land',origin:'user'}];
 const lines=lib.capexLines(result,plan,factors,register);
 const by=Object.fromEntries(lines.map(l=>[l.id,l]));
 assert.equal(by.piping.origin,'Source range · Minimum');
 assert.equal(by.piping.min,0.15);
 assert.equal(by.land.origin,'Removed by you');
 assert.equal(by.land.excluded,true);
 assert.equal(by.equipment_installation.editable,false);
 assert.equal(by.contingency.origin,'Selected by AI · provisional');
 assert.equal(by.contingency.inUse,true);
 assert.equal(by.piping.inUse,false);
 assert.equal(by.land.inUse,false);
});

test('CAPEX never attributes a saved selection to the user without provenance',()=>{
 const result={lines:[{id:'piping'},{id:'land'},{id:'contingency'}]};
 const plan={selected_factors:{piping:0.2},exclusions:{land:'existing'},overrides:{contingency:100}};
 const lines=lib.capexLines(result,plan,[],[]);
 assert.equal(lines[0].origin,'Provisional selection · review');
 assert.equal(lines[1].origin,'Scope exclusion · review');
 assert.equal(lines[2].origin,'Saved override · review');
 assert.equal(lines[0].inUse,true);
 assert.equal(lines[2].inUse,true);
 assert.ok(lines.every(l=>!l.origin.includes('by you')&&!l.origin.includes('Your')));
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

test('AI proposals from the background brainstorm are offered for review; user values are not',()=>{
 const config={
  garrett_factors:{maintenance:{fraction:.04,origin:'ai',rationale:'AI: clean service'},supervision:{fraction:.12,origin:'user'}},
  labour:[{id:'electricians',role:'Electricians',headcount_fte:6,annual_base_salary:70000,origin:'ai',rationale:'AI'},{id:'ops',role:'Operators',headcount_fte:3,origin:'user'}],
 };
 const rows=lib.opexProposals(config);
 assert.deepEqual(rows.map(r=>`${r.root}:${r.id}:${r.by}`),['garrett_factors:maintenance:ai','labour:electricians:ai']);
 const labour=rows.find(r=>r.root==='labour');
 assert.equal(labour.editKey,'headcount_fte');
 assert.match(labour.value,/^6 FTE/);
 assert.equal(labour.label,'Electricians');
});

test('background brainstorm notice reflects running, ready and failed states, and stays silent without AI',()=>{
 assert.equal(lib.brainstormNotice({status:'running'},false),null);
 assert.equal(lib.brainstormNotice({status:'running'},true),null); // shown by the analyst slot instead
 assert.match(lib.brainstormNotice({status:'ready',added:['labour.a','energy.b']},true).text,/AI added 2 proposals/);
 const failed=lib.brainstormNotice({status:'failed',error:'timeout'},true);
 assert.equal(failed.tone,'failed');
 assert.match(failed.text,/Reference defaults still apply/);
 assert.equal(lib.brainstormNotice(null,true),null);
});

test('Entry lists only streams with a usable flow and previews yearly revenue',()=>{
 const {streamsOf,revenuePreview}=require('../src/blocks/guided/revenue-setup.tsx');
 const report={entities:[
  {kind:'material',key:'s18',identifier:'18',values:[{property:'description',original_value:'Fermented Mash'},{property:'mass_flow',original_value:'#REF!',normalized_value:null},{property:'component_mass_flow',component:'Fibre',original_value:'#REF!',normalized_value:null}]},
  {kind:'material',key:'s13',identifier:'13',values:[{property:'description',original_value:'Treated Water'},{property:'mass_flow',normalized_value:125027.6},{property:'component_mass_flow',component:'Lignin',normalized_value:25},{property:'component_mass_flow',component:'Ash',normalized_value:0}]},
 ]};
 const streams=streamsOf(report);
 assert.deepEqual(streams.map(s=>s.tag),['13']);
 assert.deepEqual(streams[0].components.map(c=>c.name),['Lignin']);
 // 125,027.6 kg/h × 7,920 h × 23 USD/kg ≈ 22.8 bn USD/year: a unit slip is visible before saving.
 assert.ok(Math.abs(revenuePreview(125027.6,'23','kg','330','24')-22.774e9)<0.01e9);
 assert.equal(revenuePreview(25,'17','tonne','330','24'),25*7920*0.001*17);
 assert.equal(revenuePreview(25,'','kg','330','24'),null);
});

test('OPEX review rows show the unit, the yearly quantity and the yearly cost',()=>{
 const quantities=lib.opexQuantities(
  [{id:'feed:sucrose',quantity:'528000',unit:'kg'}],
  [{id:'ref-feed-3',annual_quantity:198201960,unit:'kg'}],
 );
 const config={materials:[
  {id:'ref-feed-3',name:'Wastewater',quantity_unit:'kg',unit_price:1,origin:'reference_default'},
  {id:'sucrose',name:'Sucrose',quantity_unit:'kg',unit_price:0.5,origin:'ai'},
 ]};
 const rows=lib.opexProposals(config,quantities);
 const feed=rows.find(r=>r.id==='ref-feed-3');
 assert.equal(feed.editLabel,'Price per kg');
 assert.deepEqual(feed.quantity,{amount:198201960,unit:'kg'});
 assert.equal(feed.quantity.amount*feed.price,198201960);
 assert.equal(rows.find(r=>r.id==='sucrose').quantity.amount,528000);
});

test('analyst slot: researching placeholder, then the briefing; nothing without AI',()=>{
 const {analystView,analystRunning}=require('../src/blocks/guided/analyst-card.tsx');
 assert.equal(analystView(undefined,false),'off');
 assert.equal(analystView(undefined,true),'researching');
 assert.equal(analystView({status:'running'},true),'researching');
 assert.equal(analystView({status:'running',summary:'old'},true),'updating');
 assert.equal(analystView({status:'ready',summary:'Compact plant'},true),'ready');
 assert.equal(analystView({status:'ready',summary:'Compact plant'},false),'ready'); // saved briefing stays visible
 assert.equal(analystView({status:'failed'},true),'failed');
 assert.equal(analystRunning({analyst:{capex:{status:'ready'},opex:{status:'running'}}}),true);
 assert.equal(analystRunning({analyst:{capex:{status:'ready'}}}),false);
});

test('held AI estimates are listed with both sizes, and the user decides',()=>{
 const conv={enabled:true,inputs:{volumetric_productivity_kg_m3_h:0.2}};
 const rows=[
  {equipment_key:'eq:r1',unit_conversion:{enabled:true,inputs:{volumetric_productivity_kg_m3_h:2}},ai_estimate_guard:{status:'held',
   anchor:{size:15.625,size_unit:'m3',basis:'b'},held:{size:156.25,size_unit:'m3',drift:9,conversion:conv,at:'t',assumptions:[{name:'volumetric_productivity_kg_m3_h',value:0.2,unit:'kg/m3/h'}]}}},
  {equipment_key:'eq:t1',ai_estimate_guard:{status:'stable',anchor:{size:10,size_unit:'m3'}}},
 ];
 const held=lib.heldEstimates(rows);
 assert.equal(held.length,1);
 assert.deepEqual([held[0].anchorSize,held[0].newSize,held[0].unit,held[0].drift],[15.625,156.25,'m3',9]);
 const kept=lib.decideHeld(rows,'eq:r1','keep');
 assert.equal(kept[0].ai_estimate_guard.status,'stable');
 assert.equal(kept[0].unit_conversion.inputs.volumetric_productivity_kg_m3_h,2);
 assert.equal(lib.heldEstimates(kept).length,0);
 const used=lib.decideHeld(rows,'eq:r1','use');
 assert.equal(used[0].unit_conversion,conv);
 assert.deepEqual([used[0].ai_estimate_guard.anchor.size,used[0].ai_estimate_guard.anchor.basis,used[0].ai_estimate_guard.anchor.by],[156.25,'b','user_accepted_ai']);
 assert.equal(used[1],rows[1]);
});

test('edited sizing assumptions show User changed while untouched AI inputs keep their origin',()=>{
 const {EquipmentInspector}=require('../src/blocks/guided/equipment-inspector.tsx');
 const state={id:'test',revision:1,effective_report:{entities:[{key:'tank',identifier:'T-1',kind:'equipment',values:[]}]},results:{stages:{equipment:{result:{equipment:[{equipment_tag:'T-1',parsed_source:{equipment_key:'tank'},equipment_cost:50,calculation:{estimate:{size:.01,size_unit:'m3'},evidence:{below_range_floor:{policy:'minimum_size_floor',requested_size:.01,priced_at_size:.4,size_unit:'m3'}}}}]}}}}};
 const conversion={enabled:true,method:'vessel_volume',inputs:{residence_time_h:1,working_fraction:.8},input_provenance:{residence_time_h:{status:'user_input',value:1,unit:'h'},working_fraction:{status:'llm_estimate',value:.8,unit:'fraction'}}};
 const plan=[{equipment_key:'tank',unit_conversion:conversion}];
 const card=lib.equipmentCards(state,plan)[0];
 assert.equal(card.assumptions[0].origin,'user');
 assert.equal(card.assumptions[1].origin,'ai');
 const html=renderToStaticMarkup(React.createElement(EquipmentInspector,{card,props:{hook:{state,catalogue:[]},equipment:{value:plan,dirty:true}},onClose:()=>{},onRun:()=>{}}));
 assert.match(html,/User changed/);assert.match(html,/AI · provisional/);
 assert.match(html,/Size and cost below show the last calculation/);
 assert.match(html,/minimum of 0.4 m3/);assert.match(html,/does not lower this model/);
 assert.match(html,/Holding \/ residence time/);
});

test('minimum-price explanation is shown only for a Python minimum-size floor',()=>{
 assert.equal(lib.equipmentPriceFloor(null,'missing'),null);
 const state={results:{stages:{equipment:{result:{equipment:[{parsed_source:{equipment_key:'tank'},calculation:{evidence:{}}}]}}}}};
 assert.equal(lib.equipmentPriceFloor(state,'tank'),null);
});

test('Financial exposes proposed values and identifies changed values without rewriting the ledger',()=>{
 const {FinancialPlayground}=require('../src/blocks/guided/financial-playground.tsx');
 const policy={discount_rate:.08,tax_rate:.25,closure_allowance:0};
 const provenance={discount_rate:{origin:'ai',value:.1,rationale:'Preliminary discount scenario'},tax_rate:{origin:'ai',value:.25,rationale:'Flat tax scenario, not verified law'},closure_allowance:{origin:'ai',value:0,rationale:'Closure scope not quantified'}};
 const state={id:'test',plan:{operating_economics:{financial:policy,financial_input_provenance:provenance,price_basis:{currency:'USD'}}},results:{stages:{financial:{result:{currency:'USD',ledger:[{period:{year:0},fcff:'-100',cumulative_project_cash:'-100'}]}}}}};
 const before=JSON.stringify(state);
 const html=renderToStaticMarkup(React.createElement(FinancialPlayground,{hook:{state}}));
 assert.match(html,/Financial planning assumptions · review/);
 assert.match(html,/Discount rate: 8.0%/);assert.match(html,/User changed/);
 assert.match(html,/Tax rate: 25.0%/);assert.match(html,/AI proposed/);
 assert.match(html,/Closure scope not quantified/);
 assert.equal(JSON.stringify(state),before);
});

test('Save & go status line follows the background run and the queued revenue',()=>{
 assert.deepEqual(lib.launchStatus({launch:{status:'running',step:'equipment'}}),{tone:'working',text:'Picking and pricing equipment…'});
 assert.match(lib.launchStatus({launch:{status:'running',step:'capex'},inbox:['revenue_setup']}).text,/your revenue is saved and applies after this step/);
 assert.match(lib.launchStatus({launch:{status:'queued',step:'waiting'}}).text,/^Queued/);
 assert.equal(lib.launchStatus({launch:{status:'finished'}}).tone,'done');
 assert.match(lib.launchStatus({launch:{status:'finished'},plan:{operating_economics:{sales:[{id:'x'}]}}}).text,/Continue to Equipment\.$/);
 assert.match(lib.launchStatus({launch:{status:'failed',error:'boom'}}).text,/stopped: boom/);
 assert.equal(lib.launchStatus({}).tone,'idle');
});

test('Save and go starts with only upload, AI choice and Save',()=>{
 const {EntryStart}=require('../src/blocks/guided/entry-start.tsx');
 const html=renderToStaticMarkup(React.createElement(EntryStart,{hook:{state:null,aiEnabled:true,aiStatus:'enabled'}}));
 assert.match(html,/Upload your mass/);assert.match(html,/type="file"/);assert.match(html,/type="checkbox"/);assert.match(html,/>Save<\/button>/);
 assert.doesNotMatch(html,/Describe your process|Analysis years|Construction years|Extract equipment|Run Autopilot/);
});

test('parsed streams show revenue setup while equipment work continues',()=>{
 const {EntryStart}=require('../src/blocks/guided/entry-start.tsx');
 const state={id:'test',revision:2,launch:{status:'running',step:'equipment'},stage_outputs:{engineering_data:{report:{entities:[{kind:'material',key:'water',identifier:'S-1',values:[{property:'mass_flow',normalized_value:100,normalized_unit:'kg/h'}]}]}}}};
 const html=renderToStaticMarkup(React.createElement(EntryStart,{hook:{state,aiEnabled:true},go:()=>{}}));
 assert.match(html,/REVENUE SETUP/);assert.match(html,/Product Sales/);assert.match(html,/How the project makes money/);
 assert.match(html,/Select product stream/);assert.match(html,/<select[^>]*>/);assert.match(html,/Choose a stream/);
 assert.match(html,/Operating assumptions/);assert.match(html,/Save revenue/);assert.match(html,/Continue to Equipment/);
 assert.doesNotMatch(html,/Reading your workbook|Another assessment is running/);
});

test('Guided Equipment reuses the advanced directory and keeps partial costs visible',()=>{
 const {EquipmentPlayground}=require('../src/blocks/guided/equipment-playground.tsx');
 const state={id:'test',effective_report:{entities:[{key:'tank',kind:'equipment',identifier:'T-1',values:[{property:'name',normalized_value:'Tank'}]},{key:'reactor',kind:'equipment',identifier:'R-1',values:[{property:'name',normalized_value:'Reactor'}]}]},results:{stages:{equipment:{result:{equipment_cost_total:null,equipment_total_with_packages:null,equipment:[{parsed_source:{equipment_key:'tank'},equipment_tag:'T-1',equipment_cost:100,amount:100},{parsed_source:{equipment_key:'reactor'},equipment_tag:'R-1',equipment_cost:null,amount:null}],priced_summary:{amounts:[{amount:'100',currency:'USD',period:'2026'}],unpriced_count:1,priced_count:1},issues:['Unresolved equipment: subtotals are partial; complete total unavailable']}}}}};
 const html=renderToStaticMarkup(React.createElement(EquipmentPlayground,{hook:{state,catalogue:[]},equipment:{value:[],dirty:false}}));
 assert.match(html,/Equipment register/);assert.match(html,/100/);assert.match(html,/peq-price-note[^>]*>\+ installation pending/);assert.match(html,/Needs attention/);
 assert.match(html,/Unpriced/);assert.match(html,/What drives every part of the total/);
});
test('Financial sensitivity renders original calculation values and isolated reset controls',()=>{
 const {ScenarioTab}=require('../src/blocks/guided/financial-playground.tsx');
 const props={hook:{state:{id:'test',plan:{operating_economics:{financial:{tax_rate:.99}}}},busy:false}};
 const base={baseline_snapshot_id:'a'.repeat(64),policy:{tax_rate:'.25',discount_rate:'.1',depreciation_years:'10',salvage_fraction:'0',working_capital_recovery_fraction:'1',closure_allowance:'0'}};
 const render=(overrides,original=base)=>renderToStaticMarkup(React.createElement(ScenarioTab,{props,base:original,baseError:'',overrides,setOverrides:()=>{},onResult:()=>{},onUpdating:()=>{}}));
 const original=render({});
 assert.match(original,/value="25"/);assert.doesNotMatch(original,/value="99"/);
 assert.match(original,/disabled="">Reset to original/);
 const changed=render({tax_rate:.35});assert.match(changed,/value="35"/);
 assert.match(changed,/>Reset to original/);assert.match(changed,/saved as separate versions/);
 assert.doesNotMatch(changed,/Apply &amp; recalculate/);
 assert.match(render({},null),/type="range" disabled=""/);
});
test('Equipment cost breakdown reconciles purchase-only and package costs explicitly',()=>{
 const {EquipmentCostBreakdown}=require('../src/blocks/guided/equipment-cost-breakdown.tsx');
 const summary={amounts:[{amount:'1624335.5531074136',currency:'USD',period:'2026-09',components:[
  {cost_scope:'purchased_equipment',amount:'1329281.5085903038',equipment_tags:['T-001','R-001']},
  {cost_scope:'unit_capital',amount:'295054.0445171098',equipment_tags:['P-001']}
 ]}]};
 const html=renderToStaticMarkup(React.createElement(EquipmentCostBreakdown,{summary,installation:{status:"embedded"}}));
 for(const label of ['1,329,281.51','295,054.04','1,624,335.55','Individual equipment prices · purchase-only factor basis','Equipment systems priced together','P-001','2026-09','does not add another installation factor']) assert.ok(html.includes(label),label);
 assert.match(html,/not split into purchase and installation/);
 assert.match(html,/includes installation within its direct-cost allowances/);
 assert.equal(renderToStaticMarkup(React.createElement(EquipmentCostBreakdown,{summary:{}})),'');
});

test('CAPEX uses one equipment headline from its own saved result',()=>{
 const {CapexPlayground}=require('../src/blocks/guided/capex-playground.tsx');
 const state={id:'test',plan:{},results:{stages:{equipment:{result:{priced_summary:{amounts:[{amount:'9999999'}]}}},capex:{result:{purchased_equipment:'1329281.51',lines:[{id:'unit_capital:P-001',amount:'295054.04',base:'pre_costed_unit_capital'}],equipment_summary:{amounts:[{amount:'1624335.55',currency:'USD',period:'2026-09'}]},total_capex:'7090118.21',currency:'USD',period:'2026-09'}}}}};
 const html=renderToStaticMarkup(React.createElement(CapexPlayground,{hook:{state},capex:{value:{},dirty:false}}));
 assert.match(html,/<small>Equipment cost<\/small><strong>\$1.62m/);
 assert.doesNotMatch(html,/<small>Purchased equipment<\/small>|9.99m|Unit capital:P-001/);
});
test('Monte Carlo condensed selector shows every stage, baseline and named configuration choices',()=>{
 const {ParameterMatrix,ConfigurationChoices}=require('../src/blocks/uncertainty/parameter-matrix.tsx');
 const p={id:'config',label:'R-1 · model',baseline:'model-a',unit:'model_id',kind:'configuration',distribution:'discrete',choices:['model-a'],probabilities:[1],choice_labels:{'model-a':'Stainless fermenter','model-b':'Carbon steel reactor'},targets:[['equipment',0,'curve_id']],source:'Saved catalogue',rationale:'Review configuration',uncertainty:'Provisional',confidence:'Uncalibrated',enabled:true};
 const html=renderToStaticMarkup(React.createElement(ParameterMatrix,{parameters:[p,{...p,id:'price',label:'Water sale',baseline:2,unit:'USD/m3',kind:'economic',targets:[['operating_economics','sales',0,'unit_price']],distribution:'triangular',minimum:1,mode:2,maximum:3}],disabled:false,onChange:()=>{}}));
 for(const text of ['Equipment','Revenue','Baseline','200 variations','Edit Water sale','Edit R-1'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/<details open=|Water sale minimum/);
 const choices=renderToStaticMarkup(React.createElement(ConfigurationChoices,{parameter:p,disabled:false,onChange:()=>{}}));
 for(const text of ['Stainless fermenter','Carbon steel reactor','Use only this'])assert.ok(choices.includes(text),text);
 assert.doesNotMatch(html,/Choices \(JSON array\)/);
});
test('Monte Carlo histogram filters preserve metric eligibility and exact bin boundaries',()=>{
 const {visibleRuns}=require('../src/blocks/uncertainty/run-explorer.tsx');
 const runs=[{index:0,status:'complete',metrics:{npv:10},metric_eligible:['npv']},{index:1,status:'complete',metrics:{npv:20},metric_eligible:['npv']},{index:2,status:'failed',metrics:{npv:15},metric_eligible:[]}];
 assert.deepEqual(visibleRuns(runs,'all','',{metric:'npv',low:10,high:20,includeHigh:false},null).map(r=>r.index),[0]);
 assert.deepEqual(visibleRuns(runs,'all','',{metric:'npv',low:10,high:20,includeHigh:true},null).map(r=>r.index),[0,1]);
 assert.deepEqual(visibleRuns(runs,'all','',null,[1]).map(r=>r.index),[1]);
});
test('Monte Carlo inspection shows applied and fixed configuration with source lineage',()=>{
 const {RunConfiguration}=require('../src/blocks/uncertainty/run-explorer.tsx');
 const run={index:4,status:'complete',configuration:{hash:'verified-hash',fingerprint_verified:true,seed:42,baseline_revision:8,plan:{equipment:[{curve_id:'fermenter',size:105}],capex:{model_id:'garrett'},operating_economics:{materials:[{unit_price:2}],commercial_lines:[{name:'Water'}]}}},metrics:{npv:100}};
 const html=renderToStaticMarkup(React.createElement(RunConfiguration,{run,id:'study',jobId:'job'}));
 for(const text of ['Variation 5','verified-hash','including those held fixed','CAPEX method and factors','Commercial revenue','download=true'])assert.ok(html.includes(text),text);
});

test('Monte Carlo inspection uses an accessible drawer instead of an inline panel',()=>{
 const {AnalysisDrawer}=require('../src/blocks/uncertainty/analysis-drawer.tsx');
 const html=renderToStaticMarkup(React.createElement(AnalysisDrawer,{open:true,title:'Variation 31',onClose:()=>{}},React.createElement('p',null,'Exact saved configuration')));
 assert.match(html,/<dialog[^>]+aria-label="Variation 31"/);
 assert.match(html,/Close analysis drawer/);assert.match(html,/Exact saved configuration/);
 const closed=renderToStaticMarkup(React.createElement(AnalysisDrawer,{open:false,title:'Variation 31',onClose:()=>{}},'Exact saved configuration'));
 assert.doesNotMatch(closed,/Exact saved configuration/);
});
test('equipment histogram filters omit unpriced assets and preserve record identity',()=>{
 const {visibleRuns}=require('../src/blocks/uncertainty/run-explorer.tsx');
 const runs=[{index:0,status:'complete',equipment_costs:{'pump-a':100}},{index:1,status:'partial',equipment_costs:{'pump-a':null}},{index:2,status:'partial',equipment_costs:{'pump-b':100}}];
 assert.deepEqual(visibleRuns(runs,'all','',{metric:'equipment:pump-a',low:90,high:110,includeHigh:true},null).map(r=>r.index),[0]);
});
test('Monte Carlo breakdown shows saved factor bases and charges instead of only technical JSON',()=>{
 const {CalculationBreakdown}=require('../src/blocks/uncertainty/calculation-breakdown.tsx');
 const run={trace_verification:{notice:'Verified frozen variation'},calculation_trace:{capex:{currency:'USD',period:'2026-09',model_id:'garrett',total_capex:'15000',purchased_equipment:'10000',lines:[{id:'piping',amount:'4500',fraction:'.45',base:'purchased_equipment',base_amount:'10000',formula:'fraction * purchased_equipment',source:{reference:'Garrett test source'},status:'source_factor'}]}}};
 const html=renderToStaticMarkup(React.createElement(CalculationBreakdown,{run}));
 for(const text of ['What built these totals?','Equipment','CAPEX','OPEX','Revenue','Verified frozen variation','45%','10,000','4,500','15,000','Garrett test source','successive subtotals']) assert.ok(html.includes(text),text);
 const missing=renderToStaticMarkup(React.createElement(CalculationBreakdown,{run:{trace_verification:{notice:'Replay mismatch'}}}));
 assert.match(missing,/Replay mismatch/);assert.doesNotMatch(missing,/<table/);
});
test('guided saved-project startup shows a loading state instead of a new upload form',()=>{
 const {GuidedFlow}=require('../src/blocks/guided/flow.tsx');
 const html=renderToStaticMarkup(React.createElement(GuidedFlow));
 assert.match(html,/Opening your saved project/);
 assert.match(html,/Loading saved stage/);
 assert.doesNotMatch(html,/Drop your mass|Checking AI availability|Not run/);
});
test('completed analyst research waiting for a safe boundary is labelled clearly',()=>{
 const {AnalystCard,analystRunning}=require('../src/blocks/guided/analyst-card.tsx');
 const state={analyst:{capex:{status:'ready',summary:'Saved research result',pending_application:true}}};
 const html=renderToStaticMarkup(React.createElement(AnalystCard,{stage:'capex',hook:{state,aiEnabled:true}}));
 assert.match(html,/AI research finished/);assert.match(html,/applies after the current calculation/);
 assert.match(html,/Saved research result/);assert.doesNotMatch(html,/gf-analyst-skeleton/);
 assert.equal(analystRunning(state),true);
});


test('shared equipment directory preserves package scope, zero costs, missing installation and source identity',()=>{
 const {equipmentWorkspaceCards}=require('../src/lib/equipment-workspace-cards.ts');
 const entities=['tank','package','zero','missing'].map(key=>({key,identifier:key,kind:'equipment',values:[{property:'name',normalized_value:key}]}));
 const line=(key,fields)=>({equipment_tag:key,parsed_source:{equipment_key:key},calculation:{estimate:{currency:'USD',period:'2026'}},...fields});
 const state={effective_report:{entities},results:{stages:{equipment:{result:{equipment:[
  line('tank',{equipment_cost:'100',installation_cost:null,equipment_and_installation_cost:null}),
  line('package',{cost_scope:'unit_capital',amount:'250',equipment_cost:null}),
  line('zero',{equipment_cost:'0',installation_cost:'0',equipment_and_installation_cost:'0'}),
  line('missing',{equipment_cost:null,amount:null}),
 ]}}}}};
 const before=JSON.stringify(state),cards=equipmentWorkspaceCards(state,[]);
 assert.equal(cards[0].knownCost,100);assert.equal(cards[0].installationPending,true);
 assert.equal(cards[1].knownCost,250);assert.equal(cards[1].capitalBasis,true);assert.equal(cards[1].costBasis,'unit_capital');
 assert.equal(cards[2].knownCost,0);assert.equal(cards[2].cost,'0');
 assert.equal(cards[3].knownCost,undefined);assert.equal(cards[3].cost,'Unpriced');
 assert.deepEqual(cards.map(c=>c.key),['tank','package','zero','missing']);assert.equal(JSON.stringify(state),before);
});

test('shared equipment directory retains user-confirmed physical sub-asset keys',()=>{
 const {equipmentWorkspaceCards}=require('../src/lib/equipment-workspace-cards.ts');
 const plan=[{equipment_key:'parent',scope_confirmation:{status:'user_confirmed'},physical_assets:[{asset_id:'a',equipment_tag:'P-1',size:5,size_unit:'kW',source_value_ids:['name']}]}];
 const state={effective_report:{entities:[{key:'parent',identifier:'Package',kind:'equipment',values:[{id:'name',property:'name',normalized_value:'Pump'}]}]}};
 const cards=equipmentWorkspaceCards(state,plan);
 assert.equal(cards[0].key,'parent::a');assert.equal(cards[0].tag,'P-1');assert.equal(cards[0].name,'Pump');assert.equal(cards[0].size,'5 kW');
});

test('evidence disclosures retain actual page references and defer raw records until opened',()=>{
 const {EvidenceNote,evidencePreview,CapexEvidenceNote}=require('../src/blocks/guided/evidence-note.tsx');
 assert.equal(evidencePreview({reference:'Garrett Table 3-4',printed_page:29,pdf_page:41}),'Garrett Table 3-4 · printed p. 29 · PDF p. 41');
 assert.equal(evidencePreview({note:'Uncited assumption'}),'');
 const html=renderToStaticMarkup(React.createElement(EvidenceNote,{note:'Saved hypothesis',evidence:['S-001'],record:{secretLazyMarker:'not rendered until opened'}}));
 assert.match(html,/identifiers alone are not external citations/);
 assert.doesNotMatch(html,/secretLazyMarker/);
 assert.match(html,/Saved hypothesis/);
 const factor=renderToStaticMarkup(React.createElement(CapexEvidenceNote,{line:{id:'piping',rationale:'Published scope note',source:{reference:'Garrett'}},config:{},factor:{},origin:'review',analyst:{pending_application:true,factors:[{id:'electrical',reasoning:['Wrong factor']},{id:'piping',reasoning:['Saved piping rationale']}]}}));
 assert.match(factor,/Saved piping rationale/);assert.doesNotMatch(factor,/Wrong factor/);
 assert.match(factor,/awaiting application/);assert.match(factor,/not independent source verification/);
});

test('currency prefixes preserve signed money, precision, missing labels and currency identity',()=>{
 const {withCurrency}=require('../src/lib/display-currency.ts');
 assert.equal(withCurrency('1,234.50','USD'),'$1,234.50');
 assert.equal(withCurrency('-12.73m','USD'),'-$12.73m');
 assert.equal(withCurrency('0.00','GBP'),'£0.00');
 assert.equal(withCurrency('1.20m','EUR'),'€1.20m');
 assert.equal(withCurrency('12','CAD'),'C$12');
 assert.equal(withCurrency('12','AED'),'AED 12');
 assert.equal(withCurrency('12',''),'12');
 for(const label of ['Pending','Not reached','Not calculated','—','$12.00'])assert.equal(withCurrency(label,'USD'),label);
});

test('evidence links require explicit web URLs and use actual PDF page numbers',()=>{
 const {evidenceLink}=require('../src/blocks/guided/evidence-note.tsx');
 assert.equal(evidenceLink({filename:'Garrett.pdf',printed_page:29,pdf_page:41}),null);
 assert.equal(evidenceLink({url:'javascript:alert(1)'}),null);
 assert.equal(evidenceLink({url:'file:///private/reference.pdf'}),null);
 assert.equal(evidenceLink({url:'https://example.org/reference.pdf',printed_page:29,pdf_page:41}),'https://example.org/reference.pdf#page=41');
 assert.equal(evidenceLink({url:'https://example.org/article',pdf_page:41}),'https://example.org/article');
});

test('reference display never manufactures publisher links from a source hash',()=>{
 const {evidenceTarget}=require('../src/lib/evidence-source-links.ts');
 assert.equal(evidenceTarget({sha256:'fe1084a476baece3a8afd4711311780b314b08ca085dbcb766f193903bfe3eff',printed_page:29,pdf_page:41}),null);
});

test('AI claim citations render only retrieval-grounded links and preserve hypothesis labels',()=>{
 const {AICitations}=require('../src/blocks/guided/ai-citations.tsx');
 const html=renderToStaticMarkup(React.createElement(AICitations,{basis:'engineering_hypothesis',citations:[{id:'S1',url:'https://example.org/source',title:'Retrieved reference',status:'retrieved',locator:'Section 2'},{id:'S2',url:'https://invented.example/',title:'Invented',status:'unverified_url_rejected'}]}));
 assert.match(html,/href="https:\/\/example.org\/source"/);assert.match(html,/Engineering hypothesis/);assert.doesNotMatch(html,/href="https:\/\/invented/);
});

test('Revenue flow sources distinguish whole stream and components without guessing volume',()=>{
 const {revenueRateSources}=require('../src/blocks/revenue/rate-lines.ts');
 const sources=revenueRateSources({entities:[{kind:'material',key:'s',identifier:'S-1',values:[
  {property:'mass_flow',normalized_value:1000,normalized_unit:'kg/h'},
  {property:'component_mass_flow',component:'Lignin',normalized_value:25,normalized_unit:'kg/h'},
  {property:'component_mass_flow',component:'Water',normalized_value:975,normalized_unit:'kg/h'},
  {property:'component_mass_flow',component:'Conflicted',normalized_value:1,normalized_unit:'kg/h'},
  {property:'component_mass_flow',component:'Conflicted',normalized_value:2,normalized_unit:'kg/h'},
  {property:'component_mass_flow',component:'Missing',normalized_value:null,normalized_unit:'kg/h'},
 ]}]});
 assert.deepEqual(sources.map(s=>[s.component,s.rate,s.unit]),[[null,1000,'kg/h'],['Lignin',25,'kg/h'],['Water',975,'kg/h']]);
 assert.equal(new Set(sources.map(s=>s.id)).size,3);
});
test('Revenue editor restores the saved component and displays its flow, not the stream total',()=>{
 const {RevenueLineEditor}=require('../src/blocks/guided/revenue-playground.tsx');
 const existing={id:'lignin',name:'Lignin sale',stream_key:'s',component:'Lignin',quantity_unit:'kg',unit_price:2,price_mode:'assumed_price'};
 const state={id:'test',revision:1,plan:{operating_economics:{sales:[existing],operating:{days_per_year:300,hours_per_day:24}}},effective_report:{entities:[{kind:'material',key:'s',identifier:'S-1',values:[{property:'mass_flow',normalized_value:1000,normalized_unit:'kg/h'},{property:'component_mass_flow',component:'Lignin',normalized_value:25,normalized_unit:'kg/h'}]}]}};
 const html=renderToStaticMarkup(React.createElement(RevenueLineEditor,{state,existing,onClose:()=>{},props:{hook:{state,id:'test'}}}));
 assert.match(html,/What is sold/);assert.match(html,/<option value="Lignin" selected=""/);
 assert.match(html,/<output>25 kg\/h<\/output>/);assert.doesNotMatch(html,/<output>1000 kg\/h/);
});
