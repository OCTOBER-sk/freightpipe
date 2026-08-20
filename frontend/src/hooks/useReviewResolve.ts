import { useMutation, useQueryClient } from "@tanstack/react-query";
import { resolveReviewItem } from "@/api/reviewQueue";
import type { ReviewResolveRequest, ReviewItem } from "@/types/backend";

interface UseReviewResolveOptions {
  onSuccess?: (item: ReviewItem) => void;
  onError?: (error: Error) => void;
}

export function useReviewResolve(options: UseReviewResolveOptions = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, data }: { itemId: string; data: ReviewResolveRequest }) =>
      resolveReviewItem(itemId, data),
    onSuccess: (item) => {
      // Invalidate review queue list
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      // Invalidate the specific item
      queryClient.invalidateQueries({ queryKey: ["review-item", item.id] });
      // Invalidate the related job
      queryClient.invalidateQueries({ queryKey: ["job", item.job_id] });
      options.onSuccess?.(item);
    },
    onError: (error: Error) => {
      options.onError?.(error);
    },
  });
}
