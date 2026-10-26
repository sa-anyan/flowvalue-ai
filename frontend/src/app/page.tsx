"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState("Connecting to API…");
  useEffect(() => {
    const controller = new AbortController();
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${base}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      })
      .then((data) => setStatus(data.status === "ok" ? "API connected" : "API unavailable"))
      .catch((error) => {
        if (error.name !== "AbortError") setStatus("API offline — start the backend with make api");
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center gap-6 px-8">
      <p className="text-sm font-semibold uppercase tracking-widest text-teal-600">Development environment</p>
      <h1 className="text-5xl font-bold tracking-tight">FlowValue AI</h1>
      <p className="text-xl">The AI-driven techno-economic assessment copilot for Chemical &amp; CleanTech Engineering.</p>
      <p role="status" className="rounded-xl border p-4">{status}</p>
      <a className="text-teal-600 underline" href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/docs`}>Open API documentation</a>
    </main>
  );
}
