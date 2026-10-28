import type { ImportMethodId } from "./import-methods";

/**
 * Reference examples are fixtures or guides, not machine-learning training data.
 * A sample is NOT evidence that all files from a simulator are compatible.
 * Only URLs under /examples are packaged by FlowValue.
 */
export type ImportSample = {
  name: string;
  downloadUrl: string;
  previewTitle: string;
  columns: readonly string[];
  previewRows: readonly (readonly string[])[];
  notes: string;
  kind: "tested-fixture" | "reference-example" | "generic-example";
};

const excelExample: ImportSample = {
  name: "Excel mass balance example (.xlsx)",
  downloadUrl: "/examples/excel-balance-sample.xlsx",
  previewTitle: "Rows in the generic Excel workbook",
  columns: ["Stream ID", "Mass flow [kg/h]", "Temperature [C]", "Pressure [bara]", "Phase"],
  previewRows: [
    ["F1", "100", "0", "1.2", "liquid"],
    ["P1", "100", "30", "2", "liquid"],
  ],
  notes: "Synthetic generic workbook used in FlowValue's automated Excel parser tests. It does not establish balance closure.",
  kind: "tested-fixture",
};

const genericSimulatorExample: ImportSample = {
  ...excelExample,
  name: "Generic Excel balance example (.xlsx)",
  notes: "Generic FlowValue test workbook only — NOT an export from the selected simulator, and NOT proof of compatibility with its vendor-specific Excel layout. A dedicated sample is not yet available.",
  kind: "generic-example",
};

const examples: Partial<Record<ImportMethodId, ImportSample>> = {
  excel: excelExample,
  csv: {
    name: "Canonical stream-table example (.csv)",
    downloadUrl: "/examples/sample-streams.csv",
    previewTitle: "Canonical CSV columns",
    columns: ["stream_id", "mass_flow_kg_h", "temperature_c", "pressure_bar_abs", "phase"],
    previewRows: [
      ["S1", "1200", "25", "1.2", "liquid"],
      ["S2", "1200", "30", "5", "liquid"],
      ["S3", "1200", "80", "4.8", "liquid"],
    ],
    notes: "Illustrative canonical stream records. The parser validates fields; the sample does not demonstrate a full engineering balance.",
    kind: "reference-example",
  },
  json: {
    name: "Canonical stream-table example (.json)",
    downloadUrl: "/examples/sample-streams.json",
    previewTitle: "Fields in the JSON streams array",
    columns: ["stream_id", "mass_flow_kg_h", "temperature_c", "pressure_bar_abs", "phase"],
    previewRows: [["S1", "1200", "25", "1.2", "liquid"], ["S2", "1200", "30", "5", "liquid"]],
    notes: 'The document has a top-level "streams" array. It contains synthetic canonical stream records.',
    kind: "reference-example",
  },
  "aspen-plus": genericSimulatorExample,
  "aspen-hysys": {
    ...genericSimulatorExample,
    notes: "This is a generic Excel fixture, NOT an Aspen HYSYS export. FlowValue has an independently tested HYSYS-style matrix adapter, but its example workbook has not been published. Do not interpret this fixture as an Aspen-validated example.",
  },
  "dwsim-excel": genericSimulatorExample,
  "dwsim-native": {
    name: "Synthetic DWSIM result file (.dwxml)",
    downloadUrl: "/examples/dwsim-native-sample.dwxml",
    previewTitle: "What the native sample contains",
    columns: ["Record", "Example", "Meaning"],
    previewRows: [
      ["MaterialStream", "Imported stream tags", "Saved temperature, pressure and mass flow"],
      ["SimulationObject", "Unit operations", "Native equipment and mapping candidates"],
    ],
    notes: "Synthetic fixture from FlowValue's DWSIM parser tests. No DWSIM model is executed or solved.",
    kind: "tested-fixture",
  },
  unisim: genericSimulatorExample,
  chemcad: genericSimulatorExample,
  "pro-ii": genericSimulatorExample,
  gproms: genericSimulatorExample,
  superpro: genericSimulatorExample,
  biosteam: {
    name: "BioSTEAM result snapshot (.json)",
    downloadUrl: "/examples/water-heating-biosteam.json",
    previewTitle: "Snapshot structure",
    columns: ["Property", "Example", "Notes"],
    previewRows: [
      ["schema_version", "flowvalue-biosteam-v1", "Trusted snapshot schema"],
      ["streams", "feed, pressurized, product", "Material streams"],
      ["equipment", "P101, E101", "Saved cost results"],
    ],
    notes: "FlowValue water-heating demonstration snapshot. Uploaded Python source is not executed.",
    kind: "reference-example",
  },
  "other-excel": genericSimulatorExample,
};

export function getImportSample(id: ImportMethodId): ImportSample | null {
  return examples[id] ?? null;
}
