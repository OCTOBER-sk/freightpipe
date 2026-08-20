// ConfidenceRail — FRONTEND.md §1.5, §4.5
// 3px left-edge bar, color by confidence state (green/amber/red)
// Used at every scale: job row, document card, field row
import {
  getConfidenceLevel,
  type ConfidenceScope,
} from "@/config/confidence";
import styles from "./ConfidenceRail.module.css";

interface ConfidenceRailProps {
  /** Confidence score 0-1 */
  value: number;
  /** Scope for threshold comparison */
  scope?: ConfidenceScope;
  /** Override rail color state */
  state?: "queued" | "processing" | "needs_review" | "complete" | "failed" | "high" | "mid" | "low";
  children: React.ReactNode;
  className?: string;
}

function getRailState(
  value: number,
  scope: ConfidenceScope,
): "high" | "mid" | "low" {
  return getConfidenceLevel(value, scope);
}

export default function ConfidenceRail({
  value,
  scope = "field",
  state,
  children,
  className = "",
}: ConfidenceRailProps) {
  const railState = state ?? getRailState(value, scope);

  return (
    <div
      className={`${styles.rail} ${className}`}
      data-rail-state={railState}
    >
      {children}
    </div>
  );
}
