import { test } from "node:test";
import assert from "node:assert/strict";
import { workspaceView, legacyWorkspaceHref } from "../src/lib/workspace-navigation.ts";

test("existing public workspace URLs select their own content", () => {
  for (const [path, view] of Object.entries({"/entry":"entry","/main-dashboard":"main","/dashboard":"analysis","/capex":"capex","/opex":"opex","/revenue":"revenue","/scenario":"scenario","/sensitivity":"sensitivity"})) assert.equal(workspaceView(path), view);
});

test("saved analysis section links resolve to the new topic pages without redirect loops", () => {
  assert.equal(legacyWorkspaceHref("/dashboard", "#equipment"), "/capex#equipment");
  assert.equal(legacyWorkspaceHref("/dashboard", "#engineering-analyst"), "/capex#engineering-analyst");
  assert.equal(legacyWorkspaceHref("/dashboard", "#playground"), "/sensitivity#playground");
  assert.equal(legacyWorkspaceHref("/dashboard", "#risk"), "/scenario#risk");
  assert.equal(legacyWorkspaceHref("/dashboard", "#streams"), "/entry#streams");
  for (const hash of ["", "#overview", "#study", "#https://example.com", "#equipment&unexpected"]) assert.equal(legacyWorkspaceHref("/dashboard",hash),null);
  assert.equal(legacyWorkspaceHref("/capex", "#equipment"),null);
});
