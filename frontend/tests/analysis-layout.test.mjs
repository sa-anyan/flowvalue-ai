import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("Analysis tools have two semantic working columns", () => {
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  const analysis = dashboard.slice(dashboard.indexOf('          <div className="analysis-tools-grid">'));
  assert.match(analysis, /aria-label="Model and costing tools"/);
  assert.match(analysis, /aria-label="Engineering and intelligence tools"/);
  assert.ok(analysis.indexOf('id="playground"') < analysis.indexOf('aria-label="Engineering and intelligence tools"'));
  assert.ok(analysis.indexOf('id="equipment"') < analysis.indexOf('aria-label="Engineering and intelligence tools"'));
  assert.ok(analysis.indexOf("<StudyWorkspace") < analysis.indexOf('aria-label="Engineering and intelligence tools"'));
  assert.ok(analysis.indexOf("<AIConnection") > analysis.indexOf('aria-label="Engineering and intelligence tools"'));
  assert.ok(analysis.indexOf("<UniversalAdvisor") > analysis.indexOf('aria-label="Engineering and intelligence tools"'));
  assert.ok(analysis.indexOf("<EngineeringAnalyst") > analysis.indexOf('aria-label="Engineering and intelligence tools"'));
  assert.ok(analysis.indexOf("<EngineeringTools") > analysis.indexOf('aria-label="Engineering and intelligence tools"'));
});

test("Analysis layout keeps all features and stacks on narrow screens", () => {
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  const css = read("../src/app/globals.css");
  assert.match(dashboard, /<div className="analysis-tools-grid">/);
  assert.equal((dashboard.match(/className="analysis-tools-column"/g) || []).length, 2);
  assert.match(css, /\.analysis-tools-grid\s*\{\s*display:\s*grid;\s*grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/);
  assert.match(css, /@media \(max-width: 1230px\)[\s\S]*?\.analysis-tools-grid\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\)/);
  assert.match(css, /\.analysis-tools-column \.equipment-panel \.table-scroll\s*\{\s*overflow-x:\s*auto/);
  for (const section of ["AIConnection","UniversalAdvisor","StudyWorkspace","EngineeringAnalyst","EngineeringTools"]) {
    assert.equal((dashboard.match(new RegExp("<" + section + "\\b", "g")) || []).length, 1);
  }
});
