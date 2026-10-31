'use client';
import {useState} from 'react';
export default function Login(){
 const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 return <main style={{maxWidth:520,margin:'8vh auto',padding:24}}><h1>Sign in to FlowValue AI</h1><p>Your rebuilt workspace is private to your existing FlowValue account.</p><form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{const r=await fetch('/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});const v=await r.json();if(!r.ok)throw Error(v.detail);window.location.assign('/entry');}catch(e){setError((e as Error).message);setBusy(false);}}}>
 <label className="field"><span>Email</span><input type="email" autoComplete="username" value={email} required onChange={e=>setEmail(e.target.value)}/></label>
 <label className="field"><span>Password</span><input type="password" autoComplete="current-password" value={password} required onChange={e=>setPassword(e.target.value)}/></label>
 {error&&<p role="alert" className="error">{error}</p>}<button disabled={busy}>{busy?'Signing in…':'Sign in'}</button></form></main>;
}
