import { ArrowUpRight, Search, ShieldAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getRiskCases } from '../services/riskApi'

export default function RiskCases() {
  const [cases, setCases] = useState([])

  useEffect(() => {
    getRiskCases().then(setCases)
  }, [])

  return (
    <section className="page-content">
      <div className="page-heading"><div><p className="eyebrow">WORKSPACE / CASE MANAGEMENT</p><h1>Risk cases</h1><p className="heading-copy">Review, assign, and track portfolio risk investigations.</p></div><button className="primary-button"><ShieldAlert size={16} />Open a case</button></div>
      <div className="panel cases-panel"><div className="panel-heading"><div><h2>Active investigations</h2><p>{cases.length} cases currently in your workspace</p></div><button className="filter-button"><Search size={15} /> Search cases</button></div><div className="table-wrap"><table><thead><tr><th>Account</th><th>Case type</th><th>Owner</th><th>Risk score</th><th>Status</th><th /></tr></thead><tbody>{cases.map((item) => <tr key={item.name}><td><div className="account-cell"><span className="company-avatar">{item.name.slice(0, 2).toUpperCase()}</span><strong>{item.name}</strong></div></td><td>{item.type}</td><td>{item.owner}</td><td><span className={`table-score table-score--${item.tone}`}>{item.score}</span></td><td><span className={`status status--${item.tone}`}>{item.status}</span></td><td><button className="text-button" aria-label={`Open ${item.name}`}>Open <ArrowUpRight size={15} /></button></td></tr>)}</tbody></table></div></div>
    </section>
  )
}
