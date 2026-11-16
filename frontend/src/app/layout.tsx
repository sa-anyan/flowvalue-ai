import type { Metadata } from 'next';
import './globals.css';
import {StartupShell} from '@/components/startup-shell';
import {startupRecoveryScript} from '@/lib/startup-recovery';
export const metadata: Metadata = {title: 'FlowValue AI · Engineering assessment', description: 'Traceable preliminary process economics'};
export default function Layout({children}: {children: React.ReactNode}) {
  return <html lang="en" suppressHydrationWarning><head>
    {/* Native bootstrap must work even when application chunks never initialize. */}
    <script dangerouslySetInnerHTML={{__html: startupRecoveryScript}} />
  </head><body><StartupShell>{children}</StartupShell></body></html>;
}
