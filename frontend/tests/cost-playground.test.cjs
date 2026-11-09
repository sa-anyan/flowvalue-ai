const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
require.extensions['.css']=()=>{};
require.extensions['.tsx']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText.replace('require("@/lib/assessment-navigation")','require("../../lib/assessment-navigation.ts")'),file);
require.extensions['.ts']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,file);
const {CostPlayground}=require('../src/blocks/shared/cost-playground.tsx');
const render=props=>renderToStaticMarkup(React.createElement(CostPlayground,{id:'test',assumptions:{},...props}));
test('empty dashboard points to engineering data without inventing metrics or execution controls',()=>{
 const html=render({domain:'capex'});assert.match(html,/No calculation completed/);assert.match(html,/Investment contributions/);assert.doesNotMatch(html,/<button[^>]*>[^<]*(?:Run|Recalculate)/);
});
test('CAPEX uses saved subtotals without adding equipment twice',()=>{
 const result={currency:'USD',period:'2026',total_capex:1000,purchased_equipment:200,fixed_capital:800,startup_expenses:100,working_capital:100,direct_costs:600,indirect_costs:200,lines:[{id:'piping',amount:40}]};
 const original=JSON.stringify(result),html=render({domain:'capex',result});assert.match(html,/1k/i);assert.match(html,/not added twice/);assert.match(html,/Piping/);assert.doesNotMatch(html,/<button[^>]*>[^<]*(?:Run|Recalculate)/);assert.equal(JSON.stringify(result),original);
});
test('OPEX ranking excludes financing and depreciation and honours last saved year',()=>{
 const result={currency:'USD',years:{1:{annual_cash_opex:0,lines:[]},2:{annual_cash_opex:50,cash_fixed:10,cash_variable:40,depreciation:5,lines:[{id:'electricity',amount:50,accounting:'cash',scope:'recurring'},{id:'excluded depreciation',amount:999,accounting:'noncash',scope:'recurring'}]}}};
 const html=render({domain:'opex',result});assert.match(html,/Operating year 2/);assert.match(html,/Electricity/);assert.doesNotMatch(html,/Excluded Depreciation/);assert.match(html,/Inspect operating year/);
});
test('zero is retained, missing data and stale outputs remain explicit',()=>{
 const html=render({domain:'capex',stale:true,result:{total_capex:0,complete:false,lines:[]}});assert.match(html,/Known subtotal/);assert.match(html,/Inputs have changed/);assert.match(html,/Not available|—/);assert.doesNotMatch(html,/<button[^>]*>[^<]*(?:Run|Recalculate)/);
});
test('negative annual cash values remain within the chart and missing years create gaps',()=>{
 const html=render({domain:'opex',result:{years:{1:{annual_cash_opex:-10},2:{annual_cash_opex:null},3:{annual_cash_opex:20}}}});
 assert.doesNotMatch(html,/NaN|Infinity/);
 assert.equal((html.match(/stroke="#b18443"/g)||[]).length,0);
 assert.match(html,/cy="30"/);
});

test('blocked stage shows its actual error within the dashboard',()=>{
 const html=render({domain:'opex',issues:['AI review exceeded context limit']});
 assert.match(html,/AI review exceeded context limit/);assert.match(html,/Operating cost drivers/);
});

test('missing OPEX inputs show a review notice and no zero trajectory',()=>{
 const result={complete:false,currency:'USD',years:{1:{annual_cash_opex:null,resolved_cash_subtotal:0,lines:[{accounting:'financing',scope:'recurring',amount:0}]}},operating_detail:{years:{1:{pending_items:[{id:'utilities'}]}}}};
 const html=render({domain:'opex',result});
 assert.match(html,/OPEX inputs are missing/);assert.match(html,/1 input needs review/);assert.doesNotMatch(html,/<circle/);
});
