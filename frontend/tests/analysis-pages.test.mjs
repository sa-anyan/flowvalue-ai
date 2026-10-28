import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("Capex, Opex and Revenue appear in order after Main dashboard under Analysis", () => {
  const nav = read("../src/components/dashboard/workspace-sidebar.tsx");
  const main = nav.indexOf('href="/main-dashboard"');
  const capex = nav.indexOf('href="/capex"');
  const opex = nav.indexOf('href="/opex"');
  const revenue = nav.indexOf('href="/revenue"');
  const tools = nav.indexOf('href={dashboardHref("#overview")}');
  assert.ok(main >= 0 && main < capex && capex < opex && opex < revenue && revenue < tools);
  for (const section of ["capex", "opex", "revenue"]) {
    assert.match(nav, new RegExp('active === "' + section + '" \\? "nav-selected"'));
  }
});

test("All three empty routes use the shared sidebar and preserve analysis modules", () => {
  const capex = read("../src/app/capex/page.tsx");
  const opex = read("../src/app/opex/page.tsx");
  const revenue = read("../src/app/revenue/page.tsx");
  const placeholder = read("../src/components/dashboard/empty-analysis-page.tsx");
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  assert.match(capex, /<EmptyAnalysisPage section="capex"\s*\/>/);
  assert.match(opex, /<EmptyAnalysisPage section="opex"\s*\/>/);
  assert.match(revenue, /<EmptyAnalysisPage section="revenue"\s*\/>/);
  assert.match(placeholder, /<WorkspaceSidebar name={name} active={section}/);
  assert.match(placeholder, /readWorkspace\(\)/);
  assert.match(dashboard, /<EngineeringTools/);
  assert.match(dashboard, /id="equipment"/);
  assert.match(dashboard, /id="playground"/);
});
