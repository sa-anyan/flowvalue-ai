const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
require.extensions['.ts']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,file);
const {revenueSeries,selectedSubtotal,streamColour,streamPalette}=require('../src/components/revenue-series.ts');

const config={sales:[{id:'biomass',name:'Dry biomass'}],commercial_lines:[{id:'service',name:'Treatment'}],pending_inputs:[{id:'prospect',rate:999999}],avoided_costs:[{id:'saving',amount:500}]};
const result={annual:[{year:2,sales_revenue:'0'},{year:1,sales_revenue:'17072'},{year:3,sales_revenue:null}],products:[{year:1,product_id:'biomass',net_sales_revenue:'15072'},{year:2,product_id:'biomass',net_sales_revenue:'0'}],commercial:[{year:1,line_id:'service',revenue:'2000'}]};
test('chart series use saved outputs, sorted years and distinct commercial identities',()=>{
 const {years,streams,total}=revenueSeries(config,result);
 assert.deepEqual(years,['1','2','3']);
 assert.deepEqual(total.values,[17072,0,null]);
 assert.deepEqual(streams.map(s=>s.name),['Dry biomass','Treatment']);
 assert.deepEqual(streams[0].values,[15072,0,null]);
 assert.deepEqual(streams[1].values,[2000,null,null]);
 assert.equal(streams.length,2); // Neither a prospective buyer nor an OPEX saving is income.
});
test('selection subtotal preserves missing years, true zero and immutable model data',()=>{
 const before=JSON.stringify({config,result});
 const {years,streams}=revenueSeries(config,result);
 assert.deepEqual(selectedSubtotal(streams,years).values,[17072,null,null]);
 assert.deepEqual(selectedSubtotal([streams[0]],years).values,[15072,0,null]);
 assert.deepEqual(selectedSubtotal([],years).values,[null,null,null]);
 assert.equal(JSON.stringify({config,result}),before);
});
test('equal product and contract IDs remain separate, with stable colours',()=>{
 const {streams}=revenueSeries({}, {annual:[{year:1,sales_revenue:3}],products:[{year:1,product_id:'same',net_sales_revenue:1}],commercial:[{year:1,line_id:'same',revenue:2}]});
 assert.deepEqual(streams.map(s=>s.id),['product:same','commercial:same']);
 assert.equal(streamColour('product:same'),streams[0].colour);
});
test('stream colours remain distinct for eight lines and independent of toggle order',()=>{
 const ids=Array.from({length:8},(_,i)=>'stream-'+i);
 const forward=streamPalette(ids),reverse=streamPalette(ids.slice().reverse());
 assert.equal(new Set(forward.values()).size,8);
 assert.deepEqual([...forward],[...reverse]);
});
