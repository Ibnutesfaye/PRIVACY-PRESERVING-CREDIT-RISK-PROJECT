import { Activity, BarChart3, BrainCircuit, FileChartColumn, Gauge, HeartPulse, KeyRound, Microscope, Settings, ShieldAlert, ShieldCheck, Users } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import CustomerPrediction from './App'
import { AdminLayout } from './admin/AdminLayout'
import { AdminLogin } from './admin/AdminLogin'
import { AdminPlaceholder } from './admin/AdminPlaceholder'
import { AuthProvider } from './admin/AuthContext'
import { ProtectedRoute } from './admin/ProtectedRoute'
import './admin/admin.css'
import './admin/admin-extra.css'

const placeholders = [
  ['predictions', 'Predictions', 'Privacy-safe encrypted prediction metadata and processing status.', Activity],
  ['privacy', 'Privacy Monitor', 'Implemented, simulated, and planned privacy controls clearly distinguished.', ShieldCheck],
  ['fhe', 'FHE Performance', 'Measured OpenFHE CKKS configuration, timing, and approximation quality.', Gauge],
  ['models', 'ML Model', 'Validated model metrics, coefficients, artifacts, and limitations.', BrainCircuit],
  ['model-versions', 'Model Versions', 'Governed model approval, activation, archive, and rollback workflows.', Microscope],
  ['benchmarks', 'Benchmarks', 'Controlled conventional and encrypted model performance evaluation.', BarChart3],
  ['users', 'Admin Users', 'Administrator accounts, status, roles, and session controls.', Users],
  ['roles', 'Roles & Permissions', 'Explicit permission matrix and role governance.', KeyRound],
  ['audit-logs', 'Audit Logs', 'Tamper-evident records of sensitive administrative activity.', FileChartColumn],
  ['security-events', 'Security Events', 'Triage and resolution of authentication and integrity events.', ShieldAlert],
  ['reports', 'Reports', 'Privacy-safe operational and model-performance exports.', FileChartColumn],
  ['system-health', 'System Health', 'Polled service health, latency, uptime, and recent incidents.', HeartPulse],
  ['settings', 'Settings', 'Validated non-secret administrative configuration.', Settings],
] as const

const DashboardOverview = lazy(() => import('./admin/DashboardOverview').then((module) => ({ default: module.DashboardOverview })))
const PredictionsPage = lazy(() => import('./admin/PredictionsPage').then((module) => ({ default: module.PredictionsPage })))
const FhePage = lazy(() => import('./admin/FhePrivacyPages').then((module) => ({ default: module.FhePage })))
const PrivacyPage = lazy(() => import('./admin/FhePrivacyPages').then((module) => ({ default: module.PrivacyPage })))
const ModelMetricsPage=lazy(()=>import('./admin/ModelsPage').then(m=>({default:m.ModelMetricsPage})))
const ModelVersionsPage=lazy(()=>import('./admin/ModelsPage').then(m=>({default:m.ModelVersionsPage})))
const management=(name:string)=>lazy(()=>import('./admin/ManagementPages').then((m:any)=>({default:m[name]})))
const UsersPage=management('UsersPage'),RolesPage=management('RolesPage'),AuditPage=management('AuditPage'),SecurityPage=management('SecurityPage'),HealthPage=management('HealthPage'),ReportsPage=management('ReportsPage'),SettingsPage=management('SettingsPage')
const enterprise=(name:string)=>lazy(()=>import('./admin/EnterprisePages').then((m:any)=>({default:m[name]})))
const ApplicationsPage=enterprise('ApplicationsPage'),OrganizationsPage=enterprise('OrganizationsPage')

export default function Root() {
  return <BrowserRouter><AuthProvider><Routes>
    <Route path="/" element={<CustomerPrediction />} />
    <Route path="/admin/login" element={<AdminLogin />} />
    <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
      <Route index element={<Suspense fallback={<div className="dashboard-skeleton" role="status" aria-label="Loading overview"><span /><span /><span /></div>}><DashboardOverview /></Suspense>} />
      <Route path="predictions" element={<Suspense fallback={<div className="dashboard-skeleton" role="status" aria-label="Loading predictions"><span /><span /><span /></div>}><PredictionsPage /></Suspense>} />
      <Route path="privacy" element={<Suspense fallback={<div className="dashboard-skeleton"><span/><span/></div>}><PrivacyPage/></Suspense>} />
      <Route path="fhe" element={<Suspense fallback={<div className="dashboard-skeleton"><span/><span/></div>}><FhePage/></Suspense>} />
      <Route path="models" element={<Suspense fallback={<div className="dashboard-skeleton"><span/><span/></div>}><ModelMetricsPage/></Suspense>}/>
      <Route path="model-versions" element={<Suspense fallback={<div className="dashboard-skeleton"><span/><span/></div>}><ModelVersionsPage/></Suspense>}/>
      <Route path="applications" element={<Suspense fallback={<div className="dashboard-skeleton"><span/><span/></div>}><ApplicationsPage/></Suspense>}/>
      <Route path="organizations" element={<Suspense fallback={<div className="dashboard-skeleton"><span/><span/></div>}><OrganizationsPage/></Suspense>}/>
      <Route path="users" element={<Suspense><UsersPage/></Suspense>}/><Route path="roles" element={<Suspense><RolesPage/></Suspense>}/><Route path="audit-logs" element={<Suspense><AuditPage/></Suspense>}/><Route path="security-events" element={<Suspense><SecurityPage/></Suspense>}/><Route path="reports" element={<Suspense><ReportsPage/></Suspense>}/><Route path="system-health" element={<Suspense><HealthPage/></Suspense>}/><Route path="settings" element={<Suspense><SettingsPage/></Suspense>}/>
      {placeholders.filter(([path])=>!['predictions','privacy','fhe','models','model-versions','users','roles','audit-logs','security-events','reports','system-health','settings'].includes(path)).map(([path, title, description, icon]) => <Route key={path} path={path} element={<AdminPlaceholder title={title} description={description} icon={icon} />} />)}
      <Route path="profile" element={<AdminPlaceholder title="Profile & Session" description="Current administrator identity and secure session details." icon={Users} />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AuthProvider></BrowserRouter>
}
