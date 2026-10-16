import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, BrainCircuit, CheckCircle2, Clock3, Database, LockKeyhole, RefreshCw, ShieldCheck } from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { API_URL } from './api'
import { useAuth } from './AuthContext'

type DashboardData = {
  summary: {
    operational_predictions: { total:number; today:number; successful_fhe:number; failed_fhe:number; source:string }
    measured_research: { evaluated_samples:number; accuracy:number; precision:number; recall:number; f1:number; roc_auc:number; normal_inference_ms:number; fhe_total_latency_ms:number; accuracy_difference:number; source:string }
    system: { active_model:string; fhe_scheme:string; polynomial_degree:number; open_security_events:number }
  }
  activity: { series:Array<{date:string;admin_events:number}>; recent:Array<{id:string;timestamp:string;action:string;result:string;resource_type:string;actor_role:string|null}>; prediction_activity_available:boolean }
  risk: { source:string; total:number; items:Array<{risk_class:string;count:number}> }
  fhe: { source:string; scheme:string; ring_dimension:number; polynomial_degree:number; stages:Array<{stage:string;milliseconds:number}>; total_latency_ms:number; ciphertext_size_bytes:number; mean_absolute_error:number }
  privacy: { compliance_status:string; encrypted_test_samples:number; secret_key_exposure_incidents:number; plaintext_storage_incidents:number; checks:Array<{name:string;status:string}>; note:string }
}

