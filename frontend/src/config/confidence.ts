export const CONFIDENCE_THRESHOLDS = {
  document: 0.8,
  field: 0.7,
} as const;

export type ConfidenceLevel = "high" | "mid" | "low";

export function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score >= CONFIDENCE_THRESHOLDS.document) return "high";
  if (score >= CONFIDENCE_THRESHOLDS.field) return "mid";
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
