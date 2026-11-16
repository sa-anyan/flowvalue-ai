'use client';

import {useEffect, useState} from 'react';

/** Server HTML is intentionally inert until React has attached its handlers. */
export function StartupShell({children}: {children: React.ReactNode}) {
 const [ready, setReady] = useState(false);
 useEffect(() => {
  window.dispatchEvent(new Event('flowvalue-started'));
  setReady(true);
 }, []);
 return <>
  {!ready && <div className="fv-startup" role="status" aria-live="polite">
   <strong>Opening FlowValue…</strong>
   <p className="fv-startup-normal">Preparing your workspace and controls.</p>
   <p className="fv-startup-slow">Startup is taking longer than expected. Reload this page to try again. Your saved projects are unchanged.</p>
   <a href="">Reload page</a>
   <noscript><p>JavaScript must be enabled to use FlowValue.</p></noscript>
  </div>}
  <div inert={!ready || undefined} aria-hidden={!ready || undefined} style={!ready ? {visibility:'hidden'} : undefined}>{children}</div>
 </>;
}
