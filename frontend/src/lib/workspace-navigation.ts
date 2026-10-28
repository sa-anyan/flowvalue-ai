export const workspaceRoutes = {
  "/entry": "entry",
  "/main-dashboard": "main",
  "/dashboard": "analysis",
  "/capex": "capex",
  "/opex": "opex",
  "/revenue": "revenue",
  "/scenario": "scenario",
  "/sensitivity": "sensitivity",
} as const;
export type WorkspaceView =
  (typeof workspaceRoutes)[keyof typeof workspaceRoutes];
export function workspaceView(pathname: string): WorkspaceView {
  return (
    workspaceRoutes[pathname as keyof typeof workspaceRoutes] || "analysis"
  );
}
export const workspaceTitles: Record<WorkspaceView, string> = {
  entry: "Project entry",
  main: "Main dashboard",
  analysis: "Analyst workspace",
  capex: "CAPEX",
  opex: "OPEX",
  revenue: "Revenue",
  scenario: "Scenario analysis",
  sensitivity: "Sensitivity analysis",
};

// Keep saved dashboard links useful after moving the old analysis sections.
export function legacyWorkspaceHref(
  pathname: string,
  hash: string,
): string | null {
  if (pathname !== "/dashboard") return null;
  const destinations: Record<string, string> = {
    "#equipment": "/capex",
    "#engineering-analyst": "/capex",
    "#playground": "/sensitivity",
    "#risk": "/scenario",
    "#streams": "/entry",
  };
  return destinations[hash] ? destinations[hash] + hash : null;
}
