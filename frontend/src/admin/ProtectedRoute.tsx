import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { admin, initializing } = useAuth()
  const location = useLocation()
  if (initializing) return <div className="admin-route-loader" role="status"><span />Verifying secure session…</div>
  if (!admin) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />
  return children
}

export function PermissionGuard({ permission, children }: { permission: string; children: ReactNode }) {
  const { hasPermission } = useAuth()
  return hasPermission(permission) ? children : null
}
