import { useState, type FormEvent } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { login as apiLogin } from "@/api/auth";
import { ApiClientError, getApiBaseUrl, setApiBase } from "@/api/client";
import styles from "@/styles/auth.module.css";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [serverUrl, setServerUrl] = useState(getApiBaseUrl());
  const [showServer, setShowServer] = useState(!getApiBaseUrl());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? "/dashboard";

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;

    // Save server URL if provided
    if (serverUrl.trim()) {
      setApiBase(serverUrl.trim());
    }

    setLoading(true);
    setError("");

    try {
      const res = await apiLogin({ email: email.trim(), password });
      login(res.token, res.user);
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 401) {
          setError("Invalid email or password.");
        } else {
          setError(err.error.message);
        }
      } else {
        setError("Cannot reach the server. Try again in a moment.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.authPage}>
      <div className={styles.authCard}>
        <div className={styles.authLogo}>
          <span className={styles.authLogoAccent}>Freight</span>Pipe
        </div>
        <div className={styles.authSubtitle}>Sign in to your account</div>

        <form onSubmit={handleSubmit}>
          {showServer && (
            <div className={styles.formGroup}>
              <label className={styles.formLabel} htmlFor="server">
                Backend URL
              </label>
              <input
                id="server"
                type="url"
                className={styles.formInput}
                placeholder="https://freightpipe.onrender.com"
                value={serverUrl}
                onChange={(e) => setServerUrl(e.target.value)}
                autoComplete="url"
              />
              <div className={styles.formHint}>
                The URL of your FreightPipe backend (e.g. https://freightpipe.onrender.com)
              </div>
            </div>
          )}

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className={styles.formInput}
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              autoComplete="email"
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className={styles.formInput}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && <div className={styles.errorBanner}>{error}</div>}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={loading || !email.trim() || !password}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className={styles.formHint}>
          Don&apos;t have an account? <Link to="/register">Register</Link>
        </div>
      </div>
    </div>
  );
}
