import Link from "next/link";
import {
  Activity,
  ChevronDown,
  FileInput,
  FlaskConical,
  GitBranch,
  Coins,
  ReceiptText,
  TrendingUp,
  Layers3,
  LayoutDashboard,
  SlidersHorizontal,
  Waves,
} from "lucide-react";

type WorkspaceSidebarProps = {
  name: string;
  activeCapexTab?: string;
  active:
    | "data"
    | "entry"
    | "process"
    | "main"
    | "capex"
    | "opex"
    | "revenue"
    | "scenario"
    | "sensitivity"
    | "overview";
};

export function WorkspaceSidebar({
  name,
  active,
  activeCapexTab,
}: WorkspaceSidebarProps) {
  return (
    <>
      <aside className="sidebar">
        <Link className="brand" href="/dashboard">
          <span className="brand-mark">
            <Waves size={23} />
          </span>
          <span>
            flowvalue<span className="brand-ai"> AI</span>
          </span>
        </Link>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-switch">
          <span className="workspace-icon">
            <FlaskConical size={17} />
          </span>
          <div>
            <strong>{name}</strong>
            <small>Process economics</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-caption">ENTRY</div>
        <nav aria-label="Entry">
          <Link
            href="/entry"
            className={active === "entry" ? "nav-selected" : undefined}
            aria-current={active === "entry" ? "page" : undefined}
          >
            <FileInput size={18} />
            Entry
            {active === "entry" && <span className="nav-dot" />}
          </Link>
          <Link href="/data" className={active === "data" ? "nav-selected" : undefined}>
            <Layers3 size={18} /> Data <ChevronDown size={14} />
          </Link>
          {active === "data" && (
            <div className="capex-subnav" aria-label="Data pages">
              <Link href="/data/equipment" className="capex-child-active" aria-current="page">Equipment</Link>
            </div>
          )}
        </nav>
        <div className="nav-caption">PROCESS VISUALISATION</div>
        <nav aria-label="Process visualisation">
          <Link
            href="/process-flow"
            className={active === "process" ? "nav-selected" : undefined}
            aria-current={active === "process" ? "page" : undefined}
          >
            <Layers3 size={18} />
            Interactive process flow
            {active === "process" && <span className="nav-dot" />}
          </Link>
        </nav>
        <div className="nav-caption">ANALYST WORKSPACE</div>
        <nav aria-label="Analyst workspace">
          <Link
            href="/main-dashboard"
            className={active === "main" ? "nav-selected" : undefined}
            aria-current={active === "main" ? "page" : undefined}
          >
            <LayoutDashboard size={18} />
            Main dashboard
            {active === "main" && <span className="nav-dot" />}
          </Link>
          <Link
            href="/capex"
            className={active === "capex" ? "nav-selected" : undefined}
            aria-current={active === "capex" ? "page" : undefined}
          >
            <Coins size={18} />
            Capex
            <ChevronDown
              size={14}
              className={
                active === "capex"
                  ? "capex-parent-chevron capex-parent-open"
                  : "capex-parent-chevron"
              }
            />
          </Link>
          {active === "capex" && (
            <div className="capex-subnav" aria-label="CAPEX pages">
              {[
                ["summary", "Summary"],
                ["equipment", "Equipment"],
                ["direct-costs", "Direct Costs"],
                ["indirect-costs", "Indirect Costs"],
                ["working-capital", "Working Capital"],
                ["assumptions", "Assumptions & Sources"],
                ["validation", "Validation / Checks"],
              ].map(([tab, label]) => (
                <Link
                  key={tab}
                  href={"/capex/" + tab}
                  className={
                    activeCapexTab === tab ? "capex-child-active" : undefined
                  }
                  aria-current={activeCapexTab === tab ? "page" : undefined}
                >
                  {label}
                </Link>
              ))}
            </div>
          )}
          <Link
            href="/opex"
            className={active === "opex" ? "nav-selected" : undefined}
            aria-current={active === "opex" ? "page" : undefined}
          >
            <ReceiptText size={18} />
            Opex
            {active === "opex" && <span className="nav-dot" />}
          </Link>
          <Link
            href="/revenue"
            className={active === "revenue" ? "nav-selected" : undefined}
            aria-current={active === "revenue" ? "page" : undefined}
          >
            <TrendingUp size={18} />
            Revenue
            {active === "revenue" && <span className="nav-dot" />}
          </Link>
          <Link
            href="/dashboard"
            className={active === "overview" ? "nav-selected" : undefined}
            aria-current={active === "overview" ? "page" : undefined}
          >
            <FlaskConical size={18} />
            Design basis & evidence
            {active === "overview" && <span className="nav-dot" />}
          </Link>
        </nav>
        <div className="nav-caption">PLAYGROUND</div>
        <nav aria-label="Playground">
          <Link
            href="/scenario"
            className={active === "scenario" ? "nav-selected" : undefined}
            aria-current={active === "scenario" ? "page" : undefined}
          >
            <GitBranch size={18} />
            Scenario
            {active === "scenario" && <span className="nav-dot" />}
          </Link>
          <Link
            href="/sensitivity"
            className={active === "sensitivity" ? "nav-selected" : undefined}
            aria-current={active === "sensitivity" ? "page" : undefined}
          >
            <SlidersHorizontal size={18} />
            Sensitivity
            {active === "sensitivity" && <span className="nav-dot" />}
          </Link>
        </nav>
        <div className="sidebar-note">
          <Activity size={18} />
          <strong>From process to possibility.</strong>
          <p>Explore the economics behind your next engineering decision.</p>
          <span>
            <i /> ENGINEERING WORKSPACE
          </span>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">FV</span>
          <div>
            <strong>Engineering workspace</strong>
            <small>FlowValue AI · v0.1</small>
          </div>
        </div>
      </aside>
      <details className="workspace-mobile-nav" key={active}>
        <summary>
          Workspace navigation ·{" "}
          {active === "overview"
            ? "Design basis & evidence"
            : active === "main"
              ? "Main dashboard"
              : active}
        </summary>
        <nav aria-label="Mobile workspace">
          {[
            ["entry", "/entry", "Entry"],
            ["main", "/main-dashboard", "Main dashboard"],
            ["capex", "/capex", "CAPEX"],
            ...(active === "capex"
              ? [
                  ["capex-summary", "/capex/summary", "  Summary"],
                  ["capex-equipment", "/capex/equipment", "  Equipment"],
                  ["capex-direct", "/capex/direct-costs", "  Direct Costs"],
                  [
                    "capex-indirect",
                    "/capex/indirect-costs",
                    "  Indirect Costs",
                  ],
                  [
                    "capex-working",
                    "/capex/working-capital",
                    "  Working Capital",
                  ],
                  [
                    "capex-assumptions",
                    "/capex/assumptions",
                    "  Assumptions & Sources",
                  ],
                  [
                    "capex-validation",
                    "/capex/validation",
                    "  Validation / Checks",
                  ],
                ]
              : []),
            ["opex", "/opex", "OPEX"],
            ["revenue", "/revenue", "Revenue"],
            ["overview", "/dashboard", "Design basis & evidence"],
            ["scenario", "/scenario", "Scenario"],
            ["sensitivity", "/sensitivity", "Sensitivity"],
            ["process", "/process-flow", "Process flow"],
          ].map(([key, href, label]) => (
            <Link
              key={key}
              href={href}
              aria-current={active === key ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
      </details>
    </>
  );
}
