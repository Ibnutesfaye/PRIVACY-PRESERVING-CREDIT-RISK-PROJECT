import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, LockKeyhole, ShieldCheck } from 'lucide-react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AdminRequestError } from './api'
import { useAuth } from './AuthContext'

export function AdminLogin() {
  const { admin, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  if (admin) return <Navigate to="/admin" replace />

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await login(email, password)
      const state = location.state as { from?: string } | null
      navigate(state?.from?.startsWith('/admin') ? state.from : '/admin', { replace: true })
    } catch (caught) {
      setError(caught instanceof AdminRequestError ? caught.message : 'Unable to sign in right now.')
    } finally {
      setSubmitting(false)
    }
  }

  return <main className="login-page">
    <section className="login-brand-panel">
      <a href="/" className="admin-wordmark"><span>P</span>Privacy-Preserving Credit Risk</a>
      <div className="login-message">
        <p className="admin-kicker">Decision Support System</p>
        <h1>Secure credit-risk assessment,<br />with encrypted inference.</h1>
        <p>Monitor risk assessments, model governance, privacy controls, and operational integrity without exposing raw financial features in the administration console.</p>
      </div>
      <div className="trust-note"><ShieldCheck size={18} /><span><strong>Privacy boundary enforced</strong>Raw financial inputs and secret-key material are excluded.</span></div>
    </section>
    <section className="login-form-panel">
      <form className="login-card" onSubmit={submit}>
        <div className="login-icon"><LockKeyhole size={22} /></div>
        <p className="admin-kicker">Authorized access only</p>
        <h2>Sign in to the console</h2>
        <p className="form-intro">Use your authorized administrator account.</p>
        <label>Email address<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="admin@organization.com" /></label>
        <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <div className="login-error" role="alert">{error}</div>}
        <button type="submit" disabled={submitting}><span>{submitting ? 'Verifying…' : 'Sign In'}</span><ArrowRight size={17} /></button>
        <p className="login-help">Repeated failures trigger account lockout and a security event.</p>
        <Link className="customer-return-link" to="/">Back to Customer Site</Link>
      </form>
    </section>
  </main>
}
