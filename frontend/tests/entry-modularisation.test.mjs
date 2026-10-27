import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("Entry and Analysis share one workspace-driven dashboard", () => {
  const entry = read("../src/app/entry/page.tsx");
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  assert.match(entry, /<Dashboard mode="entry"\s*\/>/);
  assert.match(dashboard, /writeWorkspace\(workspace\)/);
  assert.match(dashboard, /isEntry \? \(/);
});

test("Initial project data lives only in Entry and advisor context is a separate editor", () => {
  const dashboard = read("../src/components/dashboard/dashboard.tsx");
  const context = read("../src/components/dashboard/project-context-editor.tsx");
  const advisor = read("../src/components/dashboard/universal-advisor.tsx");
  assert.match(dashboard, /<ProjectContextEditor/);
  assert.match(dashboard, /Bring your process data/);
  assert.match(dashboard, /Make the assumptions yours/);
  assert.match(context, /Process description/);
  assert.match(context, /Project region/);
  assert.doesNotMatch(advisor, /aria-label="Process description"/);
});

test("Entry navigation exposes import, while analysis links remain working", () => {
  const sidebar = read("../src/components/dashboard/workspace-sidebar.tsx");
  assert.match(sidebar, /href="\/entry#streams"/);
  assert.match(sidebar, /href=\{dashboardHref\("#equipment"\)\}/);
  assert.doesNotMatch(sidebar, /dashboardHref\("#streams"\)/);
});
