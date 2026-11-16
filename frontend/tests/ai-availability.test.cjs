const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module'),ts=require('typescript');
const effects=[],statuses=[];
const originalLoad=Module._load,originalResolve=Module._resolveFilename;
Module._resolveFilename=function(request,...rest){
 if(request.startsWith('@/')){const base=path.join(__dirname,'../src',request.slice(2));for(const ext of ['.ts','.tsx'])if(fs.existsSync(base+ext))return base+ext;}
 return originalResolve.call(this,request,...rest);
};
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const fakeReact={useState:value=>[value,next=>{if(value==='checking')statuses.push(next)}],useEffect:effect=>effects.push(effect),useRef:value=>({current:value}),useCallback:fn=>fn};
Module._load=function(request,...rest){return request==='react'?fakeReact:originalLoad.call(this,request,...rest)};
const {useAssessment}=require('../src/blocks/guided/use-assessment.ts');
Module._load=originalLoad;

test('AI availability recovers after network failure and server restart without reloading',async()=>{
 const before={fetch:global.fetch,window:global.window,setTimeout:global.setTimeout,clearTimeout:global.clearTimeout};
 const timers=new Map();let serial=0,focus,enabled=true,fail=true;
 global.setTimeout=(fn,delay)=>{const id=++serial;timers.set(id,{fn,delay});return id};
 global.clearTimeout=id=>timers.delete(id);
 global.window={addEventListener:(name,fn)=>{if(name==='focus')focus=fn},removeEventListener:()=>{focus=null}};
 global.fetch=async()=>{if(fail)throw new Error('Temporary network failure');return {ok:true,json:async()=>({ai_enabled:enabled})}};
 try{
  const hook=useAssessment();assert.equal(hook.aiStatus,'checking');assert.equal(hook.aiEnabled,false);
  const stop=effects[1]();await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(statuses,['unavailable']); // Never misreport a failed request as disabled.
  const retry=[...timers.values()].find(t=>t.delay===3000);assert.ok(retry);
  fail=false;await retry.fn();assert.equal(statuses.at(-1),'enabled');
  enabled=false;focus();await new Promise(resolve=>setImmediate(resolve));assert.equal(statuses.at(-1),'disabled');
  enabled=true;focus();await new Promise(resolve=>setImmediate(resolve));assert.equal(statuses.at(-1),'enabled');
  stop();assert.equal(focus,null);assert.equal(timers.size,0);
 }finally{Object.assign(global,before)}
});
