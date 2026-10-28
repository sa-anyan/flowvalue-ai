export const workspaceRoutes = {
  "/entry": "entry",
  "/simulation-data": "import",
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
  if (pathname.startsWith("/capex/")) return "capex";
  return (
    workspaceRoutes[pathname as keyof typeof workspaceRoutes] || "analysis"
  );
}
export const workspaceTitles: Record<WorkspaceView, string> = {
  entry: "Project entry",
  import: "Simulation data",
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
  if (pathname === "/entry" && hash === "#streams")
    return "/simulation-data#streams";
  if (pathname !== "/dashboard") return null;
  const destinations: Record<string, string> = {
    "#equipment": "/capex/equipment",
    "#engineering-analyst": "/capex/equipment",
    "#playground": "/sensitivity",
    "#risk": "/scenario",
    "#streams": "/simulation-data",
  };
  return destinations[hash] ? destinations[hash] + hash : null;
}
