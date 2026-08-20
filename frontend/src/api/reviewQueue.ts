import { apiGet, apiPost } from "./client";
import type {
  ReviewQueueResponse,
  ReviewItem,
  ReviewResolveRequest,
} from "@/types/backend";

export function listReviewItems(
  page = 1,
  pageSize = 20,
  resolved = false,
): Promise<ReviewQueueResponse> {
  return apiGet<ReviewQueueResponse>(
    `/review-queue?page=${page}&page_size=${pageSize}&resolved=${resolved}`,
  );
}

export function getReviewItem(itemId: string): Promise<ReviewItem> {
  return apiGet<ReviewItem>(`/review-queue/${itemId}`);
}

export function resolveReviewItem(
  itemId: string,
  data: ReviewResolveRequest,
): Promise<ReviewItem> {
  return apiPost<ReviewItem>(`/review-queue/${itemId}/resolve`, data);
}
