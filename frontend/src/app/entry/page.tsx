"use client";

import { useEffect, useState } from "react";
import { ChevronRight } from "lucide-react";
import { WorkspaceSidebar } from "@/components/dashboard/workspace-sidebar";
import { readWorkspace } from "@/lib/workspace";

export default function EntryPage() {
  const [name, setName] = useState("Untitled process");

  useEffect(() => {
    const savedName = readWorkspace()?.project.advisor_context?.name;
    if (savedName) setName(savedName);
  }, []);

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
