import { Suspense } from "react";
import Dashboard from "@/components/dashboard/dashboard";
// Keep one project/scenario instance alive across the workspace's routed pages.
export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense
      fallback={
        <main className="auth-screen">
          <p>Loading workspace…</p>
        </main>
      }
    >
      <Dashboard />
      {children}
    </Suspense>
  );
}