function formatMs(value:number) { return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${value.toFixed(value < 1 ? 3 : 1)} ms` }
function percent(value:number) { return `${(value * 100).toFixed(1)}%` }
function actionLabel(action:string) { return action.replace('admin.', '').replaceAll('.', ' ').replaceAll('_', ' ') }

export function DashboardOverview() {
  const { accessToken } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const names = ['summary', 'activity', 'risk-distribution', 'fhe-performance', 'privacy'] as const
      const responses = await Promise.all(names.map((name) => fetch(`${API_URL}/api/admin/dashboard/${name}`, { headers: { Authorization: `Bearer ${accessToken}` } })))
      const failed = responses.find((response) => !response.ok)
      if (failed) throw new Error(`Dashboard request failed (${failed.status})`)
      const [summary, activity, risk, fhe, privacy] = await Promise.all(responses.map((response) => response.json()))
      setData({ summary, activity, risk, fhe, privacy })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Dashboard data is unavailable.')
    } finally { setLoading(false) }
  }, [accessToken])
  useEffect(() => { void load() }, [load])

  if (loading) return <div className="dashboard-skeleton" role="status" aria-label="Loading dashboard">{Array.from({length:8},(_,index)=><span key={index}/>)}</div>
  if (error || !data) return <div className="dashboard-error"><AlertTriangle/><h2>Overview unavailable</h2><p>{error}</p><button onClick={() => void load()}><RefreshCw size={15}/>Try again</button></div>

  const metrics = data.summary.measured_research
  const cards = [
    { label:'Validation samples', value:metrics.evaluated_samples.toLocaleString(), note:'Measured encrypted evaluation set', icon:Database },
    { label:'Model accuracy', value:percent(metrics.accuracy), note:'Normal and FHE classification', icon:BrainCircuit },
    { label:'F1 score', value:percent(metrics.f1), note:`Recall ${percent(metrics.recall)}`, icon:Activity },
    { label:'FHE pipeline', value:formatMs(metrics.fhe_total_latency_ms), note:'Measured packed batch', icon:Clock3 },
    { label:'Accuracy difference', value:percent(metrics.accuracy_difference), note:'FHE minus normal ML', icon:CheckCircle2 },
    { label:'Open security events', value:String(data.summary.system.open_security_events), note:'Recorded operational events', icon:ShieldCheck },
  ]
  return <div className="admin-page dashboard-page">
    <div className="dashboard-heading"><div><p className="admin-kicker">Risk Management Dashboard</p><h2>Credit risk and encrypted inference overview.</h2><p>Model-performance figures come from the measured 6,484-sample OpenFHE evaluation set. Operational counters use recorded application data only.</p></div><div className="model-chip"><span>Active model version</span><strong>{data.summary.system.active_model}</strong><small>{data.summary.system.fhe_scheme} · degree {data.summary.system.polynomial_degree}</small></div></div>
    <section className="metric-card-grid">{cards.map(({label,value,note,icon:Icon})=><article key={label}><div><p>{label}</p><strong>{value}</strong><span>{note}</span></div><Icon size={18}/></article>)}</section>
    <div className="data-provenance"><LockKeyhole size={15}/><p><strong>Data provenance:</strong> Metrics labeled measured come from saved model and OpenFHE benchmark artifacts. Operational prediction counters are currently <b>0 / not collected</b>, not estimated.</p></div>
    <section className="dashboard-grid">
      <article className="dashboard-card activity-chart"><header><div><h3>Administrative activity</h3><p>Audit events recorded during the last seven days</p></div><span className="source-badge">Database</span></header><div className="chart-body"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.activity.series}><defs><linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#73d3a7" stopOpacity={.32}/><stop offset="95%" stopColor="#73d3a7" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--a-line)"/><XAxis dataKey="date" tickFormatter={(value)=>value.slice(5)} tick={{fill:'var(--a-muted)',fontSize:9}} axisLine={false} tickLine={false}/><YAxis allowDecimals={false} tick={{fill:'var(--a-muted)',fontSize:9}} axisLine={false} tickLine={false}/><Tooltip contentStyle={{background:'var(--a-panel)',border:'1px solid var(--a-line)',fontSize:11}}/><Area type="monotone" dataKey="admin_events" stroke="#73d3a7" fill="url(#activityFill)" strokeWidth={2}/></AreaChart></ResponsiveContainer></div></article>
      <article className="dashboard-card risk-chart"><header><div><h3>Risk distribution</h3><p>Measured test-set predictions</p></div><span className="source-badge">Test set</span></header><div className="risk-chart-body"><ResponsiveContainer width="58%" height={220}><PieChart><Pie data={data.risk.items} dataKey="count" nameKey="risk_class" innerRadius={60} outerRadius={88} paddingAngle={3}>{data.risk.items.map((item,index)=><Cell key={item.risk_class} fill={index ? '#e88777' : '#73d3a7'}/>)}</Pie><Tooltip contentStyle={{background:'var(--a-panel)',border:'1px solid var(--a-line)',fontSize:11}}/></PieChart></ResponsiveContainer><div className="risk-legend">{data.risk.items.map((item,index)=><div key={item.risk_class}><span style={{background:index?'#e88777':'#73d3a7'}}/><p>{item.risk_class}<strong>{item.count.toLocaleString()}</strong><small>{percent(item.count/data.risk.total)}</small></p></div>)}</div></div></article>
      <article className="dashboard-card fhe-chart"><header><div><h3>FHE stage breakdown</h3><p>Measured OpenFHE packed-batch latency</p></div><span className="source-badge">CKKS</span></header><div className="chart-body"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.fhe.stages} layout="vertical" margin={{left:20}}><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--a-line)"/><XAxis type="number" tick={{fill:'var(--a-muted)',fontSize:9}} axisLine={false} tickLine={false} unit=" ms"/><YAxis type="category" dataKey="stage" width={92} tick={{fill:'var(--a-muted)',fontSize:9}} axisLine={false} tickLine={false}/><Tooltip contentStyle={{background:'var(--a-panel)',border:'1px solid var(--a-line)',fontSize:11}}/><Bar dataKey="milliseconds" fill="#73d3a7" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></div><footer><span>Ring dimension <strong>{data.fhe.ring_dimension.toLocaleString()}</strong></span><span>Mean error <strong>{data.fhe.mean_absolute_error.toExponential(2)}</strong></span></footer></article>
      <article className="dashboard-card privacy-card"><header><div><h3>Privacy control status</h3><p>Implemented and planned controls distinguished</p></div><span className="source-badge good">Validated</span></header><div className="privacy-checks">{data.privacy.checks.map((check)=><div key={check.name} className={check.status}><span>{check.status==='implemented'?<CheckCircle2 size={15}/>:<Clock3 size={15}/>}</span><p>{check.name}<small>{check.status}</small></p></div>)}</div><p className="privacy-note">{data.privacy.note}</p></article>
    </section>
    <section className="recent-activity"><header><div><h3>Recent activity</h3><p>Privacy-safe administrative audit records</p></div></header>{data.activity.recent.length?<div>{data.activity.recent.map((event)=><article key={event.id}><span className={event.result}/><div><strong>{actionLabel(event.action)}</strong><small>{event.resource_type} · {event.actor_role?.replaceAll('_',' ') ?? 'system'}</small></div><time>{new Date(event.timestamp).toLocaleString()}</time></article>)}</div>:<div className="empty-activity"><Activity size={20}/><p>No administrative activity has been recorded yet.</p></div>}</section>
  </div>
}
