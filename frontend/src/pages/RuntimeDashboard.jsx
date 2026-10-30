
import { Gauge, Scale, Search as SearchIcon, ShieldAlert } from 'lucide-react'
import {
  BackendOfflineNotice,
  IndicatorCard,
  RiskBadge,
  Skeleton,
} from '../components'
import { useRuntimeDashboard } from '../hooks/useRuntimeDashboard'

const LEVEL_TO_BAND = {
  low: 'LOW',
  medium: 'MEDIUM',
  high: 'HIGH',
}

export default function RuntimeDashboard() {
  const { data, loading, error } = useRuntimeDashboard()

  if (loading) {
    return (
      <section className="page-content">
        <Skeleton variant="heading" />
        <div className="indicator-grid">
          <Skeleton variant="card" count={4} />
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="page-content">
        <p className="empty-state">
          Could not load the runtime dashboard: {error.message}
        </p>
      </section>
    )
  }

  const { indicators, customerRows } = data

  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            WORKSPACE / RUNTIME DASHBOARD
            <span className="live-pill">
              <i />
              Live
            </span>
          </p>
          <h1>Runtime risk dashboard</h1>
          <p className="heading-copy">
            Live low / medium / high risk indicators aggregated from
            investigation cases.
          </p>
        </div>
      </div>

      {data.overview?.isMock && (
        <BackendOfflineNotice label="live runtime signals" />
      )}

      <section className="indicator-grid" aria-label="Risk indicators">
        <IndicatorCard
          title="Overall risk"
          description="Across all investigation cases"
          icon={Gauge}
          {...indicators.overall}
        />

        <IndicatorCard
          title="Fraud risk"
          description="Cases tagged as fraud investigations"
          icon={ShieldAlert}
          {...indicators.fraud}
        />

        <IndicatorCard
          title="Credit risk"
          description="Cases tagged as credit risk reviews"
          icon={Scale}
          {...indicators.credit}
        />

        <IndicatorCard
          title="Compliance risk"
          description="Cases tagged as compliance reviews"
          icon={SearchIcon}
          {...indicators.compliance}
        />
      </section>

      <section className="panel cases-panel">
        <div className="panel-heading">
          <div>
            <h2>Customer risk levels</h2>
            <p>Highest case severity recorded per customer</p>
          </div>
        </div>

        {customerRows.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Segment</th>
                  <th>Risk level</th>
                  <th>Open cases</th>
                </tr>
              </thead>

              <tbody>
                {customerRows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <div className="account-cell">
                        <span className="company-avatar">
                          {row.name.slice(0, 2).toUpperCase()}
                        </span>
                        <strong>{row.name}</strong>
                      </div>
                    </td>
                    <td>{row.segment}</td>
                    <td>
                      <RiskBadge band={LEVEL_TO_BAND[row.level]} />
                    </td>
                    <td>{row.caseCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-state">No customers recorded yet.</p>
        )}
      </section>
    </section>
  )
}
