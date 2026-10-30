
import { ArrowUpRight, Search, ShieldAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getCases, isNetworkError } from '../services/riskApi'
import { BackendOfflineNotice } from '../components'

function severityTone(severity) {
  if (severity === 'high') return 'high'
  if (severity === 'medium') return 'medium'
  return 'low'
}

function toCaseRow(item) {
  return {
    id: item.id,
    name: item.customer_id || 'Unassigned customer',
    type: item.case_type,
    owner: item.owner || 'Unassigned',
    score: item.severity,
    status: item.status,
    tone: severityTone(item.severity),
  }
}

export default function RiskCases() {
  const [cases, setCases] = useState([])
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    setError(null)

    getCases()
      .then((rows) => setCases(rows.map(toCaseRow)))
      .catch(setError)
  }, [reloadKey])

  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / CASE MANAGEMENT</p>
          <h1>Risk cases</h1>
          <p className="heading-copy">
            Review, assign, and track portfolio risk investigations.
          </p>
        </div>

        <button className="primary-button">
          <ShieldAlert size={16} />
          Open a case
        </button>
      </div>

      {error &&
        (isNetworkError(error) ? (
          <BackendOfflineNotice
            label="risk cases"
            onRetry={() => setReloadKey((key) => key + 1)}
          />
        ) : (
          <p className="empty-state empty-state--warning">
            Could not load cases: {error.message}
          </p>
        ))}

      <div className="panel cases-panel">
        <div className="panel-heading">
          <div>
            <h2>Active investigations</h2>
            <p>
              {cases.length} cases currently in your workspace
            </p>
          </div>

          <button className="filter-button">
            <Search size={15} />
            Search cases
          </button>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Case type</th>
                <th>Owner</th>
                <th>Risk score</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {cases.map((item) => (
                <tr key={item.id || item.name}>
                  <td>
                    <div className="account-cell">
                      <span className="company-avatar">
                        {item.name.slice(0, 2).toUpperCase()}
                      </span>
                      <strong>{item.name}</strong>
                    </div>
                  </td>

                  <td>{item.type}</td>
                  <td>{item.owner}</td>

                  <td>
                    <span
                      className={`table-score table-score--${item.tone}`}
                    >
                      {item.score}
                    </span>
                  </td>

                  <td>
                    <span className={`status status--${item.tone}`}>
                      {item.status}
                    </span>
                  </td>

                  <td>
                    <button
                      className="text-button"
                      aria-label={`Open ${item.name}`}
                    >
                      Open
                      <ArrowUpRight size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
