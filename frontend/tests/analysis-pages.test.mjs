import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { workspaceView, legacyWorkspaceHref } from "../src/lib/workspace-navigation.ts";

test("existing public workspace URLs select their own content", () => {
  for (const [path, view] of Object.entries({"/entry":"entry","/main-dashboard":"main","/dashboard":"analysis","/capex":"capex","/opex":"opex","/revenue":"revenue","/scenario":"scenario","/sensitivity":"sensitivity"})) assert.equal(workspaceView(path), view);
});

test("saved analysis section links resolve to the new topic pages without redirect loops", () => {
  assert.equal(legacyWorkspaceHref("/dashboard", "#equipment"), "/capex/equipment#equipment");
  assert.equal(legacyWorkspaceHref("/dashboard", "#engineering-analyst"), "/capex/equipment#engineering-analyst");
  assert.equal(legacyWorkspaceHref("/dashboard", "#playground"), "/sensitivity#playground");
  assert.equal(legacyWorkspaceHref("/dashboard", "#risk"), "/scenario#risk");
  assert.equal(legacyWorkspaceHref("/dashboard", "#streams"), "/entry#streams");
  for (const hash of ["", "#overview", "#study", "#https://example.com", "#equipment&unexpected"]) assert.equal(legacyWorkspaceHref("/dashboard",hash),null);
  assert.equal(legacyWorkspaceHref("/capex", "#equipment"),null);
});


test("CAPEX parent expands into seven routes, defaulting to Summary", () => {
  const nav = readFileSync(new URL("../src/components/dashboard/workspace-sidebar.tsx", import.meta.url), "utf8");
  const dash = readFileSync(new URL("../src/components/dashboard/dashboard.tsx", import.meta.url), "utf8");
  const detail = readFileSync(new URL("../src/app/(workspace)/capex/[section]/page.tsx", import.meta.url), "utf8");
  const capex = readFileSync(new URL("../src/components/dashboard/capex-workspace.tsx", import.meta.url), "utf8");
  for (const page of ["summary", "equipment", "direct-costs", "indirect-costs", "working-capital", "assumptions", "validation"]) {
    assert.match(nav, new RegExp('"' + page + '"'));
    assert.match(detail, new RegExp('"' + page + '"'));
  }
  assert.match(nav, /active === "capex" &&/);
  assert.match(dash, /<CapexSummary/);
  assert.match(dash, /<CapexCostRegister/);
  assert.match(dash, /<CapexValidation/);
  assert.match(capex, /Equipment capital allocation/);
  assert.match(capex, /Capital cost build-up/);
});
