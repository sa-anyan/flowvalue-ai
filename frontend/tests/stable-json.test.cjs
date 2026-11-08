const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const ts=require('typescript');
require.extensions['.ts']=(module,file)=>module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText,file);
const {stableJson}=require('../src/lib/stable-json.ts');
test('saved inputs compare equally after SQLite key sorting',()=>{
  assert.equal(stableJson([{size:1000,options:{target:'US',source:'US'},id:'tank'}]),stableJson([{id:'tank',options:{source:'US',target:'US'},size:1000}]));
});
test('real edits and ordered array changes stay dirty',()=>{
  assert.notEqual(stableJson([1,2]),stableJson([2,1]));
  assert.notEqual(stableJson({size:1}),stableJson({size:2}));
});
