import { useState, type FormEvent } from "react";
import { useAuth } from "@/context/AuthContext";
import { updateProfile } from "@/api/auth";
import { ApiClientError } from "@/api/client";
import styles from "./Profile.module.css";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [email, setEmail] = useState(user?.email ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [companyName, setCompanyName] = useState(user?.company_name ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const updated = await updateProfile({
        email: email.trim(),
        phone: phone.trim() || undefined,
        company_name: companyName.trim(),
      });
      setUser(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.error.message);
      } else {
        setError("Failed to update profile.");
      }
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    email !== (user?.email ?? "") ||
    phone !== (user?.phone ?? "") ||
    companyName !== (user?.company_name ?? "");

  return (
    <div>
      <h2 className={styles.sectionTitle}>Profile</h2>
      <p className={styles.description}>
        Manage your account information.
      </p>

      {error && <div className={styles.error}>{error}</div>}
      {success && <div className={styles.success}>Profile updated.</div>}

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="profile-email">Email</label>
          <input
            id="profile-email"
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="profile-phone">Phone</label>
          <input
            id="profile-phone"
            type="tel"
            className={styles.input}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Optional"
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="profile-company">Company Name</label>
          <input
            id="profile-company"
            type="text"
            className={styles.input}
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          className={styles.saveBtn}
          disabled={saving || !hasChanges}
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </form>
    </div>
  );
}
