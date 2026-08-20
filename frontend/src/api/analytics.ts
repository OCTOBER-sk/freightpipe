// Analytics API — BACKEND.md §4.1
import { apiGet } from "./client";
import type { AnalyticsUsageResponse } from "@/types/backend";

/**
 * GET /v1/analytics/usage — account-level usage and accuracy metrics
 * §4.1: query params period (default 30d, options: 7d, 30d, 90d)
 */
export function getAnalyticsUsage(period: string = "30d"): Promise<AnalyticsUsageResponse> {
  return apiGet<AnalyticsUsageResponse>(`/analytics/usage?period=${period}`);
}
