import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import styles from "@/styles/layout.module.css";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "\u25A0" },
  { to: "/documents", label: "Documents", icon: "\u25B4" },
  { to: "/review-queue", label: "Review Queue", icon: "\u25C6" },
  { to: "/analytics", label: "Analytics", icon: "\u2582" },
  { to: "/settings", label: "Settings", icon: "\u2699" },
  { to: "/docs", label: "Docs", icon: "\u2630" },
];

function getPageTitle(pathname: string): string {
  if (pathname.startsWith("/dashboard")) return "Dashboard";
  if (pathname.startsWith("/documents")) return "Documents";
  if (pathname.startsWith("/review-queue")) return "Review Queue";
  if (pathname.startsWith("/analytics")) return "Analytics";
  if (pathname.startsWith("/settings")) return "Settings";
  if (pathname.startsWith("/docs")) return "Documentation";
  return "FreightPipe";
}

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <span className={styles.logoAccent}>Freight</span>Pipe
          </div>
          <div className={styles.subtitle}>Document Normalization</div>
        </div>

        <nav className={styles.nav}>
          <div className={styles.navSection}>
            <div className={styles.navLabel}>Navigation</div>
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `${styles.navLink} ${isActive ? styles.navLinkActive : ""}`
                }
              >
                <span className={styles.navIcon}>{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            {user?.company_name ?? user?.email ?? "Account"}
          </div>
          <button
            type="button"
            className={styles.logoutBtn}
            onClick={logout}
          >
            Log out
          </button>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.headerTitle}>
            {getPageTitle(location.pathname)}
          </h1>
        </header>
        <main className={styles.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
