"use client";

import { useSyncExternalStore } from "react";
import { ChevronRight } from "lucide-react";
import { WorkspaceSidebar } from "./workspace-sidebar";
import { readWorkspace } from "@/lib/workspace";

type Section = "capex" | "opex" | "revenue";

// Route-only placeholder; existing project data and calculations are untouched.
const subscribe = () => () => {};
const getName = () =>
  readWorkspace()?.project.advisor_context?.name ?? "Untitled process";
const getServerName = () => "Untitled process";

export function EmptyAnalysisPage({ section }: { section: Section }) {
  const name = useSyncExternalStore(subscribe, getName, getServerName);
  const title = section === "capex" ? "Capex" : section === "opex" ? "Opex" : "Revenue";

  return (
    <div className="app-shell">
      <WorkspaceSidebar name={name} active={section} />
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>{title}</span>
          </div>
        </header>
        <main className="dashboard-main">
          <section className="page-heading">
            <div>
              <div className="eyebrow"><span /> ANALYSIS</div>
              <h1>{title}</h1>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
