// Review Queue API — BACKEND.md §4.1
import { apiGet, apiPost } from "./client";
import type {
  ReviewQueueResponse,
  ReviewItem,
  ReviewResolveRequest,
} from "@/types/backend";

/**
 * GET /v1/review-queue — list pending review items
 * §4.1: query params state (default pending), limit (default 50, max 200), cursor
 */
export function listReviewItems(params?: {
  state?: string;
  limit?: number;
  cursor?: string;
}): Promise<ReviewQueueResponse> {
  const searchParams = new URLSearchParams();
  if (params?.state) searchParams.set("state", params.state);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.cursor) searchParams.set("cursor", params.cursor);
  const qs = searchParams.toString();
  return apiGet<ReviewQueueResponse>(`/review-queue${qs ? `?${qs}` : ""}`);
}

/**
 * GET /v1/review-queue/{item_id} — get single review item
 */
export function getReviewItem(itemId: string): Promise<ReviewItem> {
  return apiGet<ReviewItem>(`/review-queue/${itemId}`);
}

/**
 * POST /v1/review-queue/{item_id}/resolve — human resolves a review item
 * §4.1: resolution: approved | corrected | escalated
 * §5.4: frontend sends only touched fields in corrected_fields
 */
export function resolveReviewItem(
  itemId: string,
  data: ReviewResolveRequest,
): Promise<ReviewItem> {
  return apiPost<ReviewItem>(`/review-queue/${itemId}/resolve`, data);
}
