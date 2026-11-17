const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
const ts=require('typescript'),React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const src=path.join(__dirname,'..','src'),resolve=Module._resolveFilename;
Module._resolveFilename=function(request,...rest){
 if(request.startsWith('.')&&rest[0]?.filename&&!path.extname(request)){const base=path.resolve(path.dirname(rest[0].filename),request);for(const ext of ['.ts','.tsx'])if(fs.existsSync(base+ext))return base+ext;}
 if(request.startsWith('@/')){const base=path.join(src,request.slice(2));for(const ext of ['.ts','.tsx'])if(fs.existsSync(base+ext))return base+ext;}
 return resolve.call(this,request,...rest);
};
require.extensions['.css']=()=>{};
for(const ext of ['.ts','.tsx'])require.extensions[ext]=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2020}}).outputText,file);
const {analystNumber,costReconciliation,groupCostNodes,paretoRows,capexCostTree,opexCostTree,revenueCostTree,treemapRects,analystCsv}=require('../src/lib/analyst-costs.ts');
const node=(id,amount,children=[])=>({id,label:id,amount,children,record:{source:'Synthetic independent fixture'},grain:'Saved record'});
test('chart amounts reject unknowns and retain explicit zero and signed values',()=>{
 for(const value of [null,undefined,'',' ',true,false,[],{},Infinity,'not priced'])assert.equal(analystNumber(value),null);
 assert.equal(analystNumber('0'),0);assert.equal(analystNumber('-12.25'),-12.25);
});
test('grouped subtotals never conceal unknown descendant costs or reconciliation gaps',()=>{
 const grouped=groupCostNodes([node('known',75),node('pending',null)],()=> 'Category');
 const report=costReconciliation(node('root',100,grouped));assert.equal(report.known,75);assert.equal(report.delta,25);assert.equal(report.unresolved,1);assert.equal(report.complete,false);
 const partial=costReconciliation(node('root',75,grouped));assert.equal(partial.matches,true);assert.equal(partial.complete,false);
});
test('CAPEX follows counted breakdown and does not add embedded installation, subtotal or alias charges',()=>{
 const result={total_capex:'130',lines:[{id:'piping',amount:'30',base_amount:'100',fraction:'.3',formula:'fraction * purchased_equipment',source:'Test citation'}],breakdown:[
  {category:'purchased_equipment',label:'Purchase',counted:true,amount:'100'},
  {category:'piping',label:'Piping',counted:true,amount:'30',factors:[{id:'piping',amount:'30'}]},
  {category:'installation',counted:false,status:'combined',amount:null,combined_into:'piping'},
  {category:'owners',counted:false,status:'gap',amount:null},
 ]};
 const equipment=[{equipment_tag:'P-1',equipment_cost:'100',cost_scope:'purchased_equipment'}, {equipment_tag:'Alias',equipment_cost:'100',cost_scope:'purchased_equipment',cost_status:'alias_reference'}];
 const original=JSON.stringify({result,equipment}),root=capexCostTree(result,equipment);
 assert.equal(root.children.length,3);assert.equal(root.children[0].children.length,1);assert.equal(costReconciliation(root).known,130);assert.equal(costReconciliation(root).unresolved,1);
 assert.equal(root.children[1].children[0].record.source,'Test citation');assert.match(root.children[1].children[0].grain,/item quantities not supplied/);assert.equal(JSON.stringify({result,equipment}),original);
});
test('OPEX uses the selected saved year and keeps noncash and financing outside the cash graph',()=>{
 const root=opexCostTree({currency:'USD',years:{'1':{annual_cash_opex:10,lines:[]},'2':{annual_cash_opex:30,lines:[{id:'power',category:'utilities',accounting:'cash',amount:30,quantity:100,rate:.3,method:'quantity_price'},{id:'depreciation',accounting:'noncash',amount:900}]}}},'2','category');
 assert.equal(root.amount,30);assert.equal(root.children.length,1);assert.equal(root.children[0].children[0].record.quantity,100);assert.equal(costReconciliation(root).known,30);assert.equal(root.record.excluded_non_cash.length,1);
});
test('income composition keeps pending lines and avoids counting avoided OPEX as sales',()=>{
 const root=revenueCostTree({annual:[{sales_revenue:90}],products:[{product_id:'food',net_sales_revenue:90,quantity_sold:10}]},{sales:[{id:'food',name:'Food',unit_price:9},{id:'pending',name:'Unpriced'}],avoided_costs:[{amount:1000}]});
 assert.equal(costReconciliation(root).known,90);assert.equal(costReconciliation(root).unresolved,1);assert.equal(root.amount,90);
});
test('Pareto uses all known nonnegative records and refuses percentage concentration for credits',()=>{
 const rows=paretoRows([node('a',20),node('b',80),node('unknown',null),node('zero',0)]);
 assert.equal(rows[0].node.id,'b');assert.equal(rows[0].share,.8);assert.equal(rows.at(-1).share,1);assert.equal(paretoRows([node('a',100),node('credit',-10)]),null);
});
test('treemap tile areas retain the exact known-value proportions without assigning area to missing or zero',()=>{
 const rects=treemapRects([node('a',60),node('b',30),node('c',10),node('zero',0),node('unknown',null)]);
 assert.equal(rects.length,3);for(const tile of rects)assert.ok(Math.abs(tile.width*tile.height/100-Number(tile.node.amount))<1e-8);
 assert.ok(Math.abs(rects.reduce((s,r)=>s+r.width*r.height,0)-10000)<1e-8);
});
test('chart CSV keeps saved decimals, revision and record paths and neutralises formula-like labels',()=>{
 const root=node('root','10.123456',[{...node('  =HYPERLINK("bad")','10.123456'),label:'  =HYPERLINK("bad")'}]);
 const csv=analystCsv(root,'USD','2026-09','17');assert.match(csv,/10.123456/);assert.match(csv,/2026-09/);assert.match(csv,/"17"/);assert.match(csv,/"'  =HYPERLINK/);
});
test('workbench renders explicit scope and trace controls rather than claiming itemised takeoffs',()=>{
 const {AnalystCostExplorer}=require('../src/blocks/guided/analyst-cost-explorer.tsx');
 const html=renderToStaticMarkup(React.createElement(AnalystCostExplorer,{root:node('Saved capital',100,[node('Piping',100),node('Missing bolts',null)]),currency:'USD',period:'2026',revision:'17'}));
 assert.match(html,/Pareto \/ concentration/);assert.match(html,/Contribution waterfall/);assert.match(html,/Exact ledger/);assert.match(html,/unresolved scope remains/);assert.match(html,/does not specify the number of bolts/);assert.doesNotMatch(html,/NaN|Infinity/);
});


test('equipment composition keeps source scopes and monetary bases separate and counts packages once',()=>{
 const {equipmentCostTree}=require('../src/lib/analyst-costs.ts');
 const basis={currency:'USD',period:'2026',amount:'130',components:[{cost_scope:'purchased_equipment',amount:'100',equipment_tags:['P-1']},{cost_scope:'unit_capital',amount:'30',equipment_tags:['Pack']}]};
 const root=equipmentCostTree({equipment:[{equipment_tag:'P-1',cost_scope:'purchased_equipment',equipment_cost:100},{equipment_tag:'Pack',cost_scope:'unit_capital',amount:30},{equipment_tag:'EUR-1',cost_scope:'purchased_equipment',equipment_cost:999},{equipment_tag:'Alias',cost_scope:'purchased_equipment',equipment_cost:100,cost_status:'alias_reference'}]},basis);
 assert.equal(costReconciliation(root).known,130);assert.equal(root.children[0].children.length,1);assert.equal(root.children[1].children[0].amount,30);assert.equal(root.record.currency,'USD');assert.equal(root.record.period,'2026');
});

test('responsive treemap preserves tiny records and nonoverlapping proportional areas across aspect ratios',()=>{
 const inputs=[node('large',754540),node('second',328000),node('third',141910),node('small',5690),node('tiny',1),node('pending',null),node('zero',0)];
 const original=inputs.map(n=>n.id);const total=inputs.reduce((s,n)=>s+(Number(n.amount)||0),0);
 for(const aspect of [.5,1,1.6,3]){
  const rects=treemapRects(inputs,aspect);assert.equal(rects.length,5);
  for(const r of rects){assert.ok(r.width>0&&r.height>0);assert.ok(r.x>=0&&r.y>=0&&r.x+r.width<=100+1e-9&&r.y+r.height<=100+1e-9);assert.ok(Math.abs(r.width*r.height/10000-Number(r.node.amount)/total)<1e-10);}
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
   const a=rects[i],b=rects[j];const w=Math.max(0,Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x));const h=Math.max(0,Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y));assert.ok(w*h<1e-8);
  }
 }
 assert.deepEqual(inputs.map(n=>n.id),original);
});
