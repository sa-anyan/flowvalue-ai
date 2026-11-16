'use client';
import {useEffect,useState} from 'react';

type Theme='light'|'dark';
const KEY='flowvalue-genesis-theme';
export function GenesisThemeToggle(){
 const [theme,setTheme]=useState<Theme>('light');
 useEffect(()=>{
  let stored: string|null=null;
  try{stored=window.localStorage.getItem(KEY);}catch{}
  const next:Theme=stored==='dark'?'dark':'light';
  document.documentElement.dataset.genesisTheme=next;
  setTheme(next);
 },[]);
 function toggle(){
  const next:Theme=theme==='light'?'dark':'light';
  document.documentElement.dataset.genesisTheme=next;
  try{window.localStorage.setItem(KEY,next);}catch{}
  setTheme(next);
 }
 return <button type="button" className="genesis-theme-toggle" onClick={toggle} aria-label={`Switch to ${theme==='light'?'dark':'light'} theme`} title={`Switch to ${theme==='light'?'dark':'light'} theme`} aria-pressed={theme==='dark'}><span aria-hidden="true">{theme==='light'?'☾':'☀'}</span><span>{theme==='light'?'Dark mode':'Light mode'}</span></button>;
}
