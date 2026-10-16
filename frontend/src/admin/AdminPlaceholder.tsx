import type { LucideIcon } from 'lucide-react'
import { ArrowUpRight, LockKeyhole, ShieldCheck } from 'lucide-react'

export function AdminOverview() {
  return <div className="admin-page overview-intro">
    <div className="page-heading"><div><p className="admin-kicker">Privacy-preserving operations</p><h2>Welcome to the administration console.</h2><p>Authentication, authorization, role-aware navigation, and privacy-safe operational views are active.</p></div><div className="phase-badge"><span>Pilot Environment</span>Access controls active</div></div>
    <section className="foundation-grid">
      <article><ShieldCheck /><p>Access control</p><h3>Database-backed permissions</h3><span>Navigation and backend operations resolve authorization from assigned roles.</span></article>
      <article><LockKeyhole /><p>Privacy boundary</p><h3>Sensitive features excluded</h3><span>The admin surface is designed around operational metadata, never raw customer inputs.</span></article>
      <article><ArrowUpRight /><p>Operational evidence</p><h3>Measured overview metrics</h3><span>Summary APIs and evidence-based charts display recorded values without fabricated operational statistics.</span></article>
    </section>
    <section className="model-disclaimer"><strong>Model Validation Notice</strong><p>The bundled model is intended for controlled pilot validation. Institution-specific historical data, calibration, fairness assessment, security approval, and formal validation are required before production lending use. Model assessments must not replace authorized human decisions.</p></section>
  </div>
}

export function AdminPlaceholder({ title, description, icon: Icon }: { title: string; description: string; icon: LucideIcon }) {
  return <div className="admin-page"><div className="page-heading"><div><p className="admin-kicker">Protected administration area</p><h2>{title}</h2><p>{description}</p></div></div><div className="placeholder-panel"><Icon size={28} /><h3>No operational records available</h3><p>This area will display authorized, recorded data when it becomes available. No simulated statistics are presented as operational results.</p></div></div>
}
