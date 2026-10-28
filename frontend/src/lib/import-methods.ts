export const importMethods = [
  {
    id: "excel",
    label: "Excel workbook (.xlsx, .xls, .xlsm)",
    group: "Spreadsheets & tables",
    mode: "excel",
    help: "Upload a mass and energy balance workbook (.xlsx or .xls). Macro-enabled .xlsm workbooks support tagged equipment extraction from stream descriptions; macros are never executed.",
  },
  {
    id: "csv",
    label: "CSV stream table",
    group: "Spreadsheets & tables",
    mode: "simulation",
    help: "Upload the CSV stream table here. CSV currently requires the canonical stream_id, mass_flow_kg_h, temperature_c, pressure_bar_abs and phase columns.",
  },
  {
    id: "json",
    label: "JSON stream table",
    group: "Spreadsheets & tables",
    mode: "simulation",
    help: "Upload JSON here for canonical stream tables or supported FlowValue project files.",
  },
  {
    id: "aspen-plus",
    label: "Aspen Plus",
    group: "Process simulators",
    mode: "excel",
    help: "Export material/energy stream tables to Excel, then upload the .xlsx or .xls report. Native Aspen project, backup and archive files are not parsed.",
  },
  {
    id: "aspen-hysys",
    label: "Aspen HYSYS",
    group: "Process simulators",
    mode: "excel",
    help: "Export the material/energy balance or stream report to Excel (.xlsx or .xls). Native HYSYS simulation files are not parsed.",
  },
  {
    id: "dwsim-excel",
    label: "DWSIM · Excel report",
    group: "Process simulators",
    mode: "excel",
    help: "Upload an exported .xlsx or .xls material/energy balance. Table support depends on the exported cells and units.",
  },
  {
    id: "dwsim-native",
    label: "DWSIM · native .dwxml",
    group: "Process simulators",
    mode: "simulation",
    help: "Upload native DWSIM .dwxml files. Mapping gaps remain explicit; this is separate from Excel balance validation.",
  },
  {
    id: "unisim",
    label: "Honeywell UniSim Design",
    group: "Process simulators",
    mode: "excel",
    help: "Export stream and energy tables to Excel (.xlsx or .xls). Native UniSim files are not parsed.",
  },
  {
    id: "chemcad",
    label: "CHEMCAD",
    group: "Process simulators",
    mode: "excel",
    help: "Upload an Excel export of the engineering tables (.xlsx or .xls). Native CHEMCAD files are not parsed.",
  },
  {
    id: "pro-ii",
    label: "PRO/II",
    group: "Process simulators",
    mode: "excel",
    help: "Export the material/energy report tables to .xlsx or .xls. Native simulation files are not parsed.",
  },
  {
    id: "gproms",
    label: "gPROMS",
    group: "Process simulators",
    mode: "excel",
    help: "Upload exported engineering tables in .xlsx or .xls. Native models and source code are not executed.",
  },
  {
    id: "superpro",
    label: "SuperPro Designer",
    group: "Process simulators",
    mode: "excel",
    help: "Upload an Excel material/energy report (.xlsx or .xls). Batch/time-dependent balance closure may remain unresolved; native files are not parsed.",
  },
  {
    id: "biosteam",
    label: "BioSTEAM snapshot",
    group: "Process simulators",
    mode: "simulation",
    help: "Upload trusted flowvalue-biosteam-v1 JSON snapshots. Uploaded Python code is never executed.",
  },
  {
    id: "other-excel",
    label: "Other software / Python / MATLAB export",
    group: "Other inputs",
    mode: "excel",
    help: "Export the engineering tables as .xlsx or .xls. Unknown layouts, units and missing information remain unresolved; scripts and arbitrary native files are not executed.",
  },
  {
    id: "documents",
    label: "PDF / Word engineering report",
    group: "Other inputs",
    mode: "unavailable",
    help: "Document parsing is not supported yet. Export or transcribe the material/energy tables into Excel, then select Excel workbook. No automatic OCR or document reconstruction is claimed.",
  },
  {
    id: "images",
    label: "Scanned table / image / PFD",
    group: "Other inputs",
    mode: "unavailable",
    help: "Image and drawing extraction is not supported yet. Prepare a tabular Excel balance with units. A drawing or image alone does not establish numerical balance data.",
  },
  {
    id: "manual",
    label: "Manual / natural-language description",
    group: "Other inputs",
    mode: "unavailable",
    help: "Use the process-description box alongside an uploaded balance. A description alone cannot supply verified stream values or balance closure.",
  },
] as const;
export type ImportMethodId = (typeof importMethods)[number]["id"];
export function getImportMethod(id: string) {
  return importMethods.find((method) => method.id === id) ?? importMethods[0];
}
export function acceptsBalanceWorkbook(methodId: string, filename: string) {
  return (
    getImportMethod(methodId).mode === "excel" &&
    /\.(xlsx|xls|xlsm)$/i.test(filename)
  );
}
export function readImportMethod(): ImportMethodId {
  try {
    return getImportMethod(
      sessionStorage.getItem("flowvalue-import-method") || "excel",
    ).id;
  } catch {
    return "excel";
  }
}
