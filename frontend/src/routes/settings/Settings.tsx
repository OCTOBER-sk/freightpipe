import { useState } from "react";
import Profile from "./Profile";
import ApiKeys from "./ApiKeys";
import Webhooks from "./Webhooks";
import styles from "./Settings.module.css";

type Tab = "profile" | "api-keys" | "webhooks";

const TABS: { key: Tab; label: string }[] = [
  { key: "profile", label: "Profile" },
  { key: "api-keys", label: "API Keys" },
  { key: "webhooks", label: "Webhooks" },
];

export default function Settings() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Settings</h1>
      </div>

      <div className={styles.tabs} role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={styles.tab}
            data-active={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
            role="tab"
            aria-selected={activeTab === tab.key}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {activeTab === "profile" && <Profile />}
        {activeTab === "api-keys" && <ApiKeys />}
        {activeTab === "webhooks" && <Webhooks />}
      </div>
    </div>
  );
}
