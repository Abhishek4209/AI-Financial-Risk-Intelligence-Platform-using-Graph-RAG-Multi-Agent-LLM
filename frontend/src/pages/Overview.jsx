
import { Activity, ArrowUpRight, ShieldAlert, Sparkles } from 'lucide-react'
import { useRiskOverview } from '../hooks/useRiskOverview'
import {
  BackendOfflineNotice,
  PriorityCasesTable,
  RiskDistributionDonut,
  ScoreRing,
  Skeleton,
  TrendChart,
} from '../components'

function formatCurrency(value) {
  if (!value) return '$0'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

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

export default function Overview() {
  const { data, loading, error } = useRiskOverview()

  if (loading) {
    return (
      <section className="page-content">
        <Skeleton variant="heading" />
        <div className="metric-grid">
          <Skeleton variant="card" count={3} />
        </div>
        <div className="dashboard-grid">
          <Skeleton variant="panel" count={2} />
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="page-content">
        <p className="empty-state">
          Could not load the dashboard: {error.message}
        </p>
      </section>
    )
  }

  const openRate = data.total_cases
    ? Math.round((data.open_cases / data.total_cases) * 100)
    : 0

  const trendValues = data.monthly_case_trend.map((point) => point.count)
  const trendLabels = data.monthly_case_trend.map((point) => point.month)
  const latestTrend = trendValues.at(-1) ?? 0
  const ringTone =
    openRate > 50 ? 'red' : openRate > 25 ? 'orange' : 'green'

  return (
    <section className="page-content">
      {data.isMock && (
        <BackendOfflineNotice label="live portfolio data" />
      )}

      <section className="page-heading">
        <div>
          <p className="eyebrow">
            WORKSPACE / OVERVIEW
            <span className="live-pill">
              <i />
              Live
            </span>
          </p>
          <h1>Portfolio overview</h1>
          <p className="heading-copy">
            Live aggregates from PostgreSQL. {data.open_cases} of{' '}
            {data.total_cases} cases are open.
          </p>
        </div>
        <button className="primary-button">
          <Sparkles size={16} />
          Run new analysis
        </button>
      </section>

      <section className="metric-grid" aria-label="Portfolio metrics">
        <article className="metric-card metric-card--score">
          <div className="metric-card__top">
            <span className="metric-label">Open case rate</span>
          </div>
          <div className="score-content">
            <ScoreRing
              score={openRate}
              label="Open case rate"
              tone={ringTone}
              suffix="% open"
            />
            <div>
              <strong className="metric-value">
                {data.open_cases} open
              </strong>
              <p className="metric-change">
                of {data.total_cases} total cases
              </p>
            </div>
          </div>
        </article>

        <article className="metric-card">
          <div className="metric-card__top">
            <span className="metric-label">Exposure under review</span>
            <span className="metric-icon metric-icon--orange">
              <Activity size={17} />
            </span>
          </div>
          <strong className="metric-value">
            {formatCurrency(data.exposure_under_review)}
          </strong>
          <p className="metric-change">
            Sum of transaction amounts tied to open cases
          </p>
        </article>

        <article className="metric-card">
          <div className="metric-card__top">
            <span className="metric-label">Total transactions</span>
            <span className="metric-icon metric-icon--red">
              <ShieldAlert size={17} />
            </span>
          </div>
          <strong className="metric-value">
            {data.total_transactions.toLocaleString()}
          </strong>
          <p className="metric-change">
            Recorded in the platform database
          </p>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel trend-panel">
          <div className="panel-heading">
            <div>
              <h2>Case volume trend</h2>
              <p>New investigation cases per month</p>
            </div>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-line" />
              Cases opened
            </span>
            <span className="legend-total">
              Latest <b>{latestTrend}</b>
            </span>
          </div>
          <TrendChart values={trendValues} labels={trendLabels} />
        </article>

        <article className="panel distribution-panel">
          <div className="panel-heading">
            <div>
              <h2>Risk distribution</h2>
              <p>By severity, across all cases</p>
            </div>
          </div>
          <RiskDistributionDonut data={data.case_breakdown} />
        </article>
      </section>

      <section className="panel cases-panel">
        <div className="panel-heading">
          <div>
            <h2>Recent cases</h2>
            <p>Latest investigations recorded in the workspace</p>
          </div>
          <div className="panel-actions">
            <ArrowUpRight size={15} />
          </div>
        </div>

        {data.recent_cases.length ? (
          <PriorityCasesTable cases={data.recent_cases.map(toCaseRow)} />
        ) : (
          <p className="empty-state">No cases recorded yet.</p>
        )}
      </section>
    </section>
  )
}
