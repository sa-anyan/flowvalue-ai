import type { Metadata } from 'next';
import {GenesisThemeToggle} from '@/components/genesis-theme-toggle';
import './globals.css';
export const metadata: Metadata = {title: 'FlowValue AI · Engineering assessment', description: 'Traceable preliminary process economics'};
export default function Layout({children}: {children: React.ReactNode}) {
  return <html lang="en" suppressHydrationWarning><body>{children}<div className="genesis-theme-dock"><GenesisThemeToggle/></div></body></html>;
}
