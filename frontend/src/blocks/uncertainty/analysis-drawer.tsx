'use client';
import {useEffect,useRef,type ReactNode} from 'react';
import './analysis-drawer.css';

/** Shared inspection surface: native focus containment, Escape and backdrop close. */
export function AnalysisDrawer({open,title,onClose,children}:{open:boolean;title:string;onClose:()=>void;children:ReactNode}) {
 const dialog=useRef<HTMLDialogElement>(null),close=useRef<HTMLButtonElement>(null);
 useEffect(()=>{
  if(!open)return;
  const node=dialog.current;if(!node)return;
  const origin=document.activeElement instanceof HTMLElement?document.activeElement:null;
  const overflow=document.body.style.overflow;
  node.showModal();document.body.style.overflow='hidden';close.current?.focus();
  return()=>{node.close();document.body.style.overflow=overflow;if(origin?.isConnected)origin.focus({preventScroll:true});};
 },[open]);
 return <dialog ref={dialog} className="mc-analysis-drawer" aria-label={title} onCancel={event=>{event.preventDefault();onClose();}} onClick={event=>{if(event.target===event.currentTarget)onClose();}}>
  <div className="mc-analysis-drawer-layout"><header className="mc-analysis-drawer-head"><div><small>MONTE CARLO · INSPECTION</small><h2>{title}</h2></div><button ref={close} type="button" className="secondary" aria-label="Close analysis drawer" onClick={onClose}>Close ×</button></header>
  <div className="mc-analysis-drawer-body">{open?children:null}</div></div>
 </dialog>;
}
