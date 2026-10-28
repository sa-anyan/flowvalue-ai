import { notFound } from "next/navigation";

const sections = [
  "summary", "equipment", "direct-costs", "indirect-costs",
  "working-capital", "assumptions", "validation",
] as const;

export function generateStaticParams() {
  return sections.map((section) => ({ section }));
}

export default async function CapexChildPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  if (!sections.some((candidate) => candidate === section)) notFound();
  // The parent workspace layout keeps a single live project instance.
  // Dashboard renders the selected CAPEX view from the current pathname.
  return null;
}
