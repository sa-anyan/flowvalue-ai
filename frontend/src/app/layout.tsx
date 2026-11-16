import type { Metadata } from 'next';
import './globals.css';
import './genesis.css';
export const metadata: Metadata = {title: 'FlowValue AI · Engineering assessment', description: 'Traceable preliminary process economics'};
export default function Layout({children}: {children: React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
