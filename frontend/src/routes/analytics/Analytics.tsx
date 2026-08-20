import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getAnalyticsUsage } from "@/api/analytics";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import styles from "./Analytics.module.css";

const PERIODS = [
  { label: "7 days", value: "7d" },
  { label: "30 days", value: "30d" },
  { label: "90 days", value: "90d" },
];

export default function Analytics() {
  const [period, setPeriod] = useState("30d");

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["analytics", period],
    queryFn: () => getAnalyticsUsage(period),
  });

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Analytics</h1>
        </div>
        <div className={styles.loading}>Loading analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Analytics</h1>
        </div>
        <div className={styles.error}>
          <p className={styles.errorTitle}>Failed to load analytics</p>
          <p className={styles.errorMessage}>{error.message}</p>
          <button type="button" className={styles.retryBtn} onClick={() => refetch()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data || data.jobs.total === 0) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Analytics</h1>
        </div>
        <div className={styles.empty}>
          <p className={styles.emptyText}>
            No data yet &mdash; analytics populate after your first completed job.
          </p>
          <Link to="/jobs/new" className={styles.emptyCta}>
            + Submit document
          </Link>
        </div>
      </div>
    );
  }

  // Build volume data for chart (synthetic daily breakdown from totals)
  const volumeData = [
    { name: "Jobs", total: data.jobs.total, completed: data.jobs.completed, needs_review: data.jobs.needs_review, failed: data.jobs.failed },
  ];

  // Build accuracy data
  const accuracyData = [
    { name: "Avg Confidence", value: Math.round(data.accuracy.avg_confidence * 100) },
    { name: "Review Rate", value: Math.round(data.accuracy.review_rate * 100) },
    { name: "Correction Rate", value: Math.round(data.accuracy.correction_rate * 100) },
  ];

  // Build processing time data
  const processingData = [
    { name: "p50", value: data.processing_time.p50_seconds },
    { name: "p90", value: data.processing_time.p90_seconds },
    { name: "p99", value: data.processing_time.p99_seconds },
  ];

  // Build LLM usage data
  const providerData = Object.entries(data.llm_usage.by_provider).map(([name, count]) => ({
    name,
    count,
  }));

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Analytics</h1>
        <select
          className={styles.periodSelect}
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          aria-label="Select time period"
        >
          {PERIODS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* Stat cards */}
      <div className={styles.stats}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Total Jobs</div>
          <div className={styles.statValue}>{data.jobs.total}</div>
          <div className={styles.statSub}>
            {data.jobs.completed} completed, {data.jobs.needs_review} review, {data.jobs.failed} failed
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Documents</div>
          <div className={styles.statValue}>{data.documents.total}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Avg Confidence</div>
          <div className={styles.statValue}>{Math.round(data.accuracy.avg_confidence * 100)}%</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Review Rate</div>
          <div className={styles.statValue}>{Math.round(data.accuracy.review_rate * 100)}%</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>LLM Calls</div>
          <div className={styles.statValue}>{data.llm_usage.total_calls}</div>
          <div className={styles.statSub}>
            {Math.round(data.llm_usage.cache_hit_rate * 100)}% cache hit rate
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>Processing p50</div>
          <div className={styles.statValue}>{data.processing_time.p50_seconds}s</div>
          <div className={styles.statSub}>
            p90: {data.processing_time.p90_seconds}s, p99: {data.processing_time.p99_seconds}s
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className={styles.chartRow}>
        <div className={styles.chartSection}>
          <h2 className={styles.chartTitle}>Accuracy Metrics</h2>
          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={accuracyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
                <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 12 }} domain={[0, 100]} unit="%" />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
                <Bar dataKey="value" fill="var(--accent)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={styles.chartSection}>
          <h2 className={styles.chartTitle}>Processing Time</h2>
          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={processingData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
                <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 12 }} unit="s" />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface-raised)",
                    border: "1px solid var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
                <Bar dataKey="value" fill="var(--confidence-high)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* LLM Usage */}
      <div className={styles.chartSection}>
        <h2 className={styles.chartTitle}>LLM Usage by Provider</h2>
        <div className={styles.chartContainer}>
          {providerData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={providerData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
                  <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface-raised)",
                      border: "1px solid var(--border)",
                      color: "var(--text-primary)",
                    }}
                  />
                  <Bar dataKey="count" fill="var(--accent)" />
                </BarChart>
              </ResponsiveContainer>
              <div className={styles.providerList}>
                {providerData.map((p) => (
                  <div key={p.name} className={styles.providerRow}>
                    <span className={styles.providerName}>{p.name}</span>
                    <span className={styles.providerCount}>{p.count} calls</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className={styles.statSub}>No LLM usage data</p>
          )}
        </div>
      </div>

      {/* Document types breakdown */}
      {Object.keys(data.documents.by_type).length > 0 && (
        <div className={styles.chartSection}>
          <h2 className={styles.chartTitle}>Documents by Type</h2>
          <div className={styles.chartContainer}>
            <div className={styles.providerList}>
              {Object.entries(data.documents.by_type).map(([type, count]) => (
                <div key={type} className={styles.providerRow}>
                  <span className={styles.providerName}>{type}</span>
                  <span className={styles.providerCount}>{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
