import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { register as apiRegister } from "@/api/auth";
import { ApiClientError } from "@/api/client";
import styles from "@/styles/auth.module.css";

interface ValidationErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  companyName?: string;
}

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>({});
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  function validate(): boolean {
    const errors: ValidationErrors = {};

    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = "Enter a valid email address.";
    }

    if (!companyName.trim()) {
      errors.companyName = "Company name is required.";
    }

    if (password.length < 8) {
      errors.password = "Password must be at least 8 characters.";
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match.";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError("");

    try {
      const res = await apiRegister({
        email: email.trim(),
        phone: phone.trim() || undefined,
        company_name: companyName.trim(),
        password,
      });
      login(res.token, res.user);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          setError("An account with this email already exists.");
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
        <div className={styles.authSubtitle}>Create your account</div>

        <form onSubmit={handleSubmit}>
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
            {validationErrors.email && (
              <div className={styles.validationError}>{validationErrors.email}</div>
            )}
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="phone">
              Phone <span style={{ color: "var(--text-tertiary)" }}>(optional)</span>
            </label>
            <input
              id="phone"
              type="tel"
              className={styles.formInput}
              placeholder="+1 (555) 000-0000"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="company">
              Company Name
            </label>
            <input
              id="company"
              type="text"
              className={styles.formInput}
              placeholder="Your company or brokerage"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
            />
            {validationErrors.companyName && (
              <div className={styles.validationError}>{validationErrors.companyName}</div>
            )}
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel} htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                className={styles.formInput}
                placeholder="Min 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                required
                minLength={8}
              />
              {validationErrors.password && (
                <div className={styles.validationError}>{validationErrors.password}</div>
              )}
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel} htmlFor="confirm-password">
                Confirm Password
              </label>
              <input
                id="confirm-password"
                type="password"
                className={styles.formInput}
                placeholder="Repeat password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
              {validationErrors.confirmPassword && (
                <div className={styles.validationError}>{validationErrors.confirmPassword}</div>
              )}
            </div>
          </div>

          {error && <div className={styles.errorBanner}>{error}</div>}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={loading}
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <div className={styles.formHint}>
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
