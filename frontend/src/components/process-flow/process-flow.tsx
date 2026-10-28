"use client";
import { LegacyProjectWorkspace } from "@/components/dashboard/legacy-project-workspace";
import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Position,
  useNodesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { FlowNode, FlowEdge } from "./scene";
import {
  readWorkspace,
  writeWorkspace,
  scenarioScopeNotes,
  type Workspace,
} from "@/lib/workspace";
import { apiFetch } from "@/lib/client-api";
import {
  apiError,
  fieldLabels,
  kindLabels,
  usd,
  type EquipmentSpec,
  type Assessment,
} from "@/lib/assessment";
import { EngineeringAnalyst } from "@/components/dashboard/engineering-analyst";
import { useAIStatus } from "@/components/dashboard/ai-connection";
import { Button } from "@/components/ui/button";
import { WorkspaceSidebar } from "@/components/dashboard/workspace-sidebar";
const Scene = dynamic(() => import("./scene"), {
  ssr: false,
  loading: () => <p>Loading 3D process view…</p>,
});
function graph(w: Workspace): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const units = new Map<string, FlowNode>();
  const imported = w.native_import?.units || [];
  imported.forEach((u, i) =>
    units.set(u.unit_id, {
      id: u.unit_id,
      label: u.unit_id,
      kind:
        w.project.costing.equipment.find((e) => e.unit_id === u.unit_id)
          ?.kind || u.native_type,
      position: { x: u.x || i * 240, y: u.y || 80 },
    }),
  );
  (w.project.study?.engineering_cases || []).forEach((u, i) => {
    if (
      !units.has(u.unit_id) &&
      !w.project.costing.equipment.some((e) => e.unit_id === u.unit_id)
    )
      units.set(u.unit_id, {
        id: u.unit_id,
        label: u.unit_id,
        kind: u.unit_kind,
        position: { x: (i % 4) * 260 + 180, y: Math.floor(i / 4) * 180 + 380 },
      });
  });
  w.project.costing.equipment.forEach((u, i) => {
    if (!units.has(u.unit_id))
      units.set(u.unit_id, {
        id: u.unit_id,
        label: u.unit_id,
        kind: u.kind,
        position: { x: (i % 4) * 260 + 180, y: Math.floor(i / 4) * 180 + 140 },
      });
  });
  const edges: FlowEdge[] = [];
  w.streams.forEach((s, i) => {
    const source = s.source_unit || `feed:${s.stream_id}`,
      target = s.destination_unit || `product:${s.stream_id}`;
    if (!units.has(source))
      units.set(source, {
        id: source,
        label: s.source_unit || `${s.stream_id} feed`,
        kind: s.source_unit ? "unpriced" : "boundary",
        position: { x: -120, y: i * 130 },
      });
    if (!units.has(target))
      units.set(target, {
        id: target,
        label: s.destination_unit || `${s.stream_id} product`,
        kind: s.destination_unit ? "unpriced" : "boundary",
        position: { x: 950, y: i * 130 },
      });
    edges.push({
      id: s.stream_id,
      source,
      target,
      label: `${s.stream_id} · ${s.mass_flow_kg_h.toLocaleString(undefined, { maximumFractionDigits: 0 })} kg/h`,
    });
  });
  // Preserve native layout where distinct. Coincident exports get a display-only grid.
  const nodes = Array.from(units.values());
  const unique = new Set(nodes.map((n) => `${n.position.x},${n.position.y}`));
  if (unique.size < nodes.length / 2)
    nodes.forEach((n, i) => {
      n.position = { x: (i % 4) * 260, y: Math.floor(i / 4) * 170 };
    });
  return { nodes, edges };
}
export default function ProcessFlow() {
  const ai = useAIStatus(0);
  const [workspace, setWorkspace] = useState<Workspace | null>(null),
    [mode, setMode] = useState<"2d" | "3d">("2d"),
    [selected, setSelected] = useState(""),
    [draft, setDraft] = useState<EquipmentSpec | null>(null),
    [message, setMessage] = useState(""),
    [result, setResult] = useState<Assessment | null>(null),
    [busy, setBusy] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  useEffect(() => {
    Promise.resolve().then(() => setWorkspace(readWorkspace()));
  }, []);
  const topology = useMemo(
    () => (workspace ? graph(workspace) : { nodes: [], edges: [] }),
    [workspace],
  );
  useEffect(() => {
    setNodes(
      topology.nodes.map((n) => ({
        id: n.id,
        position: n.position,
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: { label: n.label },
        style: {
          background: n.kind === "boundary" ? "#eff4eb" : "#e4eddf",
          borderColor: "#769979",
          borderRadius: 10,
          width: 180,
          padding: 16,
        },
      })),
    );
  }, [topology, setNodes]);
  function select(id: string) {
    if (busy) return;
    setResult(null);
    setSelected(id);
    setDraft(
      workspace?.project.costing.equipment.find((u) => u.unit_id === id) ||
        null,
    );
    setMessage("");
  }
  async function save() {
    if (!workspace || !draft) return;
    setBusy(true);
    try {
      const project = {
        ...workspace.project,
        costing: {
          ...workspace.project.costing,
          equipment: workspace.project.costing.equipment.map((e) =>
            e.unit_id === draft.unit_id ? draft : e,
          ),
        },
      };
      project.engineering_notes = scenarioScopeNotes(
        project,
        workspace.native_import,
      );
      const r = await apiFetch("/api/assessment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(project),
      });
      if (!r.ok) throw Error(await apiError(r));
      setResult(await r.json());
      const w = { ...workspace, project };
      setWorkspace(w);
      writeWorkspace(w);
      setMessage(
        "Equipment updated. Dashboard will use this scenario on return. Save a cloud revision there to keep history.",
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }
  const streams =
    workspace?.streams.filter(
      (s) =>
        s.source_unit === selected ||
        s.destination_unit === selected ||
        selected === `feed:${s.stream_id}` ||
        selected === `product:${s.stream_id}`,
    ) || [];
  const imported = workspace?.native_import?.units.find(
    (u) => u.unit_id === selected,
  );
  const viewNodes: FlowNode[] = nodes.map((n) => ({
    id: n.id,
    label: String(n.data.label),
    position: n.position,
    kind: topology.nodes.find((t) => t.id === n.id)?.kind || "unit",
  }));
  if (workspace?.project.legacy_reference)
    return (
      <div className="app-shell">
        <WorkspaceSidebar
          name={workspace.project.advisor_context?.name ?? "Legacy project"}
          active="process"
        />
        <div className="main-shell">
          <main className="dashboard-main">
            <LegacyProjectWorkspace
              project={workspace.project}
              mode="process"
            />
          </main>
        </div>
      </div>
    );
  return (
    <div className="app-shell">
      <WorkspaceSidebar
        name={workspace?.project.advisor_context?.name || "Untitled process"}
        active="process"
      />
      <div className="main-shell">
        <main className="flow-page">
          <header className="flow-header">
            <div>
              <a href="/main-dashboard">← Return to Main dashboard</a>
              <h1>Process flow workspace</h1>
              <p>
                {workspace?.project.advisor_context?.name ||
                  "Load a project in the dashboard first"}
              </p>
            </div>
            <div className="extension-actions">
              <Button
                variant={mode === "2d" ? "default" : "outline"}
                onClick={() => setMode("2d")}
              >
                2D flowsheet
              </Button>
              <Button
                variant={mode === "3d" ? "default" : "outline"}
                onClick={() => setMode("3d")}
              >
                3D process view
              </Button>
            </div>
          </header>
          {!workspace ? (
            <p>
              No active scenario in this browser tab.{" "}
              <a href="/entry">Open Entry</a> and import a simulation.
            </p>
          ) : (
            <>
              <div className="flow-layout">
                <div>
                  <div className="flow-canvas">
                    {mode === "2d" ? (
                      <ReactFlow
                        nodes={nodes}
                        edges={topology.edges as Edge[]}
                        onNodesChange={onNodesChange}
                        onNodeClick={(_e, n) => select(n.id)}
                        nodesConnectable={false}
                        edgesReconnectable={false}
                        fitView
                        fitViewOptions={{ padding: 0.25 }}
                      >
                        <Background gap={22} />
                        <Controls />
                        <MiniMap pannable zoomable />
                      </ReactFlow>
                    ) : (
                      <Scene
                        nodes={viewNodes}
                        edges={topology.edges}
                        selected={selected}
                        onSelect={select}
                      />
                    )}
                  </div>
                  <p className="flow-note">
                    Display layout only; 3D blocks are schematic, not plant
                    geometry. Drag nodes in 2D, orbit or zoom in 3D. Connections
                    come from imported stream endpoints; no connections are
                    inferred from equipment order.{" "}
                    {workspace.streams.length === 0
                      ? "This project has no stream connections; equipment is shown as independent blocks."
                      : ""}
                  </p>
                  <div className="flow-node-selector">
                    {topology.nodes.map((n) => (
                      <button key={n.id} onClick={() => select(n.id)}>
                        {n.label}
                      </button>
                    ))}
                  </div>
                </div>
                <aside className="flow-inspector">
                  <h2>{selected || "Select an operation"}</h2>
                  {draft ? (
                    <>
                      <p>{kindLabels[draft.kind]}</p>
                      {Object.entries(draft)
                        .filter(
                          ([k, v]) =>
                            typeof v === "number" &&
                            ![
                              "material_factor_override",
                              "pressure_factor_override",
                            ].includes(k),
                        )
                        .map(([k, v]) => (
                          <label key={k}>
                            {fieldLabels[k] || k.replaceAll("_", " ")}
                            <input
                              aria-label={`${draft.unit_id} ${k}`}
                              type="number"
                              step="any"
                              value={Number(v)}
                              disabled={busy}
                              onChange={(e) => {
                                setResult(null);
                                setMessage(
                                  "Unapplied changes. Apply & recalculate to update the project.",
                                );
                                setDraft({
                                  ...draft,
                                  [k]: Number(e.target.value),
                                });
                              }}
                            />
                          </label>
                        ))}
                      {draft.kind !== "quoted" && (
                        <label>
                          Material
                          <select
                            value={draft.material || "carbon_steel"}
                            disabled={busy}
                            onChange={(e) => {
                              setResult(null);
                              setMessage(
                                "Unapplied changes. Apply & recalculate to update the project.",
                              );
                              setDraft({ ...draft, material: e.target.value });
                            }}
                          >
                            <option value="carbon_steel">Carbon steel</option>
                            <option value="stainless_steel">
                              Stainless steel
                            </option>
                          </select>
                        </label>
                      )}
                      {draft.kind === "quoted" && <p>{draft.source}</p>}
                      <Button disabled={busy} onClick={save}>
                        {busy ? "Calculating…" : "Apply & recalculate"}
                      </Button>
                    </>
                  ) : (
                    <p>
                      {selected
                        ? "No complete priced sizing model for this object. Complete the mapping in the dashboard."
                        : "Click an operation in the diagram or use the buttons below it to inspect its sizing and cost parameters."}
                    </p>
                  )}
                  {imported?.warnings.map((w, i) => (
                    <p key={i}>{w}</p>
                  ))}
                  {imported?.missing_inputs.map((w, i) => (
                    <p className="engineering-warning" key={i}>
                      Missing in original simulation: {w}
                    </p>
                  ))}
                  {streams.map((s) => (
                    <p key={s.stream_id}>
                      <strong>{s.stream_id}</strong>
                      <br />
                      {s.mass_flow_kg_h.toLocaleString()} kg/h ·{" "}
                      {s.temperature_c.toFixed(1)} °C ·{" "}
                      {s.pressure_bar_abs.toFixed(2)} bar abs · {s.phase}
                    </p>
                  ))}
                  {result && (
                    <p>
                      Updated scenario CAPEX:{" "}
                      <strong>
                        {usd(result.bom.total_bare_module_cost_usd)}
                      </strong>
                      <br />
                      NPV: {usd(result.financial.npv_usd)}
                    </p>
                  )}
                  {message && <p role="status">{message}</p>}
                </aside>
              </div>
              {selected &&
                !selected.startsWith("feed:") &&
                !selected.startsWith("product:") && (
                  <EngineeringAnalyst
                    project={workspace.project}
                    native={workspace.native_import}
                    aiAvailable={!!ai.status?.can_generate}
                    selectedUnit={selected}
                    onProject={(project) => {
                      const w = { ...workspace, project };
                      setWorkspace(w);
                      writeWorkspace(w);
                      setResult(null);
                      setDraft(
                        project.costing.equipment.find(
                          (e) => e.unit_id === selected,
                        ) || null,
                      );
                    }}
                  />
                )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
