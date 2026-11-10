const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {revenueLines}=require('../src/blocks/revenue/rate-lines.ts');
test('custom rate draft retains its value, units and pending user confirmation',()=>{
 const [line]=revenueLines({sales:[{id:'water',price_mode:'assumed_price',unit_price:5,manual_rate:{value:2,unit:'m3/h',confirmed_by_user:false}}]});
 assert.equal(line.rate,2);assert.equal(line.rate_unit,'m3/h');assert.equal(line.confirmRate,true);assert.equal(line.advanced,false);
});
test('missing price stays missing while a zero user price remains explicit',()=>{
 const rows=revenueLines({sales:[{id:'missing',unit_price:null},{id:'zero',unit_price:0}]});
 assert.equal(rows[0].price,null);assert.equal(rows[1].price,0);
});
test('complex annual contract terms remain in the advanced workflow',()=>{
 const rows=revenueLines({commercial_lines:[{id:'simple',payment_rule:'variable_fee',rate_period:'per_unit',years:[{year:1,rate:5},{year:2,rate:5}]},{id:'annual',payment_rule:'variable_fee',rate_period:'per_unit',years:[{year:1,rate:5},{year:2,rate:6}]}]});
 assert.equal(rows[0].advanced,false);assert.equal(rows[1].advanced,true);
});
test('each income line retains its price period rather than inheriting an unrelated historical basis',()=>{
 const [line]=revenueLines({price_basis:{price_period:'1987'},sales:[{id:'water',price_basis:{price_period:'2026'}}]});
 assert.equal(line.price_period,'2026');
});
const {requiresTerms}=require('../src/blocks/revenue/rate-lines.ts');
test('co-products retain their role and saved price evidence range',()=>{
 const [line]=revenueLines({sales:[{id:'co',role:'byproduct',price_mode:'assumed_price',price_review:{minimum:13,maximum:34,selected:24,rationale:'User scenario'}}]});
 assert.equal(line.category,'product_sales');assert.equal(line.role,'byproduct');assert.equal(line.price_review.minimum,13);assert.equal(requiresTerms(line),false);
});
test('fixed commercial income opens its own terms rather than physical flow fields',()=>{
 const [line]=revenueLines({commercial_lines:[{id:'license',category:'other_contractual_income',quantity_unit:'payment',rate_period:'per_unit',years:[{year:1,rate:0,fixed_payment:50},{year:2,rate:0,fixed_payment:50}]}]});
 assert.equal(line.advanced,false);assert.equal(requiresTerms(line),true);
});
