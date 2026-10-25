import { ArrowUpRight, Search, ShieldAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getCases } from '../services/riskApi'
function tone(severity) { return severity === 'high' ? 'high' : severity === 'medium' ? 'medium' : 'low' }
export default function RiskCases() {
  const [cases, setCases] = useState([])
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  useEffect(() => {
    let active = true
    getCases().then((rows) => { if (active) setCases(rows) }).catch((err) => { if (active) setError(err) })
    return () => { active = false }
  }, [])
  const filtered = cases.filter((item) => `${item.customer_id || ''} ${item.case_type || ''} ${item.status || ''}`.toLowerCase().includes(query.toLowerCase()))
  return (
    <section className="page-content">
      <div className="page-heading"><div><p className="eyebrow">WORKSPACE / CASE MANAGEMENT</p><h1>Risk cases</h1><p className="heading-copy">Review and track portfolio risk investigations.</p></div><button className="primary-button" onClick={() => window.alert('Creating a case requires the backend.')}><ShieldAlert size={16} />Open a case</button></div>
      {error && <p className="empty-state empty-state--warning">Could not load cases: {error.message}</p>}
      <div className="panel cases-panel"><div className="panel-heading"><div><h2>Active investigations</h2><p>{filtered.length} cases in your workspace</p></div><label className="filter-button"><Search size={15} /><input aria-label="Search cases" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search cases" /></label></div>
        <div className="table-wrap"><table><thead><tr><th>Account</th><th>Case type</th><th>Owner</th><th>Risk</th><th>Status</th><th /></tr></thead><tbody>
          {filtered.map((item) => <tr key={item.id}><td><div className="account-cell"><span className="company-avatar">{String(item.customer_id || 'NA').slice(0, 2).toUpperCase()}</span><strong>{item.customer_id || 'Unassigned customer'}</strong></div></td><td>{item.case_type || 'Risk review'}</td><td>{item.owner || 'Unassigned'}</td><td><span className={`table-score table-score--${tone(item.severity)}`}>{item.severity || 'low'}</span></td><td><span className={`status status--${tone(item.severity)}`}>{item.status || 'Open'}</span></td><td><button className="text-button" aria-label={`Open ${item.id}`}>Open <ArrowUpRight size={15} /></button></td></tr>)}
        </tbody></table></div>
        {filtered.length === 0 && <p className="empty-state">No matching cases found.</p>}
      </div>
    </section>
  )
}
