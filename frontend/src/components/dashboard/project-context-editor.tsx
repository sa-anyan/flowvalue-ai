"use client";

import { X } from "lucide-react";
import type { AdvisorContext } from "./universal-advisor";

export function ProjectContextEditor({
  context,
  onContext,
}: {
  context: AdvisorContext;
  onContext: (value: AdvisorContext) => void;
}) {
  return (
    <section className="panel entry-context-panel" id="project-details">
      <div className="panel-heading">
        <div>
          <h2>Project description & context</h2>
          <p>Name, describe and locate the process before analysing it.</p>
        </div>
      </div>
        <div className="advisor-context-grid">
          <label>
            Project name
            <input
              aria-label="Advisor project name"
              value={context.name}
              maxLength={120}
              onChange={(e) => onContext({ ...context, name: e.target.value })}
            />
          </label>
          <label>
            Process class
            <select
              aria-label="Process classification"
              value={context.classification}
              onChange={(e) =>
                onContext({ ...context, classification: e.target.value })
              }
            >
              {[
                "auto",
                "general",
                "electrochemical",
                "thermal",
                "biological",
                "separation",
                "circular",
                "specialty",
              ].map((x) => (
                <option key={x} value={x}>
                  {x === "auto"
                    ? "Auto-detect from context"
                    : x[0].toUpperCase() + x.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Region
            <input
              aria-label="Project region"
              placeholder="Country / power market"
              value={context.region}
              maxLength={120}
              onChange={(e) =>
                onContext({ ...context, region: e.target.value })
              }
            />
          </label>
        </div>
        <label className="advisor-description">
          Process context
          <input
            aria-label="Process description"
            placeholder="Describe the actual process, product and key equipment"
            value={context.description}
            maxLength={2000}
            onChange={(e) =>
              onContext({ ...context, description: e.target.value })
            }
          />
        </label>
        <details className="advisor-basis named-costs">
          <summary>Detailed annual costs (optional)</summary>
          <p>
            Base USD/year components of the existing raw-material and utility
            budgets. They are not additional costs. Category sliders scale every
            component; update the base OPEX totals below if the budget changes.
          </p>
          {(["raw_materials", "utilities"] as const).map((key) => (
            <section key={key}>
              <div className="named-cost-heading">
                <strong>
                  {key === "raw_materials"
                    ? "Raw materials"
                    : "Utilities: electricity / steam / water"}
                </strong>
                <button
                  disabled={context[key].length >= 100}
                  onClick={() =>
                    onContext({
                      ...context,
                      [key]: [
                        ...context[key],
                        {
                          name: `${key === "raw_materials" ? "Material" : "Utility"} ${context[key].length + 1}`,
                          annual_cost: 0,
                        },
                      ],
                    })
                  }
                >
                  Add component
                </button>
              </div>
              {context[key].map((row, i) => (
                <div className="named-cost-row" key={i}>
                  <input
                    aria-label={`${key} component ${i + 1} name`}
                    value={row.name}
                    maxLength={120}
                    onChange={(e) =>
                      onContext({
                        ...context,
                        [key]: context[key].map((x, j) =>
                          j === i ? { ...x, name: e.target.value } : x,
                        ),
                      })
                    }
                  />
                  <input
                    type="number"
                    min={0}
                    aria-label={`${key} component ${i + 1} annual cost`}
                    value={row.annual_cost}
                    onChange={(e) =>
                      onContext({
                        ...context,
                        [key]: context[key].map((x, j) =>
                          j === i
                            ? { ...x, annual_cost: Number(e.target.value) }
                            : x,
                        ),
                      })
                    }
                  />
                  <button
                    className="icon-button"
                    aria-label={`Remove ${key} component ${i + 1}`}
                    onClick={() =>
                      onContext({
                        ...context,
                        [key]: context[key].filter((_, j) => i !== j),
                      })
                    }
                  >
                    <X size={13} />
                  </button>
                </div>
              ))}
            </section>
          ))}
        </details>
    </section>
  );
}
