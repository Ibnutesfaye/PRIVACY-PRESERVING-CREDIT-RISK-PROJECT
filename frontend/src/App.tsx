import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import './App.css'

type FormValues = {
  person_age: number
  person_income: number
  person_emp_length: number
  loan_amnt: number
  loan_int_rate: number
  loan_percent_income: number
  cb_person_cred_hist_length: number
}

type PredictionResult = {
  risk_score: number
  raw_fhe_score: number
  prediction: 'LOW RISK' | 'HIGH RISK'
  timing: {
    key_generation_ms: number
    encryption_ms: number
    evaluation_ms: number
    decryption_ms: number
    total_latency_ms: number
  }
  privacy: {
    scheme: string
    encrypted_inference: boolean
    evaluator_received_plaintext_features: boolean
    trusted_gateway_received_plaintext_features: boolean
    secret_key_available_to_evaluator: boolean
    architecture_note: string
  }
}

const initialValues: FormValues = {
  person_age: 28,
  person_income: 45000,
  person_emp_length: 5,
  loan_amnt: 10000,
  loan_int_rate: 11.5,
  loan_percent_income: 0.22,
  cb_person_cred_hist_length: 4,
}

const fields: Array<{ key: keyof FormValues; label: string; hint: string; step?: number }> = [
  { key: 'person_age', label: 'Age', hint: 'Years' },
  { key: 'person_income', label: 'Annual income', hint: 'Currency units' },
  { key: 'person_emp_length', label: 'Employment length', hint: 'Years', step: 0.1 },
  { key: 'loan_amnt', label: 'Loan amount', hint: 'Requested principal' },
  { key: 'loan_int_rate', label: 'Interest rate', hint: 'Percent', step: 0.01 },
  { key: 'loan_percent_income', label: 'Loan / income', hint: 'Between 0 and 1', step: 0.01 },
  { key: 'cb_person_cred_hist_length', label: 'Credit history', hint: 'Years', step: 0.1 },
]

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8001'

function App() {
  const [values, setValues] = useState(initialValues)
  const [result, setResult] = useState<PredictionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.detail ?? `Prediction failed (${response.status})`)
      }
      setResult(await response.json())
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Privacy-Preserving Credit Risk home">
          <span className="brand-mark">P</span>
          <span>Privacy-Preserving Credit Risk</span>
        </a>
        <div className="topbar-actions">
          <div className="status-pill"><span /> OpenFHE CKKS ready</div>
          <Link className="admin-login-link" to="/admin/login">Admin Login</Link>
        </div>
      </header>

      <section className="hero" id="top">
        <p className="eyebrow">Privacy-preserving credit intelligence</p>
        <h1>Credit risk assessment,<br /><em>without exposing the computation.</em></h1>
        <p className="lede">Secure credit-risk decision support with privacy-preserving OpenFHE CKKS encrypted inference.</p>
      </section>

      <section className="workspace">
        <form className="card form-card" onSubmit={submit}>
          <div className="card-heading">
            <div>
              <p className="section-number">01 / APPLICANT PROFILE</p>
              <h2>Assessment inputs</h2>
            </div>
            <span className="lock" aria-hidden="true">⌁</span>
          </div>
          <div className="form-grid">
            {fields.map((field) => (
              <label key={field.key} className="field">
                <span>{field.label}</span>
                <input
                  type="number"
                  required
                  step={field.step ?? 1}
                  value={values[field.key]}
                  onChange={(event) => setValues({ ...values, [field.key]: Number(event.target.value) })}
                />
                <small>{field.hint}</small>
              </label>
            ))}
          </div>
          <button className="predict-button" type="submit" disabled={loading}>
            <span>{loading ? 'Evaluating encrypted model…' : 'Assess risk securely'}</span>
            <span aria-hidden="true">→</span>
          </button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>

        <aside className="card result-card" aria-live="polite">
          <p className="section-number">02 / ENCRYPTED RESULT</p>
          {!result ? (
            <div className="empty-state">
              <div className="orb">◎</div>
              <h2>{loading ? 'OpenFHE is computing' : 'Awaiting assessment'}</h2>
              <p>{loading ? 'Generating keys, encrypting features, and evaluating the polynomial model.' : 'Submit a customer profile to run the encrypted inference pipeline.'}</p>
            </div>
          ) : (
            <div className="result-content">
              <div className={`risk-label ${result.prediction === 'HIGH RISK' ? 'high' : 'low'}`}>{result.prediction}</div>
              <div className="score-row">
                <strong>{(result.risk_score * 100).toFixed(1)}</strong><span>%</span>
              </div>
              <p className="score-caption">Predicted risk score · decision support only</p>
              <div className="meter"><span style={{ width: `${result.risk_score * 100}%` }} /></div>
              <div className="timing-grid">
                <div><span>Encrypt</span><strong>{result.timing.encryption_ms.toFixed(1)} ms</strong></div>
                <div><span>Evaluate</span><strong>{result.timing.evaluation_ms.toFixed(1)} ms</strong></div>
                <div><span>Decrypt</span><strong>{result.timing.decryption_ms.toFixed(1)} ms</strong></div>
                <div><span>Total</span><strong>{result.timing.total_latency_ms.toFixed(1)} ms</strong></div>
              </div>
              <ul className="privacy-list">
                <li><span>✓</span> Features encrypted with CKKS</li>
                <li><span>✓</span> Evaluator received ciphertext only</li>
                <li><span>✓</span> Secret key withheld from evaluator</li>
              </ul>
            </div>
          )}
        </aside>
      </section>

      <section className="boundary-note">
        <span>Pilot environment boundary</span>
        <p>This browser assessment uses the trusted compatibility gateway for preprocessing. Institutional encrypted inference uses the trusted local client so the evaluator receives ciphertext only. Model output supports, but does not replace, an authorized human lending decision.</p>
      </section>

      <footer>Privacy-Preserving Credit Risk Decision Support System · Encrypted inference using OpenFHE</footer>
    </main>
  )
}

export default App
