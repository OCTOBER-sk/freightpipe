import { apiGet } from "./client";
import type { AnalyticsResponse } from "@/types/backend";

export function getAnalytics(
  startDate?: string,
  endDate?: string,
): Promise<AnalyticsResponse> {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const qs = params.toString();
  return apiGet<AnalyticsResponse>(`/analytics${qs ? `?${qs}` : ""}`);
}
