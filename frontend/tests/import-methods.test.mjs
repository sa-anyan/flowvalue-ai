import { test } from "node:test";
import assert from "node:assert/strict";
import {
  importMethods,
  getImportMethod,
  acceptsBalanceWorkbook,
} from "../src/lib/import-methods.ts";
test("simulator origins accept exported workbooks while rejecting native project files", () => {
  for (const method of importMethods.filter((m) => m.mode === "excel")) {
    assert.equal(acceptsBalanceWorkbook(method.id, "balance.XLSX"), true);
    assert.equal(acceptsBalanceWorkbook(method.id, "balance.xls"), true);
    for (const file of [
      "case.hsc",
      "case.bkp",
      "case.apw",
      "case.dwxml",
      "script.py",
      "balance.pdf",
    ])
      assert.equal(acceptsBalanceWorkbook(method.id, file), false);
  }
});
test("non-Excel paths stay explicit and never route arbitrary data through Excel parsing", () => {
  for (const method of importMethods.filter((m) => m.mode !== "excel"))
    assert.equal(acceptsBalanceWorkbook(method.id, "balance.xlsx"), false);
  assert.equal(getImportMethod("aspen-plus").mode, "excel");
  assert.equal(getImportMethod("dwsim-native").mode, "simulation");
  assert.equal(getImportMethod("documents").mode, "unavailable");
  assert.equal(getImportMethod("unknown").id, "excel");
  assert.equal(
    new Set(importMethods.map((m) => m.id)).size,
    importMethods.length,
  );
});
