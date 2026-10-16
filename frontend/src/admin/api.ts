import type { ApiError, TokenResponse } from './types'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8001'

export class AdminRequestError extends Error {
  status: number
  code: string

  constructor(message: string, status: number, code = 'REQUEST_FAILED') {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parseError(response: Response): Promise<AdminRequestError> {
  const payload = await response.json().catch(() => ({})) as ApiError
  return new AdminRequestError(
    payload.error?.message ?? payload.detail ?? 'The request could not be completed.',
    response.status,
    payload.error?.code,
  )
}

export async function loginRequest(email: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/api/admin/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) throw await parseError(response)
  return response.json() as Promise<TokenResponse>
}

export async function refreshRequest(refreshToken: string): Promise<TokenResponse> {
  const response = await fetch(`${API_URL}/api/admin/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) throw await parseError(response)
  return response.json() as Promise<TokenResponse>
}

export async function logoutRequest(accessToken: string, refreshToken: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/admin/auth/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) throw await parseError(response)
}
