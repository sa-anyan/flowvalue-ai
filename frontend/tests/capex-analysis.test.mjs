import { test } from "node:test";
import assert from "node:assert/strict";
import { capitalAmount, capitalGroup, capitalScope, capitalCoverage, capitalRowIssues, capitalChecks } from "../src/lib/capex-analysis.ts";

const row = (patch={}) => ({item_id:"C1",description:"Piping",category:"Direct Costs / Piping",cost_type:"capex",status:"included",quantity:2,unit:"m",rate_usd:125,allocation_fraction:.5,cost_arrangement:"incremental",basis:"Independent test quantity and current USD rate",evidence_ids:["Q1"],...patch});
const project = (rows=[],equipment=[]) => ({costing:{equipment},study:{cost_items:rows,evidence:[{evidence_id:"Q1",kind:"quotation",title:"Synthetic quote",reference:"Independent software fixture",source_url:null}]}});

test("capital quantities, rates and allocations reconcile independently",()=>{
  assert.equal(capitalAmount(row()),125);
  assert.equal(capitalAmount(row({rate_usd:0})),0);
  assert.equal(capitalAmount(row({allocation_fraction:0})),0);
  assert.equal(capitalAmount(row({quantity:4,rate_usd:250,allocation_fraction:.25})),250);
});

test("missing, invalid and out-of-scope costs never become healthy zeroes",()=>{
  for (const patch of [{quantity:null},{rate_usd:null},{quantity:-1},{quantity:1e13},{rate_usd:1e13},{rate_usd:Infinity},{allocation_fraction:1.1},{allocation_fraction:-.1},{allocation_fraction:NaN},{status:"missing"},{status:"excluded"},{status:"unsupported"},{status:"not_applicable"},{cost_arrangement:"charged_elsewhere"},{cost_type:"utilities"}]) assert.equal(capitalAmount(row(patch)),null,JSON.stringify(patch));
});

test("scope assignment preserves legacy group names without guessing partial descriptions",()=>{
  assert.equal(capitalGroup(row({category:"direct_costs"})),"direct-costs");
  assert.equal(capitalGroup(row({category:"Indirect Costs / Contingency"})),"indirect-costs");
  assert.equal(capitalGroup(row({category:"Working Capital"})),"working-capital");
  assert.equal(capitalGroup(row({category:"Miscellaneous"})),"unclassified");
  assert.equal(capitalScope(row()).code,"D03");
  assert.equal(capitalScope(row({category:"Direct Costs",description:"Special piping package — scope undecided"})),undefined);
});

test("coverage counts unknown scope separately and sums multiple included entries exactly once",()=>{
  const p=project([row(),row({item_id:"C2",quantity:1,rate_usd:50,allocation_fraction:1}),row({item_id:"C3",status:"excluded",quantity:100})]);
  const coverage=capitalCoverage(p);
  const piping=coverage.find(c=>c.scope.code==="D03");
  assert.equal(piping.amount,175);
  assert.equal(piping.rows.length,3);
  assert.equal(coverage.find(c=>c.scope.code==="D08").amount,null);
  assert.equal(coverage.find(c=>c.scope.code==="D08").status,"Not assessed");
});

test("documented exclusions and zero amounts remain distinct from missing inputs",()=>{
  const n=capitalCoverage(project([row({category:"Direct Costs / Land",description:"Land",status:"not_applicable",quantity:null,rate_usd:null,basis:"Existing site, no land purchase"})])).find(c=>c.scope.code==="D08");
  assert.equal(n.status,"Not applicable");assert.equal(n.amount,null);
  const zero=capitalCoverage(project([row({rate_usd:0})])).find(c=>c.scope.code==="D03");
  assert.equal(zero.amount,0);assert.equal(zero.status,"Documented input");
});

test("installation overlap is flagged without applying another installation factor",()=>{
  const p=project([row()],[{unit_id:"P1",kind:"pump"}]);
  assert.ok(capitalRowIssues(p.study.cost_items[0],p).some(s=>s.includes("overlap")));
  assert.equal(capitalAmount(p.study.cost_items[0]),125);
});

test("assumptions alone are not misrepresented as sourced cost evidence",()=>{
  const p=project([row()]);p.study.evidence[0].kind="assumption";
  assert.ok(capitalRowIssues(p.study.cost_items[0],p).some(s=>s.startsWith("Link a")));
  p.study.evidence[0].kind="quotation";
  assert.ok(!capitalRowIssues(p.study.cost_items[0],p).some(s=>s.startsWith("Link a")));
});

test("exclusion reasons, unsupported methods and unconverted source currency remain visible",()=>{
  assert.ok(capitalRowIssues(row({status:"excluded",basis:""}),project()).length);
  assert.ok(capitalRowIssues(row({status:"unsupported"}),project()).some(s=>s.includes("supported method")));
  assert.ok(capitalRowIssues(row({basis:"GBP quotation, 2023"}),project()).some(s=>s.includes("currency conversion")));
});

test("engineering worklist links to the affected saved scope item without mutating project data",()=>{
  const p=project([row({item_id:'C1 & / "',basis:"",evidence_ids:[]})]);const before=JSON.stringify(p);
  const checks=capitalChecks(p);
  assert.ok(checks.length>0);
  assert.ok(checks.every(c=>c.href.startsWith('/capex/direct-costs#capital-C1%20%26%20%2F%20%22')));
  assert.equal(JSON.stringify(p),before);
});
