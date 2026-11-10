import AssessmentWorkspace from "@/components/assessment-workspace";
import RateRevenueWorkspace from "@/blocks/revenue/rate-workspace";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ advanced?: string }>;
}) {
  const query = await searchParams;
  return query.advanced === "1" ? (
    <AssessmentWorkspace page="revenue" />
  ) : (
    <RateRevenueWorkspace />
  );
}
