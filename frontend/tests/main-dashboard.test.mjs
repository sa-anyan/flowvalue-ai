import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8");

test("Main dashboard is a dedicated route and is first under Analysis", () => {
  const route = read("../src/app/(workspace)/main-dashboard/page.tsx");
  const nav = read("../src/components/dashboard/workspace-sidebar.tsx");
  assert.doesNotMatch(route, /EmptyAnalysisPage/);
  const processSection = nav.indexOf('PROCESS VISUALISATION');
  const analysisSection = nav.indexOf('>ANALYST WORKSPACE</div>');
  assert.ok(processSection >= 0 && processSection < analysisSection);
  assert.ok(nav.indexOf('href="/process-flow"') > processSection);
  assert.ok(nav.indexOf('href="/process-flow"') < analysisSection);
  assert.ok(nav.indexOf('href="/main-dashboard"') > analysisSection);
  assert.match(nav, /href="\/scenario"/);
});

test("Main dashboard owns six headline metrics and three charts", () => {
  const main = read("../src/components/dashboard/main-dashboard.tsx");
  const analysis = read("../src/components/dashboard/dashboard.tsx");
  for (const key of ["capex", "opex", "npv", "irr", "lcop", "payback"]) {
    assert.match(main, new RegExp(`data-testid="${key}"`));
  }
  for (const chart of ["CashFlowChart", "RiskChart", "CapexChart"]) {
    assert.match(main, new RegExp(`<${chart} data={data}`));

  }
  assert.match(analysis, /<MainDashboard/);
  assert.match(analysis, /id="equipment"/);
  assert.match(analysis, /id="playground"/);
});

test("Entry continues to Main dashboard instead of the long analysis view", () => {
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  assert.match(dashboard, /href="\/main-dashboard"[\s\S]*?className="entry-analysis-link"/);
});

test("Process view uses shared sidebar with its own active state", () => {
  const flow = read("../src/components/process-flow/process-flow.tsx");
  const nav = read("../src/components/dashboard/workspace-sidebar.tsx");
  assert.match(flow, /<WorkspaceSidebar[\s\S]*?active="process"/);
  assert.match(nav, /active === "process" \? "nav-selected"/);
  assert.equal((nav.match(/href="\/process-flow"/g) || []).length, 1);
});
