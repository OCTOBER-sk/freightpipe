// config/confidence.ts
// SOURCE: BACKEND.md §5.7 — explicitly flagged there as "starting points to be
// tuned against the eval harness in §9, never presented to the client as fixed
// truth." Do not inline these numbers anywhere else in the codebase.

export const CONFIDENCE_THRESHOLDS = {
  document: 0.80,
  field: 0.70,
} as const;

export type ConfidenceScope = "document" | "field";
export type ConfidenceLevel = "high" | "mid" | "low";

/**
 * FRONTEND.md §4.1: ConfidenceBadge
 * - green: value >= CONFIDENCE_THRESHOLDS[scope]
 * - amber: value >= CONFIDENCE_THRESHOLDS[scope] - 0.10
 * - red: below that
 */
export function getConfidenceLevel(
  score: number,
  scope: ConfidenceScope = "field",
): ConfidenceLevel {
  const threshold = CONFIDENCE_THRESHOLDS[scope];
  if (score >= threshold) return "high";
  if (score >= threshold - 0.10) return "mid";
  return "low";
}

export function getConfidenceColor(level: ConfidenceLevel): string {
  switch (level) {
    case "high":
      return "var(--confidence-high)";
    case "mid":
      return "var(--confidence-mid)";
    case "low":
      return "var(--confidence-low)";
  }
}

export function getConfidenceLabel(level: ConfidenceLevel): string {
  switch (level) {
    case "high":
      return "High";
    case "mid":
      return "Mid";
    case "low":
      return "Low";
  }
}
