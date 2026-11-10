const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const ts=require('typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {displayInput,storedInput}=require('../src/blocks/revenue/simple-inputs.ts');
test('friendly percentages round-trip without changing the canonical fraction',()=>{assert.equal(displayInput(.95,true),95);assert.equal(storedInput('95',true),'0.95');assert.equal(storedInput('100',true),'1');assert.equal(storedInput('-10',true),'-0.1');});
test('empty and ordinary money inputs stay untouched',()=>{assert.equal(displayInput('',true),'');assert.equal(storedInput('',true),'');assert.equal(storedInput('10000',false),'10000');assert.equal(displayInput(0,true),0);});
