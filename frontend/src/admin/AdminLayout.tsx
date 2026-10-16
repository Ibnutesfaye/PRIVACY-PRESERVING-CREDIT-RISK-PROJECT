import { useEffect, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  Activity, BarChart3, Bell, BrainCircuit, ChevronLeft, FileChartColumn,
  Gauge, HeartPulse, KeyRound, LayoutDashboard, LockKeyhole, LogOut, Menu,
  Building2, ClipboardList, House, Microscope, Moon, Search, Settings, ShieldAlert, ShieldCheck, Sun, Users, X,
} from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { API_URL } from './api'

type NavItem = { label: string; path: string; icon: LucideIcon; permission?: string }
const navigation: Array<{ label: string; items: NavItem[] }> = [
  { label: 'Monitor', items: [
    { label: 'Overview', path: '/admin', icon: LayoutDashboard, permission: 'dashboard.read' },
    { label: 'Risk Assessments', path: '/admin/predictions', icon: Activity, permission: 'predictions.read' },
    { label: 'Privacy Monitor', path: '/admin/privacy', icon: ShieldCheck, permission: 'privacy.read' },
    { label: 'Privacy & OpenFHE', path: '/admin/fhe', icon: Gauge, permission: 'fhe.read' },
  ] },
  { label: 'Credit Operations', items: [
    { label: 'Credit Applications', path: '/admin/applications', icon: ClipboardList, permission: 'applications.read' },
    { label: 'Organizations', path: '/admin/organizations', icon: Building2, permission: 'organizations.read' },
  ] },
  { label: 'Intelligence', items: [
    { label: 'Model Performance', path: '/admin/models', icon: BrainCircuit, permission: 'model.read' },
    { label: 'Model Versions', path: '/admin/model-versions', icon: Microscope, permission: 'model.read' },
    { label: 'Benchmarks', path: '/admin/benchmarks', icon: BarChart3, permission: 'fhe.benchmark' },
  ] },
  { label: 'Administration', items: [
    { label: 'Users', path: '/admin/users', icon: Users, permission: 'users.read' },
    { label: 'Roles & Permissions', path: '/admin/roles', icon: KeyRound, permission: 'roles.read' },
    { label: 'Audit Logs', path: '/admin/audit-logs', icon: FileChartColumn, permission: 'audit.read' },
    { label: 'Security Events', path: '/admin/security-events', icon: ShieldAlert, permission: 'security.read' },
    { label: 'Reports', path: '/admin/reports', icon: FileChartColumn, permission: 'reports.export' },
    { label: 'System Health', path: '/admin/system-health', icon: HeartPulse, permission: 'dashboard.read' },
    { label: 'Settings', path: '/admin/settings', icon: Settings, permission: 'settings.read' },
  ] },
]

const titles: Record<string, string> = {
  '/admin': 'Risk Management Dashboard', '/admin/predictions': 'Risk Assessments', '/admin/privacy': 'Privacy Monitor',
  '/admin/fhe': 'Privacy & OpenFHE', '/admin/models': 'Model Performance', '/admin/model-versions': 'Model Versions',
  '/admin/benchmarks': 'Benchmarks', '/admin/users': 'Admin Users', '/admin/roles': 'Roles & Permissions',
  '/admin/audit-logs': 'Audit Logs', '/admin/security-events': 'Security Events', '/admin/reports': 'Reports',
  '/admin/system-health': 'System Health', '/admin/settings': 'Settings',
  '/admin/applications': 'Credit Applications', '/admin/organizations': 'Organizations & Branches',
}

export function AdminLayout() {
  const { admin, accessToken, hasPermission, logout } = useAuth()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [notificationsOpen,setNotificationsOpen]=useState(false)
  const [notifications,setNotifications]=useState<Array<{id:string;title:string;message:string;severity:string}>>([])
  const [theme, setTheme] = useState(() => localStorage.getItem('cipherscore.theme') ?? 'dark')

  useEffect(() => {
    document.documentElement.dataset.adminTheme = theme
    localStorage.setItem('cipherscore.theme', theme)
  }, [theme])
  useEffect(() => setMobileOpen(false), [location.pathname])

  const initials = admin?.full_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
  async function toggleNotifications(){const next=!notificationsOpen;setNotificationsOpen(next);if(next){const response=await fetch(`${API_URL}/api/admin/notifications`,{headers:{Authorization:`Bearer ${accessToken}`}});if(response.ok)setNotifications((await response.json()).items)}}
  return <div className={`admin-shell ${collapsed ? 'is-collapsed' : ''}`}>
    <button className={`mobile-backdrop ${mobileOpen ? 'visible' : ''}`} onClick={() => setMobileOpen(false)} aria-label="Close navigation" />
    <aside className={`admin-sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-brand"><span className="brand-glyph">P</span><span className="brand-copy"><strong>Secure Credit Risk</strong><small>Administration</small></span><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={19} /></button></div>
      <nav aria-label="Admin navigation">
        {navigation.map((group) => {
          const visible = group.items.filter((item) => hasPermission(item.permission))
          if (!visible.length) return null
          return <div className="nav-group" key={group.label}><p>{group.label}</p>{visible.map((item) => <NavLink key={item.path} to={item.path} end={item.path === '/admin'} title={collapsed ? item.label : undefined}><item.icon size={18} /><span>{item.label}</span></NavLink>)}</div>
        })}
      </nav>
      <NavLink className="customer-site-link" to="/" title={collapsed ? 'Customer Site' : undefined}><House size={18} /><span>Customer Site</span></NavLink>
      <div className="sidebar-privacy"><LockKeyhole size={17} /><span><strong>Privacy-safe view</strong><small>No raw financial features</small></span></div>
      <button className="collapse-button" onClick={() => setCollapsed((value) => !value)}><ChevronLeft size={17} /><span>Collapse sidebar</span></button>
    </aside>
    <div className="admin-main">
      <header className="admin-topbar">
        <div className="topbar-title"><button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={20} /></button><div><p>Operations Console</p><h1>{titles[location.pathname] ?? 'Administration'}</h1></div></div>
        <div className="topbar-actions">
          <label className="global-search"><Search size={16} /><input aria-label="Global search" placeholder="Search console" /></label>
          <div className="system-chip"><span />All systems operational</div>
          <button className="icon-button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Use ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
          <div className="profile-wrap"><button className="icon-button notification-button" aria-label="Notifications" onClick={()=>void toggleNotifications()}><Bell size={18} />{notifications.length>0&&<span />}</button>{notificationsOpen&&<div className="profile-menu notification-menu"><p>Notifications</p>{notifications.length?notifications.slice(0,6).map(item=><div key={item.id}><strong>{item.title}</strong><small>{item.message}</small></div>):<div><small>No notifications recorded.</small></div>}</div>}</div>
          <div className="profile-wrap"><button className="profile-button" onClick={() => setProfileOpen((value) => !value)} aria-expanded={profileOpen}><span>{initials}</span><div><strong>{admin?.full_name}</strong><small>{admin?.roles[0]?.replaceAll('_', ' ')}</small></div></button>{profileOpen && <div className="profile-menu"><p>{admin?.email}</p><NavLink to="/admin/profile">Profile & session</NavLink><button onClick={() => void logout()}><LogOut size={15} />Sign out</button></div>}</div>
        </div>
      </header>
      <main className="admin-content"><Outlet /></main>
    </div>
  </div>
}
