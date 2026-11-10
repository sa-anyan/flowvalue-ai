"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { WorkspaceNavigation } from "@/components/workspace-navigation";
import { WorkspaceIcon } from "@/components/workspace-visuals";
import { assessmentFromUrl, assessmentHref } from "@/lib/assessment-navigation";
import "./workspace.css";
const sections = [
  {
    id: "scenarios",
    label: "Scenarios",
    title: "Scenario analysis",
    description: "Compare different project choices side by side.",
    empty: "Scenario setup is not available yet.",
  },
  {
    id: "sensitivity",
    label: "Sensitivity",
    title: "Sensitivity analysis",
    description:
      "Explore which inputs have the biggest effect on your results.",
    empty: "Sensitivity setup is not available yet.",
  },
] as const;
export function ScenarioWorkspace() {
  const [id, setId] = useState(""),
    [name, setName] = useState("Current assessment"),
    [selected, setSelected] = useState(0),
    [dark, setDark] = useState(false),
    [error, setError] = useState("");
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  useEffect(() => {
    setId(
      assessmentFromUrl(
        location.href,
        localStorage.getItem("flowvalue-assessment"),
      ),
    );
    setDark(localStorage.getItem("flowvalue-theme") === "dark");
  }, []);
  useEffect(() => {
    if (!id) return;
    const controller = new AbortController();
    void fetch(`/api/assessments/${id}`, {
      cache: "no-store",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw Error("Could not load the project name.");
        return response.json();
      })
      .then((state) => setName(state.filename || "Current assessment"))
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [id]);
  return (
    <div className={`shell ${dark ? "dark" : ""}`} data-page="scenario">
      <a className="skip-link" href="#scenario-content">
        Skip to analysis
      </a>
      <aside>
        <Link className="brand" href={assessmentHref("/entry", id)}>
          ≋ flowvalue <small>AI</small>
        </Link>
        <p className="eyebrow">WORKSPACE</p>
        <div className="project">
          {name}
          <small>Project analysis</small>
        </div>
        <WorkspaceNavigation page="scenario" id={id} />
      </aside>
      <main>
        <header>
          <span className="breadcrumb">
            Workspace › <strong>Scenario & Sensitivity Analysis</strong>
          </span>
          <button
            className="theme-toggle"
            aria-label="Toggle dark mode"
            onClick={() => {
              setDark(!dark);
              localStorage.setItem("flowvalue-theme", !dark ? "dark" : "light");
            }}
          >
            {dark ? "☀" : "☾"}
          </button>
        </header>
        <div className="content scenario-workspace" id="scenario-content">
          <h1>Scenario & Sensitivity Analysis</h1>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <div
            role="tablist"
            aria-label="Analysis type"
            className="scenario-tabs"
          >
            {sections.map((section, index) => (
              <button
                key={section.id}
                ref={(node) => {
                  tabs.current[index] = node;
                }}
                id={`tab-${section.id}`}
                type="button"
                role="tab"
                aria-selected={selected === index}
                aria-controls={`panel-${section.id}`}
                tabIndex={selected === index ? 0 : -1}
                onClick={() => setSelected(index)}
                onKeyDown={(event) => {
                  const next =
                    event.key === "ArrowRight"
                      ? (index + 1) % sections.length
                      : event.key === "ArrowLeft"
                        ? (index + sections.length - 1) % sections.length
                        : event.key === "Home"
                          ? 0
                          : event.key === "End"
                            ? sections.length - 1
                            : null;
                  if (next !== null) {
                    event.preventDefault();
                    setSelected(next);
                    tabs.current[next]?.focus();
                  }
                }}
              >
                {section.label}
              </button>
            ))}
          </div>
          {sections.map((section, index) => (
            <section
              key={section.id}
              role="tabpanel"
              id={`panel-${section.id}`}
              aria-labelledby={`tab-${section.id}`}
              hidden={selected !== index}
              tabIndex={0}
              className="scenario-panel"
            >
              <div className="scenario-panel-heading">
                <WorkspaceIcon name="scenario" />
                <div>
                  <h2>{section.title}</h2>
                  <p>{section.description}</p>
                </div>
              </div>
              <div className="scenario-empty">
                <span className="scenario-status">Not set up</span>
                <p>{section.empty}</p>
              </div>
            </section>
          ))}
          <div className="scenario-related">
            <span>Uncertainty testing</span>
            <Link href={assessmentHref("/monte-carlo/setup", id)}>
              Open Monte Carlo →
            </Link>
          </div>
          {!id && (
            <p className="scenario-start">
              Select a project from <Link href="/entry">Entry</Link> to keep
              your analysis with its assessment.
            </p>
          )}
        </div>
      </main>
    </div>
  );
}
