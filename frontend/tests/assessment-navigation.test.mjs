import test from 'node:test';
import assert from 'node:assert/strict';
import {assessmentHref,assessmentFromUrl} from '../src/lib/assessment-navigation.ts';
const before='2f2c8ed1d44e49dba0d73d965e81659b',after='50b9d4260f984da3bf4f2100694b538f';
test('pinned assessment wins over another tabs stored selection',()=>{
  assert.equal(assessmentFromUrl('http://localhost:3000/revenue?assessment='+after,before),after);
  assert.equal(assessmentFromUrl('http://localhost:3000/revenue?assessment='+before,after),before);
});
test('all model links preserve the selected assessment',()=>{
  for(const page of ['/entry','/data','/capex/equipment','/capex','/opex','/revenue','/financial-modelling']) {
    const href=assessmentHref(page,after);assert.equal(assessmentFromUrl(href,before),after);
  }
});
test('selecting a new upload/version replaces the old URL id without losing location',()=>{
  const next=assessmentHref('/entry?view=details&assessment='+before+'#equipment',after);
  const url=new URL(next,'http://localhost');assert.equal(url.pathname,'/entry');assert.equal(url.searchParams.get('view'),'details');
  assert.equal(url.searchParams.getAll('assessment').length,1);assert.equal(url.hash,'#equipment');assert.equal(assessmentFromUrl(next,before),after);
});
test('malformed stored selections and external navigation are rejected',()=>{
  assert.equal(assessmentFromUrl('/entry?assessment=invalid','also invalid'),'');
  assert.throws(()=>assessmentHref('https://example.com/steal',after));
});
