import { useState } from "react";
import { Link } from "react-router-dom";
import styles from "./Docs.module.css";

type Section = "quickstart" | "auth" | "api" | "examples";

const SECTIONS: { key: Section; label: string }[] = [
  { key: "quickstart", label: "Quickstart" },
  { key: "auth", label: "Authentication" },
  { key: "api", label: "API Reference" },
  { key: "examples", label: "Examples" },
];

const ENDPOINTS = [
  { method: "POST", path: "/v1/auth/register", desc: "Create a new account" },
  { method: "POST", path: "/v1/auth/login", desc: "Sign in and receive JWT" },
  { method: "GET", path: "/v1/auth/me", desc: "Get current user profile" },
  { method: "PUT", path: "/v1/auth/profile", desc: "Update user profile" },
  { method: "POST", path: "/v1/documents", desc: "Submit a PDF for processing (async)" },
  { method: "GET", path: "/v1/jobs", desc: "List all jobs (paginated)" },
  { method: "GET", path: "/v1/jobs/{job_id}", desc: "Get job status" },
  { method: "GET", path: "/v1/jobs/{job_id}/result", desc: "Get structured extraction result" },
  { method: "GET", path: "/v1/documents/{document_id}/pdf", desc: "Get original PDF" },
  { method: "GET", path: "/v1/review-queue", desc: "List pending review items" },
  { method: "GET", path: "/v1/review-queue/{item_id}", desc: "Get review item detail" },
  { method: "POST", path: "/v1/review-queue/{item_id}/resolve", desc: "Resolve a review item" },
  { method: "GET", path: "/v1/analytics/usage", desc: "Usage and accuracy metrics" },
  { method: "GET", path: "/v1/api-keys", desc: "List API keys (masked)" },
  { method: "POST", path: "/v1/api-keys", desc: "Create a new API key" },
  { method: "DELETE", path: "/v1/api-keys/{key_id}", desc: "Revoke an API key" },
  { method: "GET", path: "/v1/settings/webhook", desc: "Get account webhook config" },
  { method: "PUT", path: "/v1/settings/webhook", desc: "Update account webhook config" },
  { method: "POST", path: "/v1/webhooks/test", desc: "Test a webhook URL" },
  { method: "GET", path: "/v1/health", desc: "Liveness check (no auth)" },
];

