import { Link } from "react-router-dom";
import styles from "./Landing.module.css";

const FEATURES = [
  {
    icon: "\u2699",
    title: "Multi-doc extraction",
    desc: "Handles rate confirmations, BOLs, PODs, invoices, and merged PDFs in a single upload.",
  },
  {
    icon: "\u26A0",
    title: "Confidence scoring",
    desc: "Every field carries a confidence score. Low-confidence values are flagged for human review.",
  },
  {
    icon: "\u25C6",
    title: "3-way match",
    desc: "Automatically cross-checks line items across rate con, BOL/POD, and invoice documents.",
  },
  {
    icon: "\u21BB",
    title: "Review queue",
    desc: "Items needing attention are sorted oldest-first so nothing sits unresolved.",
  },
  {
    icon: "\u2630",
    title: "REST API",
    desc: "Programmatic access via API keys. Submit documents and fetch structured JSON results.",
  },
  {
    icon: "\u25B4",
    title: "Webhooks",
    desc: "Get notified on job completion, review needed, or failure. Configure per-account or per-job.",
  },
];

const STEPS = [
  { num: "1", title: "Upload", desc: "Submit a PDF via the dashboard or API." },
  { num: "2", title: "Extract", desc: "Documents are classified, split, and fields extracted using rules + LLM." },
  { num: "3", title: "Validate", desc: "Confidence scoring, 3-way matching, and discrepancy detection run automatically." },
  { num: "4", title: "Review", desc: "Low-confidence or mismatched items go to the review queue. Everything else is ready to use." },
];

const FAQ = [
  {
    q: "What document types does FreightPipe support?",
    a: "Rate confirmations, bills of lading (BOL), proof of delivery (POD), and carrier invoices. Merged PDFs containing multiple document types are handled automatically.",
  },
  {
    q: "How does the free tier work?",
    a: "The free tier includes 100 documents per month with full access to all features. No credit card required to start.",
  },
  {
    q: "What happens when confidence is low?",
    a: "Fields below the confidence threshold are flagged and routed to the review queue. You can approve, correct, or escalate from the review interface.",
  },
  {
    q: "Can I use FreightPipe programmatically?",
    a: "Yes. Every account gets API keys. Submit documents via POST /v1/documents and poll for results or configure a webhook for notifications.",
  },
  {
    q: "Is my data secure?",
    a: "Documents are encrypted in transit and at rest. Each account is isolated. API keys are hashed at rest and only shown once at creation.",
  },
];

