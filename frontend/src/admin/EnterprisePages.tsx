import { useCallback, useEffect, useState } from 'react'
import { Building2, CheckCircle2, ClipboardList, LockKeyhole, RefreshCw } from 'lucide-react'
import { API_URL } from './api'
import { useAuth } from './AuthContext'

type Application = { id:string; application_number:string; organization_id:string; branch_id:string; status:string; model_recommendation:string|null; risk_score_band:string|null; prediction_id:string|null; version:number; created_at:string }
type Organization = { id:string; code:string; name:string; status:string; risk_threshold:number; model_version:string; openfhe_profile:string }

async function authorizedJson(url:string, token:string|null, init?:RequestInit){
  const response=await fetch(url,{...init,headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`,...init?.headers}})
  const body=await response.json()
  if(!response.ok)throw new Error(body.error?.message??body.detail??`Request failed (${response.status})`)
  return body
}

export function ApplicationsPage(){
  const{accessToken,hasPermission}=useAuth();const[items,setItems]=useState<Application[]>([]);const[status,setStatus]=useState('');const[error,setError]=useState('');const[loading,setLoading]=useState(true)
  const load=useCallback(()=>{setLoading(true);setError('');const query=status?`?status=${encodeURIComponent(status)}`:'';authorizedJson(`${API_URL}/api/v1/applications${query}`,accessToken).then(body=>setItems(body.items)).catch(e=>setError(e instanceof Error?e.message:'Unable to load applications')).finally(()=>setLoading(false))},[accessToken,status])
  useEffect(()=>{void load()},[load])
  async function advance(item:Application,target:string){setError('');try{await authorizedJson(`${API_URL}/api/v1/applications/${item.id}/transitions`,accessToken,{method:'POST',body:JSON.stringify({to_status:target,expected_version:item.version})});load()}catch(e){setError(e instanceof Error?e.message:'Transition failed')}}
  return <div className="admin-page enterprise-page"><div className="monitor-heading"><div><p className="admin-kicker">Human-governed credit workflow</p><h2>Credit Applications</h2><p>Organization-scoped operational metadata. Customer financial features are not displayed or stored here.</p></div>{hasPermission('applications.write')&&<button className="export-button"><ClipboardList size={15}/>New application</button>}</div>
    <div className="privacy-strip"><LockKeyhole size={16}/><span><strong>Privacy Mode: OpenFHE CKKS encrypted inference</strong>Model recommendation supports—but never replaces—the authorized human decision.</span></div>
    <div className="enterprise-toolbar"><label>Status<select value={status} onChange={event=>setStatus(event.target.value)}><option value="">All states</option>{['DRAFT','SUBMITTED','PREDICTION_PENDING','PREDICTED','UNDER_REVIEW','APPROVED','REJECTED','NEEDS_ADDITIONAL_INFORMATION','CANCELLED'].map(value=><option key={value}>{value}</option>)}</select></label><button onClick={load} aria-label="Refresh applications"><RefreshCw size={15}/></button></div>
    {error&&<div className="table-error" role="alert">{error}</div>}{loading?<div className="dashboard-skeleton"><span/><span/><span/></div>:<section className="application-list">{items.length?items.map(item=><article key={item.id}><div><span className={`request-badge ${['APPROVED','PREDICTED'].includes(item.status)?'completed':item.status==='REJECTED'?'failed':''}`}>{item.status.replaceAll('_',' ')}</span><h3>{item.application_number}</h3><small>Created {new Date(item.created_at).toLocaleString()}</small></div><div><span>Model recommendation</span><strong>{item.model_recommendation??'Pending encrypted prediction'}</strong><small>{item.risk_score_band?`${item.risk_score_band} score band`:'No plaintext score retained'}</small></div><div><span>Governance</span><strong>Version {item.version}</strong><small>{item.prediction_id??'Prediction not linked'}</small></div>{hasPermission('applications.review')&&<div className="workflow-actions">{item.status==='DRAFT'&&<button onClick={()=>void advance(item,'SUBMITTED')}>Submit</button>}{item.status==='SUBMITTED'&&<button onClick={()=>void advance(item,'PREDICTION_PENDING')}>Request prediction</button>}{item.status==='PREDICTED'&&<button onClick={()=>void advance(item,'UNDER_REVIEW')}>Begin review</button>}</div>}</article>):<div className="table-empty"><ClipboardList/><strong>No applications in this scope</strong><p>Create or assign an application to begin the governed workflow.</p></div>}</section>}</div>
}

export function OrganizationsPage(){
  const{accessToken}=useAuth();const[items,setItems]=useState<Organization[]>([]);const[error,setError]=useState('')
  useEffect(()=>{authorizedJson(`${API_URL}/api/v1/organizations`,accessToken).then(body=>setItems(body.items)).catch(e=>setError(e instanceof Error?e.message:'Unable to load organizations'))},[accessToken])
  return <div className="admin-page enterprise-page"><div className="monitor-heading"><div><p className="admin-kicker">Institution configuration</p><h2>Organizations & Branches</h2><p>Model, risk threshold, OpenFHE profile, branch structure, and access scope are governed per institution.</p></div></div>{error&&<div className="table-error">{error}</div>}<section className="organization-grid">{items.map(item=><article key={item.id}><header><Building2/><span className="request-badge completed">{item.status}</span></header><h3>{item.name}</h3><small>{item.code}</small><dl><div><dt>Risk threshold</dt><dd>{item.risk_threshold.toFixed(2)}</dd></div><div><dt>Model</dt><dd>{item.model_version}</dd></div><div><dt>Crypto profile</dt><dd>{item.openfhe_profile}</dd></div></dl><p><CheckCircle2 size={14}/>Scoped access policy active</p></article>)}</section></div>
}