export default function Docs() {
  const [activeSection, setActiveSection] = useState<Section>("quickstart");

  return (
    <div className={styles.docs}>
      <nav className={styles.docsNav}>
        <div className={styles.docsNavHeader}>
          <Link to="/" className={styles.docsNavLogo}>
            <span className={styles.docsNavLogoAccent}>Freight</span>Pipe
          </Link>
          <span className={styles.docsNavTitle}>Documentation</span>
        </div>
        <div className={styles.docsNavLinks}>
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              type="button"
              className={styles.docsNavLink}
              data-active={activeSection === s.key}
              onClick={() => setActiveSection(s.key)}
            >
              {s.label}
            </button>
          ))}
          <Link to="/login" className={styles.docsNavLink}>
            Back to App
          </Link>
        </div>
      </nav>

      <main className={styles.docsContent}>
        {activeSection === "quickstart" && (
          <section>
            <h1 className={styles.docsH1}>Quickstart</h1>
            <p className={styles.docsP}>
              FreightPipe turns freight PDFs (rate confirmations, BOLs, PODs, invoices)
              into structured JSON. Extracted fields carry confidence scores, and
              low-confidence values are routed to a review queue.
            </p>

            <h2 className={styles.docsH2}>1. Create an account</h2>
            <p className={styles.docsP}>
              Register at{" "}
              <code className={styles.docsCode}>/register</code> with your email,
              company name, and password. You will be logged in automatically.
            </p>

            <h2 className={styles.docsH2}>2. Get your API key</h2>
            <p className={styles.docsP}>
              Navigate to <strong>Settings</strong> and create an API key under the
              API Keys tab. The key is shown once &mdash; copy it immediately.
            </p>

            <h2 className={styles.docsH2}>3. Submit a document</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>curl</div>
              <pre>{`curl -X POST https://api.freightpipe.dev/v1/documents \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -F "file=@invoice.pdf"`}</pre>
            </div>
            <p className={styles.docsP}>
              The response returns a <code className={styles.docsCode}>job_id</code> with
              status <code className={styles.docsCode}>queued</code>. Processing is
              asynchronous.
            </p>

            <h2 className={styles.docsH2}>4. Poll for results</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>curl</div>
              <pre>{`curl https://api.freightpipe.dev/v1/jobs/{job_id}/result \\
  -H "Authorization: Bearer YOUR_TOKEN"`}</pre>
            </div>
            <p className={styles.docsP}>
              Once status reaches <code className={styles.docsCode}>complete</code>,
              the response contains extracted documents with fields, confidence scores,
              and 3-way match results.
            </p>

            <h2 className={styles.docsH2}>5. Review flagged items</h2>
            <p className={styles.docsP}>
              Items with low confidence or discrepancies are routed to the review queue.
              Resolve them via the dashboard or the API.
            </p>
          </section>
        )}

        {activeSection === "auth" && (
          <section>
            <h1 className={styles.docsH1}>Authentication</h1>
            <p className={styles.docsP}>
              FreightPipe supports two authentication methods:
            </p>

            <h2 className={styles.docsH2}>JWT Bearer Token</h2>
            <p className={styles.docsP}>
              Obtain a token via <code className={styles.docsCode}>POST /v1/auth/login</code>.
              Include it in requests as:
            </p>
            <div className={styles.docsCodeBlock}>
              <pre>{`Authorization: Bearer eyJhbGciOiJIUzI1NiIs...`}</pre>
            </div>
            <p className={styles.docsP}>
              Tokens expire after 24 hours. Use <code className={styles.docsCode}>/v1/auth/me</code> to
              verify a token is still valid.
            </p>

            <h2 className={styles.docsH2}>API Key</h2>
            <p className={styles.docsP}>
              For programmatic access, use an API key created in Settings. Include it as:
            </p>
            <div className={styles.docsCodeBlock}>
              <pre>{`X-Api-Key: fp_live_a1b2c3d4e5f6...`}</pre>
            </div>
            <p className={styles.docsP}>
              API keys do not expire but can be revoked at any time. All endpoints
              accept either method.
            </p>

            <h2 className={styles.docsH2}>Registration</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>POST /v1/auth/register</div>
              <pre>{`{
  "email": "you@company.com",
  "phone": "+15551234567",
  "company_name": "Acme Freight",
  "password": "securepassword"
}`}</pre>
            </div>
            <p className={styles.docsP}>
              Returns a JWT token and user profile. No email verification required.
            </p>

            <h2 className={styles.docsH2}>Login</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>POST /v1/auth/login</div>
              <pre>{`{
  "email": "you@company.com",
  "password": "securepassword"
}`}</pre>
            </div>
          </section>
        )}

        {activeSection === "api" && (
          <section>
            <h1 className={styles.docsH1}>API Reference</h1>
            <p className={styles.docsP}>
              Base URL: <code className={styles.docsCode}>https://api.freightpipe.dev</code>
            </p>
            <p className={styles.docsP}>
              All endpoints require authentication unless noted. Responses use standard
              HTTP status codes. Errors return an envelope:
            </p>
            <div className={styles.docsCodeBlock}>
              <pre>{`{
  "error": {
    "code": "invalid_pdf",
    "message": "Could not read file as PDF",
    "request_id": "req_abc123"
  }
}`}</pre>
            </div>

            <h2 className={styles.docsH2}>Endpoints</h2>
            <div className={styles.endpointTable}>
              <div className={styles.endpointHeader}>
                <span>Method</span>
                <span>Path</span>
                <span>Description</span>
              </div>
              {ENDPOINTS.map((ep) => (
                <div key={ep.path + ep.method} className={styles.endpointRow}>
                  <span className={styles.method} data-method={ep.method}>
                    {ep.method}
                  </span>
                  <span className={styles.path} data-mono>{ep.path}</span>
                  <span className={styles.desc}>{ep.desc}</span>
                </div>
              ))}
            </div>

            <h2 className={styles.docsH2}>Job Status Values</h2>
            <div className={styles.enumList}>
              <code className={styles.docsCode}>queued</code>
              <code className={styles.docsCode}>classifying</code>
              <code className={styles.docsCode}>splitting</code>
              <code className={styles.docsCode}>extracting</code>
              <code className={styles.docsCode}>normalizing</code>
              <code className={styles.docsCode}>validating</code>
              <code className={styles.docsCode}>matching</code>
              <code className={styles.docsCode}>scoring</code>
              <code className={styles.docsCode}>needs_review</code>
              <code className={styles.docsCode}>complete</code>
              <code className={styles.docsCode}>failed</code>
              <code className={styles.docsCode}>needs_llm_capacity</code>
            </div>

            <h2 className={styles.docsH2}>Review Reasons</h2>
            <div className={styles.enumList}>
              <code className={styles.docsCode}>low_confidence</code>
              <code className={styles.docsCode}>discrepancy</code>
              <code className={styles.docsCode}>classification_failed</code>
              <code className={styles.docsCode}>needs_llm_capacity</code>
              <code className={styles.docsCode}>validation_failed</code>
            </div>

            <h2 className={styles.docsH2}>Pagination</h2>
            <p className={styles.docsP}>
              List endpoints use cursor-based pagination. Pass{" "}
              <code className={styles.docsCode}>cursor</code> from the previous
              response&apos;s <code className={styles.docsCode}>next_cursor</code> field.
              Default limit is 50, max 200.
            </p>

            <h2 className={styles.docsH2}>Rate Limits</h2>
            <p className={styles.docsP}>
              Free tier: 100 documents/month. Rate-limited requests return{" "}
              <code className={styles.docsCode}>429</code> with a{" "}
              <code className={styles.docsCode}>Retry-After</code> header.
            </p>
          </section>
        )}

        {activeSection === "examples" && (
          <section>
            <h1 className={styles.docsH1}>Examples</h1>

            <h2 className={styles.docsH2}>Python</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>Python</div>
              <pre>{`import requests

API_BASE = "https://api.freightpipe.dev/v1"
TOKEN = "your_jwt_token"

headers = {"Authorization": f"Bearer {TOKEN}"}

# Submit a document
with open("invoice.pdf", "rb") as f:
    res = requests.post(
        f"{API_BASE}/documents",
        headers=headers,
        files={"file": f},
    )
    job = res.json()
    print(f"Job created: {job['job_id']}")

# Poll for result
import time
while True:
    res = requests.get(
        f"{API_BASE}/jobs/{job['job_id']}/result",
        headers=headers,
    )
    if res.status_code == 200:
        result = res.json()
        for doc in result["documents"]:
            print(f"  {doc['doc_type']}: {len(doc['fields'])} fields")
        break
    time.sleep(5)`}</pre>
            </div>

            <h2 className={styles.docsH2}>JavaScript</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>JavaScript</div>
              <pre>{`const API_BASE = "https://api.freightpipe.dev/v1";
const TOKEN = "your_jwt_token";

async function submitAndPoll(file) {
  // Submit
  const formData = new FormData();
  formData.append("file", file);

  const submitRes = await fetch(\`\${API_BASE}/documents\`, {
    method: "POST",
    headers: { Authorization: \`Bearer \${TOKEN}\` },
    body: formData,
  });
  const { job_id } = await submitRes.json();

  // Poll
  while (true) {
    const res = await fetch(\`\${API_BASE}/jobs/\${job_id}/result\`, {
      headers: { Authorization: \`Bearer \${TOKEN}\` },
    });
    if (res.ok) {
      return await res.json();
    }
    await new Promise((r) => setTimeout(r, 5000));
  }
}`}</pre>
            </div>

            <h2 className={styles.docsH2}>curl</h2>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>bash</div>
              <pre>{`# Submit a document
curl -X POST https://api.freightpipe.dev/v1/documents \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -F "file=@rate_confirmation.pdf"

# Check job status
curl https://api.freightpipe.dev/v1/jobs/{job_id} \\
  -H "Authorization: Bearer YOUR_TOKEN"

# Get result
curl https://api.freightpipe.dev/v1/jobs/{job_id}/result \\
  -H "Authorization: Bearer YOUR_TOKEN"

# List review items
curl https://api.freightpipe.dev/v1/review-queue?state=pending \\
  -H "Authorization: Bearer YOUR_TOKEN"`}</pre>
            </div>

            <h2 className={styles.docsH2}>Webhook Configuration</h2>
            <p className={styles.docsP}>
              Set a default webhook URL for your account:
            </p>
            <div className={styles.docsCodeBlock}>
              <div className={styles.docsCodeLabel}>curl</div>
              <pre>{`curl -X PUT https://api.freightpipe.dev/v1/settings/webhook \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"webhook_url": "https://your-app.com/hooks/freightpipe"}'`}</pre>
            </div>
            <p className={styles.docsP}>
              FreightPipe will POST to this URL on job completion, review needed, and
              failure events. Verify deliveries using the{" "}
              <code className={styles.docsCode}>X-FreightPipe-Signature</code> header.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
