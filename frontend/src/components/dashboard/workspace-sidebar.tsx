import {
  Activity,
  ChevronDown,
  FileInput,
  FlaskConical,
  Coins,
  ReceiptText,
  TrendingUp,
  Layers3,
  LayoutDashboard,
  ShieldCheck,
  SlidersHorizontal,
  Upload,
  Waves,
} from "lucide-react";

type WorkspaceSidebarProps = {
  name: string;
  active: "entry" | "process" | "main" | "capex" | "opex" | "revenue" | "overview";
};

export function WorkspaceSidebar({ name, active }: WorkspaceSidebarProps) {
  const dashboardHref = (hash: string) =>
    active === "overview" ? hash : `/dashboard${hash}`;

  return (
      <aside className="sidebar">
        <a className="brand" href="/dashboard">
          <span className="brand-mark">
            <Waves size={23} />
          </span>
          <span>
            flowvalue<span className="brand-ai"> AI</span>
          </span>
        </a>
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
          <a
            href="/entry"
            className={active === "entry" ? "nav-selected" : undefined}
            aria-current={active === "entry" ? "page" : undefined}
          >
            <FileInput size={18} />
            Entry
            {active === "entry" && <span className="nav-dot" />}
          </a>
          <a href="/entry#streams">
            <Upload size={18} />
            Simulation data
          </a>
        </nav>
        <div className="nav-caption">PROCESS VISUALISATION</div>
        <nav aria-label="Process visualisation">
          <a
            href="/process-flow"
            className={active === "process" ? "nav-selected" : undefined}
            aria-current={active === "process" ? "page" : undefined}
          >
            <Layers3 size={18} />
            Interactive process flow
            {active === "process" && <span className="nav-dot" />}
          </a>
        </nav>
        <div className="nav-caption">ANALYSIS</div>
        <nav>
          <a
            href="/main-dashboard"
            className={active === "main" ? "nav-selected" : undefined}
            aria-current={active === "main" ? "page" : undefined}
          >
            <LayoutDashboard size={18} />
            Main dashboard
            {active === "main" && <span className="nav-dot" />}
          </a>
          <a
            href="/capex"
            className={active === "capex" ? "nav-selected" : undefined}
            aria-current={active === "capex" ? "page" : undefined}
          >
            <Coins size={18} />
            Capex
            {active === "capex" && <span className="nav-dot" />}
          </a>
          <a
            href="/opex"
            className={active === "opex" ? "nav-selected" : undefined}
            aria-current={active === "opex" ? "page" : undefined}
          >
            <ReceiptText size={18} />
            Opex
            {active === "opex" && <span className="nav-dot" />}
          </a>
          <a
            href="/revenue"
            className={active === "revenue" ? "nav-selected" : undefined}
            aria-current={active === "revenue" ? "page" : undefined}
          >
            <TrendingUp size={18} />
            Revenue
            {active === "revenue" && <span className="nav-dot" />}
          </a>
          <a
            href={dashboardHref("#overview")}
            className={active === "overview" ? "nav-selected" : undefined}
            aria-current={active === "overview" ? "page" : undefined}
          >
            <Layers3 size={18} />
            Analysis tools
            {active === "overview" && <span className="nav-dot" />}
          </a>
          <a href={dashboardHref("#equipment")}>
            <Layers3 size={18} />
            Equipment & costing
          </a>
          <a href={dashboardHref("#playground")}>
            <SlidersHorizontal size={18} />
            Financial playground
          </a>
          <a href="/main-dashboard#risk">
            <ShieldCheck size={18} />
            Risk & uncertainty
          </a>
          <a href={dashboardHref("#engineering-analyst")}>
            <FlaskConical size={18} />
            Engineering analyst
          </a>
          <a href={dashboardHref("#study")}>
            <FlaskConical size={18} />
            Analyst workspace
          </a>
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
  );
}
