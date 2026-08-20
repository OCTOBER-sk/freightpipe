import { Routes, Route, Navigate } from "react-router-dom";
import JobList from "@/routes/jobs/JobList";
import JobSubmit from "@/routes/jobs/JobSubmit";
import JobDetail from "@/routes/jobs/JobDetail";
import JobResult from "@/routes/jobs/JobResult";
import ReviewQueueList from "@/routes/review-queue/ReviewQueueList";
import ReviewItemDetail from "@/routes/review-queue/ReviewItemDetail";
import Analytics from "@/routes/analytics/Analytics";
import ApiKeys from "@/routes/settings/ApiKeys";
import Webhooks from "@/routes/settings/Webhooks";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/jobs" replace />} />
      <Route path="/jobs" element={<JobList />} />
      <Route path="/jobs/new" element={<JobSubmit />} />
      <Route path="/jobs/:id" element={<JobDetail />} />
      <Route path="/jobs/:id/result" element={<JobResult />} />
      <Route path="/review-queue" element={<ReviewQueueList />} />
      <Route path="/review-queue/:id" element={<ReviewItemDetail />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/settings/api-keys" element={<ApiKeys />} />
      <Route path="/settings/webhooks" element={<Webhooks />} />
    </Routes>
  );
}
