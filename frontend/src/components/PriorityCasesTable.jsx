import { MoreHorizontal } from 'lucide-react'

export default function PriorityCasesTable({ cases = [] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead><tr><th>Account</th><th>Case type</th><th>Owner</th><th>Risk score</th><th>Status</th><th aria-label="Actions" /></tr></thead>
        <tbody>
          {cases.map((item) => (
            <tr key={item.id || item.name}>
              <td><div className="account-cell"><span className="company-avatar">{item.name.split(' ').map((word) => word[0]).slice(0, 2).join('')}</span><strong>{item.name}</strong></div></td>
              <td>{item.type}</td>
              <td>{item.owner}</td>
              <td><span className={`table-score table-score--${item.tone}`}>{item.score}</span></td>
              <td><span className={`status status--${item.tone}`}>{item.status}</span></td>
              <td><button className="card-menu" aria-label={`Open ${item.name} actions`}><MoreHorizontal size={18} /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
