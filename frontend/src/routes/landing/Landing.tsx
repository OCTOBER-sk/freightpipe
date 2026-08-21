import { Link } from "react-router-dom";
import styles from "./Landing.module.css";

const FEATURES = [
  {
    title: "Multi-doc extraction",
    desc: "Handles rate confirmations, BOLs, PODs, invoices, and merged PDFs in a single upload. Each document type uses field-specific extraction rules.",
  },
  {
    title: "Confidence scoring",
    desc: "Every extracted field carries a confidence score. Values below threshold are automatically routed to the review queue for human verification.",
  },
  {
    title: "3-way match",
    desc: "Cross-checks line items across rate confirmation, BOL/POD, and invoice documents. Discrepancies are flagged with specific field-level diffs.",
  },
  {
    title: "Review queue",
    desc: "Low-confidence and mismatched items are sorted oldest-first for operational urgency. Inline correction with approve, correct, or escalate actions.",
  },
  {
    title: "REST API",
    desc: "Programmatic access via API keys. Submit documents via POST, poll for results, and fetch structured JSON with field-level metadata.",
  },
  {
    title: "Webhooks",
    desc: "Get notified on job completion, review needed, or failure. Configure per-account defaults or per-job webhook URLs with signature verification.",
  },
];

const STEPS = [
  { num: "1", title: "Upload", desc: "Submit a PDF via the dashboard or API. Supports up to 25MB per file." },
  { num: "2", title: "Extract", desc: "Documents are classified, split if merged, and fields extracted using type-specific rules." },
  { num: "3", title: "Validate", desc: "Confidence scoring, 3-way matching, and discrepancy detection run automatically." },
  { num: "4", title: "Review", desc: "Flagged items go to the review queue. Everything else is ready to export as JSON." },
];

const FAQ = [
  {
    q: "What document types does FreightPipe support?",
    a: "Rate confirmations, bills of lading (BOL), proof of delivery (POD), and carrier invoices. Merged PDFs containing multiple document types are split and processed individually.",
  },
  {
    q: "How does the free tier work?",
    a: "The free tier includes 100 documents per month with full access to all features including API access, webhooks, and the review queue. No credit card required.",
  },
  {
    q: "What happens when confidence is low?",
    a: "Fields below the confidence threshold are flagged and routed to the review queue. You can approve the extracted value, correct it inline, or escalate for further review.",
  },
  {
    q: "Can I use FreightPipe programmatically?",
    a: "Yes. Every account gets API keys. Submit documents via POST /v1/documents and poll for results or configure a webhook for push notifications. Full API reference is in the docs.",
  },
  {
    q: "Is my data secure?",
    a: "Documents are encrypted in transit and at rest. Each account is isolated. API keys are hashed at rest and only shown once at creation. We do not train on your data.",
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
            Turn messy freight PDFs into structured data
          </h1>
          <p className={styles.heroSubtitle}>
            FreightPipe extracts, validates, and cross-checks fields from rate confirmations,
            BOLs, PODs, and invoices. Low-confidence values are flagged for human review.
          </p>
          <div className={styles.heroActions}>
            <Link to="/register" className={styles.heroCta}>Start for Free</Link>
            <Link to="/docs" className={styles.heroSecondary}>Read the Docs</Link>
          </div>
        </div>
      </section>

      <section className={styles.problem}>
        <div className={styles.problemInner}>
          <p className={styles.problemText}>
            <strong>15% of carrier invoices contain errors.</strong> Manual keying
            runs a 1-4% field error rate. FreightPipe extracts structured data from
            freight documents and cross-checks them automatically. No TMS required.
          </p>
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
              <div className={styles.pricingPrice}>Contact us</div>
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
