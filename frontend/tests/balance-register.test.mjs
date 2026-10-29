import { test } from "node:test";
import assert from "node:assert/strict";
import { equipmentPropertyGroups, equipmentRegister } from "../src/lib/balance-register.ts";
import { isBalanceAttachment } from "../src/lib/workspace.ts";
import { emptyDescription } from "../src/lib/balance.ts";

const evidence = (id, sheet, property, label, number) => ({ id, workbook: "sample.xlsx", sheet, cell: "B2", header_cells: [], property, label, original_value: number, normalized_value: number, original_unit: "kg/h", normalized_unit: "kg/h", status: "inferred", component: "Na+", formula: null, cached: false, note: "" });
const entity = (key, kind, sheet, id, values, stream_keys) => ({ key, kind, identifier: id, case: "", table: "t1", id_evidence: evidence(`${key}:id`,sheet,"identifier","ID",id), values, ...(stream_keys === undefined ? {} : {stream_keys}), status: "inferred" });
const report = (entities) => ({ schema_version: "flowvalue-balance-v1", parser_version: "workbook-pipeline-3.0", filename: "sample.xlsx", entities, tables: [], issues: [], checks: [], sheets: [], declarations: [], limitations: [] });

test("scoped stream references supply properties without equipment value copies", () => {
  const payload=report([
    entity("sA","material","Plant A","1",[evidence("a","Plant A","component_mass_flow","Na+",100)]),
    entity("sB","material","Plant B","1",[evidence("b","Plant B","component_mass_flow","Na+",200)]),
    entity("eA","equipment","Plant A","P-001",[],["sA"]),
    entity("eB","equipment","Plant B","P-001",[],["sB"]),
    entity("waste","material","Plant A","14",[evidence("w","Plant A","mass_flow","Flow",20)]),
  ]);
  const groups=equipmentPropertyGroups(payload);
  assert.equal(groups.length,3);
  assert.equal(groups[0].rows[0].evidence.original_value,100);
  assert.equal(groups[1].rows[0].evidence.original_value,200);
  assert.equal(groups[2].tag,"Unassigned · Stream 14");
  assert.equal(equipmentRegister(payload)[0].streams[0].key,"sA");
  assert.equal(isBalanceAttachment({ report:payload, description:emptyDescription }),true);
});

test("old saved reports with copied evidence remain readable", () => {
  const old=report([entity("p","equipment","Old","P-001",[evidence("old","Old","mass_flow","Stream 1 | Flow",99)])]);
  assert.equal(equipmentPropertyGroups(old)[0].rows[0].evidence.original_value,99);
});
