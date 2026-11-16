import type { Metadata } from 'next';
import {GenesisThemeToggle} from '@/components/genesis-theme-toggle';
import './globals.css';
import './genesis.css';
export const metadata: Metadata = {title: 'FlowValue AI · Engineering assessment', description: 'Traceable preliminary process economics'};
const themeBootstrap = "try{const theme=localStorage.getItem('flowvalue-genesis-theme')??localStorage.getItem('flowvalue-theme');document.documentElement.dataset.genesisTheme=theme==='dark'?'dark':'light'}catch{}";
export default function Layout({children}: {children: React.ReactNode}) {
  return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:themeBootstrap}} /></head><body>{children}<div className="genesis-theme-dock"><GenesisThemeToggle/></div></body></html>;
}
