import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const read = (path) => readFileSync(new URL(path, import.meta.url),"utf8");

test("the routed workspace keeps one shared project owner rather than separate dashboard instances", () => {
  const layout=read("../src/app/(workspace)/layout.tsx");
  assert.equal((layout.match(/<Dashboard\s*\/>/g)||[]).length,1);
  for(const route of ["dashboard","entry","main-dashboard","capex","opex","revenue","scenario","sensitivity"]) assert.doesNotMatch(read(`../src/app/(workspace)/${route}/page.tsx`),/<Dashboard|<EmptyAnalysisPage/);
});

test("shared navigation exposes the analyst pages and the existing Playground pages", () => {
  const nav=read("../src/components/dashboard/workspace-sidebar.tsx");
  assert.match(nav,/ANALYST WORKSPACE/);
  assert.match(nav,/aria-label="Playground"/);
  for(const path of ["/entry","/main-dashboard","/capex","/opex","/revenue","/dashboard","/scenario","/sensitivity","/process-flow"]) assert.match(nav,new RegExp(`href="${path}"`));
  assert.doesNotMatch(nav,/Analysis tools|dashboardHref/);
});
