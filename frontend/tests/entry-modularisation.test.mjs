import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("Entry and Analysis share one workspace-driven dashboard", () => {
  const entry = read("../src/app/(workspace)/entry/page.tsx");
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  assert.doesNotMatch(entry, /EmptyAnalysisPage/);
  assert.match(dashboard, /writeWorkspace\(workspace\)/);
  assert.match(dashboard, /isEntry \? \(/);
});

test("Entry owns the unified file selector without the removed secondary controls", () => {
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  assert.match(dashboard, /onSimulationUpload=\{upload\}/);
  assert.match(dashboard, /<BalanceImport/);
  assert.doesNotMatch(
    dashboard,
    /Bring your process data|Make the assumptions yours|<ProjectContextEditor/,
  );
});

test("Entry navigation exposes import, while analysis links remain working", () => {
  const sidebar = read("../src/components/dashboard/workspace-sidebar.tsx");
  assert.doesNotMatch(sidebar, /href="\/simulation-data"/);
  assert.match(sidebar, /href="\/entry"/);
  assert.match(sidebar, /href="\/capex"/);
  assert.doesNotMatch(sidebar, /dashboardHref\("#streams"\)/);
});
