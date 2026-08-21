import { Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import Landing from "@/routes/landing/Landing";
import Login from "@/routes/Login";
import Register from "@/routes/Register";
import Dashboard from "@/routes/dashboard/Dashboard";
import Documents from "@/routes/documents/Documents";
import ReviewQueueList from "@/routes/review-queue/ReviewQueueList";
import ReviewItemDetail from "@/routes/review-queue/ReviewItemDetail";
import Analytics from "@/routes/analytics/Analytics";
import Settings from "@/routes/settings/Settings";
import Docs from "@/routes/docs/Docs";
import JobList from "@/routes/jobs/JobList";
import JobSubmit from "@/routes/jobs/JobSubmit";
import JobDetail from "@/routes/jobs/JobDetail";
import JobResult from "@/routes/jobs/JobResult";

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/docs" element={<Docs />} />

      {/* Protected routes inside Layout shell */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/jobs" element={<JobList />} />
        <Route path="/jobs/new" element={<JobSubmit />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/jobs/:id/result" element={<JobResult />} />
        <Route path="/review-queue" element={<ReviewQueueList />} />
        <Route path="/review-queue/:id" element={<ReviewItemDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
