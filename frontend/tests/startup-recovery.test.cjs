const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const compile=(file)=>ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const lib={exports:{}};
vm.runInNewContext(compile(path.join(__dirname,'../src/lib/startup-recovery.ts')),{exports:lib.exports});
const script=lib.exports.startupRecoveryScript;
function browser({storage=new Map(),blocked=false}={}) {
 const events=new Map(),timers=new Map(),attributes=new Map();let reloads=0,sequence=0;
 const context={location:{pathname:'/flow',search:'?assessment=original&stage=equipment',reload:()=>reloads++},sessionStorage:{getItem:key=>{if(blocked)throw Error('storage disabled');return storage.get(key)||null;},setItem:(key,v)=>{if(blocked)throw Error('storage disabled');storage.set(key,v);}},document:{documentElement:{setAttribute:(k,v)=>attributes.set(k,v),removeAttribute:k=>attributes.delete(k)}},Date:{now:()=>1000000},setTimeout:(fn,delay)=>{timers.set(++sequence,{fn,delay});return sequence;},clearTimeout:key=>timers.delete(key),window:{addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:name=>events.delete(name)}};
 vm.runInNewContext(script,context);
 return {storage,attributes,timers,emit:(event,data={})=>events.get(event)?.(data),expire:()=>[...timers.values()].forEach(t=>t.fn()),reloads:()=>reloads};
}
test('stalled initialization recovers once at 20 seconds, preserving the exact project URL',()=>{
 const first=browser();assert.equal([...first.timers.values()][0].delay,20000);first.expire();assert.equal(first.reloads(),1);
 assert.ok([...first.storage.keys()][0].endsWith('/flow?assessment=original&stage=equipment'));
 const retry=browser({storage:first.storage});retry.expire();assert.equal(retry.reloads(),0);assert.equal(retry.attributes.get('data-fv-startup'),'slow');
});
test('startup completion cancels recovery, including later failures with unsaved work',()=>{
 const page=browser();page.emit('flowvalue-started');page.expire();
 page.emit('error',{target:{tagName:'SCRIPT',src:'http://localhost/_next/failed.js'}});
 page.emit('unhandledrejection',{reason:Error('ChunkLoadError')});
 assert.equal(page.reloads(),0);assert.equal(page.timers.size,0);
});
test('unavailable storage never causes an automatic reload loop',()=>{
 const page=browser({blocked:true});page.expire();assert.equal(page.reloads(),0);assert.equal(page.attributes.get('data-fv-startup'),'slow');
});
test('failed application chunks recover but unrelated extensions do not reload the app',()=>{
 const page=browser();page.emit('error',{target:{tagName:'SCRIPT',src:'chrome-extension://other/script.js'}});assert.equal(page.reloads(),0);
 page.emit('error',{target:{tagName:'SCRIPT',src:'http://localhost/_next/static/chunks/app/flow/page.js'}});assert.equal(page.reloads(),1);
 page.emit('unhandledrejection',{reason:Error('Loading chunk 42 failed')});assert.equal(page.reloads(),1);
});
test('server-rendered controls remain hidden and inert until initialized, with a native reload link',()=>{
 const module={exports:{}};vm.runInNewContext(compile(path.join(__dirname,'../src/components/startup-shell.tsx')),{exports:module.exports,require});
 const html=renderToStaticMarkup(React.createElement(module.exports.StartupShell,null,React.createElement('button',null,'Reset')));
 assert.match(html,/Opening FlowValue/);assert.match(html,/inert=""/);assert.match(html,/aria-hidden="true"/);assert.match(html,/visibility:hidden/);assert.match(html,/<a href="">Reload page<\/a>/);
});
