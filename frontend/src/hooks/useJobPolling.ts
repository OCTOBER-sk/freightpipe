import { useQuery } from "@tanstack/react-query";
import { getJob } from "@/api/jobs";
import type { Job } from "@/types/backend";
import { JobStatus } from "@/types/backend";

interface UseJobPollingOptions {
  enabled?: boolean;
}

function getPollInterval(elapsedMs: number): number {
  if (elapsedMs < 30_000) return 2_000;   // 2s for first 30s
  if (elapsedMs < 120_000) return 5_000;  // 5s from 30s to 2min
  return 15_000;                           // 15s after 2min
}

const TERMINAL_STATUSES: JobStatus[] = [
  JobStatus.COMPLETED,
  JobStatus.FAILED,
  JobStatus.REVIEW_REQUIRED,
];

export function useJobPolling(jobId: string, options: UseJobPollingOptions = {}) {
  const startTime = Date.now();

  return useQuery<Job>({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      // Stop polling if job is in a terminal state
      if (job && TERMINAL_STATUSES.includes(job.status)) {
        return false;
      }
      const elapsed = Date.now() - startTime;
      return getPollInterval(elapsed);
    },
    enabled: options.enabled !== false,
  });
}
