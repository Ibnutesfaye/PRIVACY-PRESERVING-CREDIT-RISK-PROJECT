export type AdminIdentity = {
  id: string
  email: string
  full_name: string
  roles: string[]
  permissions: string[]
}

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  access_expires_at: string
  refresh_expires_at: string
  admin: AdminIdentity
}

export type ApiError = {
  success?: false
  error?: { code?: string; message?: string; request_id?: string }
  detail?: string
}
