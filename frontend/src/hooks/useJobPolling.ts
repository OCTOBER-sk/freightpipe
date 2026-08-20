import { useQuery } from "@tanstack/react-query";
import { getJob } from "@/api/jobs";
import type { JobDetail } from "@/types/backend";
import { TERMINAL_STATUSES } from "@/types/backend";

interface UseJobPollingOptions {
  enabled?: boolean;
}

function getPollInterval(elapsedMs: number): number {
  if (elapsedMs < 30_000) return 2_000;   // 2s for first 30s
  if (elapsedMs < 120_000) return 5_000;  // 5s from 30s to 2min
  return 15_000;                           // 15s after 2min
}

const MAX_POLL_DURATION = 30 * 60 * 1000; // 30 minutes (§6)

export function useJobPolling(jobId: string, options: UseJobPollingOptions = {}) {
  const startTime = Date.now();

  return useQuery<JobDetail>({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      // Stop polling if job is in a terminal state (§6)
      if (job && TERMINAL_STATUSES.includes(job.status)) {
        return false;
      }
      // Stop polling after 30 minutes (§6)
      const elapsed = Date.now() - startTime;
      if (elapsed > MAX_POLL_DURATION) {
        return false;
      }
      return getPollInterval(elapsed);
    },
    enabled: options.enabled !== false,
  });
}