export default function Landing() {
  return (
    <div className={styles.landing}>
      <nav className={styles.nav}>
        <div className={styles.navInner}>
          <div className={styles.navLogo}>
            <span className={styles.navLogoAccent}>Freight</span>Pipe
          </div>
          <div className={styles.navLinks}>
            <a href="#features" className={styles.navLink}>Features</a>
            <a href="#pricing" className={styles.navLink}>Pricing</a>
            <a href="#faq" className={styles.navLink}>FAQ</a>
            <Link to="/docs" className={styles.navLink}>Docs</Link>
            <Link to="/login" className={styles.navLink}>Login</Link>
            <Link to="/register" className={styles.navCta}>Get Started</Link>
          </div>
        </div>
      </nav>

      <section className={styles.hero}>
        <div className={styles.heroInner}>
          <h1 className={styles.heroTitle}>
            Turn messy freight PDFs into clean JSON
          </h1>
          <p className={styles.heroSubtitle}>
            FreightPipe extracts, validates, and cross-checks fields from rate confirmations,
            BOLs, PODs, and invoices. Low-confidence values are flagged for human review.
          </p>
          <div className={styles.heroActions}>
            <Link to="/register" className={styles.heroCta}>Start for Free</Link>
            <Link to="/docs" className={styles.heroSecondary}>Read the Docs</Link>
          </div>
          <div className={styles.heroPreview}>
            <div className={styles.previewCard}>
              <div className={styles.previewHeader}>Result: job_a91f... &mdash; Complete</div>
              <div className={styles.previewRow}>
                <span className={styles.previewField}>load_number</span>
                <span className={styles.previewValue}>RC-48213</span>
                <span className={styles.previewConf}>0.97</span>
              </div>
              <div className={styles.previewRow}>
                <span className={styles.previewField}>linehaul_rate</span>
                <span className={styles.previewValue}>$1,850.00</span>
                <span className={styles.previewConf}>0.94</span>
              </div>
              <div className={styles.previewRow}>
                <span className={styles.previewField}>pickup_date</span>
                <span className={styles.previewValue}>2026-08-15</span>
                <span className={styles.previewConf}>0.91</span>
              </div>
              <div className={styles.previewRow}>
                <span className={styles.previewField}>fuel_surcharge</span>
                <span className={styles.previewValue}>&mdash;</span>
                <span className={styles.previewConfLow}>0.62</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className={styles.features}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>What FreightPipe does</h2>
          <p className={styles.sectionSubtitle}>
            A document normalization pipeline with human-in-the-loop review.
          </p>
          <div className={styles.featureGrid}>
            {FEATURES.map((f) => (
              <div key={f.title} className={styles.featureCard}>
                <div className={styles.featureIcon}>{f.icon}</div>
                <h3 className={styles.featureTitle}>{f.title}</h3>
                <p className={styles.featureDesc}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className={styles.howItWorks}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>How it works</h2>
          <div className={styles.stepsGrid}>
            {STEPS.map((s) => (
              <div key={s.num} className={styles.step}>
                <div className={styles.stepNum}>{s.num}</div>
                <h3 className={styles.stepTitle}>{s.title}</h3>
                <p className={styles.stepDesc}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className={styles.pricing}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>Pricing</h2>
          <p className={styles.sectionSubtitle}>Start free. Scale when you need to.</p>
          <div className={styles.pricingGrid}>
            <div className={styles.pricingCardHighlight}>
              <div className={styles.pricingTier}>Free</div>
              <div className={styles.pricingPrice}>$0</div>
              <div className={styles.pricingPeriod}>per month</div>
              <ul className={styles.pricingFeatures}>
                <li>100 documents / month</li>
                <li>Full extraction + validation</li>
                <li>Review queue</li>
                <li>API access</li>
                <li>Webhook notifications</li>
              </ul>
              <Link to="/register" className={styles.pricingCta}>Get Started</Link>
            </div>
            <div className={styles.pricingCard}>
              <div className={styles.pricingTier}>Pro</div>
              <div className={styles.pricingPrice}>Coming soon</div>
              <div className={styles.pricingPeriod}>unlimited volume</div>
              <ul className={styles.pricingFeatures}>
                <li>Unlimited documents</li>
                <li>Team access</li>
                <li>Priority processing</li>
                <li>Custom integrations</li>
              </ul>
              <button type="button" className={styles.pricingCtaMuted} disabled>Notify Me</button>
            </div>
            <div className={styles.pricingCard}>
              <div className={styles.pricingTier}>Enterprise</div>
              <div className={styles.pricingPrice}>Coming soon</div>
              <div className={styles.pricingPeriod}>custom</div>
              <ul className={styles.pricingFeatures}>
                <li>Custom SLA</li>
                <li>Dedicated support</li>
                <li>On-prem deployment</li>
                <li>Custom models</li>
              </ul>
              <button type="button" className={styles.pricingCtaMuted} disabled>Contact Sales</button>
            </div>
          </div>
        </div>
      </section>

      <section id="faq" className={styles.faq}>
        <div className={styles.sectionInner}>
          <h2 className={styles.sectionTitle}>Frequently Asked Questions</h2>
          <div className={styles.faqList}>
            {FAQ.map((item) => (
              <div key={item.q} className={styles.faqItem}>
                <h3 className={styles.faqQuestion}>{item.q}</h3>
                <p className={styles.faqAnswer}>{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerLogo}>
            <span className={styles.navLogoAccent}>Freight</span>Pipe
          </div>
          <div className={styles.footerLinks}>
            <Link to="/docs">Documentation</Link>
            <a href="https://github.com" target="_blank" rel="noreferrer">GitHub</a>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </div>
          <div className={styles.footerCopy}>
            &copy; {new Date().getFullYear()} FreightPipe. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
