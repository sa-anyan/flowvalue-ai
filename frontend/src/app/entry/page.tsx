"use client";

import { useSyncExternalStore } from "react";
import { ChevronRight } from "lucide-react";
import { WorkspaceSidebar } from "@/components/dashboard/workspace-sidebar";
import { readWorkspace } from "@/lib/workspace";

function subscribeToWorkspace() {
  // This blank page only reads the current workspace when it is opened.
  return () => {};
}

function getWorkspaceName() {
  return readWorkspace()?.project.advisor_context?.name ?? "Untitled process";
}

export default function EntryPage() {
  const name = useSyncExternalStore(
    subscribeToWorkspace,
    getWorkspaceName,
    () => "Untitled process",
  );

  return (
    <div className="app-shell">
      <WorkspaceSidebar name={name} active="entry" />
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>Entry</span>
          </div>
        </header>
        <main className="dashboard-main">
          <h1>Entry</h1>
        </main>
      </div>
    </div>
  );
}
