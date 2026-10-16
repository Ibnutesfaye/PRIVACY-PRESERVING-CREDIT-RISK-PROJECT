import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Root from '../Root'

const session = {
  access_token: 'access-token', refresh_token: 'refresh-token', token_type: 'bearer',
  access_expires_at: '2099-08-05T12:15:00Z', refresh_expires_at: '2099-08-12T12:00:00Z',
  admin: {
    id: 'admin-id', email: 'admin@example.com', full_name: 'Ada Administrator',
    roles: ['super_admin'], permissions: ['dashboard.read', 'privacy.read', 'users.read'],
  },
}

const dashboardPayloads: Record<string, unknown> = {
  summary: { operational_predictions:{total:0,today:0,successful_fhe:0,failed_fhe:0,source:'not_collected_until_phase_5'}, measured_research:{evaluated_samples:6484,accuracy:.832,precision:.707,recall:.396,f1:.508,roc_auc:.831,normal_inference_ms:.617,fhe_total_latency_ms:2343.7,accuracy_difference:0,source:'measured_test_set_benchmark'}, system:{active_model:'logistic-regression-baseline-v1',fhe_scheme:'CKKS',polynomial_degree:7,open_security_events:0} },
  activity: { series:[], recent:[], prediction_activity_available:false },
  'risk-distribution': { source:'measured_test_set_predictions',total:6484,items:[{risk_class:'LOW RISK',count:5689},{risk_class:'HIGH RISK',count:795}] },
  'fhe-performance': { source:'measured_openfhe_test_set_benchmark',scheme:'CKKS',ring_dimension:32768,polynomial_degree:7,stages:[],total_latency_ms:2343.7,ciphertext_size_bytes:29371223,mean_absolute_error:4.7e-12 },
  privacy: { compliance_status:'pilot_controls_verified',encrypted_test_samples:6484,secret_key_exposure_incidents:0,plaintext_storage_incidents:0,checks:[],note:'Pilot controls monitored.' },
}

describe('admin routing and authentication', () => {
  beforeEach(() => {
    sessionStorage.clear()
    window.history.pushState({}, '', '/admin')
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('redirects an unauthenticated administrator to login', async () => {
    render(<Root />)
    expect(await screen.findByRole('heading', { name: 'Sign in to the console' })).toBeInTheDocument()
  })

  it('links the customer site and administrator login without bypassing authentication', async () => {
    window.history.pushState({}, '', '/')
    render(<Root />)
    const adminLink = screen.getByRole('link', { name: 'Admin Login' })
    expect(adminLink).toHaveAttribute('href', '/admin/login')
    await userEvent.click(adminLink)
    expect(await screen.findByRole('heading', { name: 'Sign in to the console' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Customer Site' })).toHaveAttribute('href', '/')
  })

  it('authenticates and displays only permitted navigation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async (input: string) => {
      if (input.endsWith('/auth/login')) return { ok: true, json: async () => session }
      const key = input.split('/').at(-1) ?? ''
      return { ok: true, json: async () => dashboardPayloads[key] }
    }))
    window.history.pushState({}, '', '/admin/login')
    render(<Root />)
    // Direct input events keep this integration test deterministic on slower
    // Windows CI hosts; user-event keyboard behavior is covered elsewhere.
    fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'admin@example.com' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'Strong-Admin-Password-2026!' } })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(await screen.findByRole(
      'heading',
      { name: 'Credit risk and encrypted inference overview.' },
      { timeout: 10_000 },
    )).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Privacy Monitor' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Customer Site' })).toHaveAttribute('href', '/')
    expect(screen.queryByRole('link', { name: 'Audit Logs' })).not.toBeInTheDocument()
    await waitFor(() => expect(sessionStorage.getItem('cipherscore.admin.refresh')).toBe('refresh-token'))
  }, 15_000)
})
