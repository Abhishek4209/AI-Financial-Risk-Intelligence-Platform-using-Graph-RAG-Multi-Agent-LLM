import { Activity, ArrowUpRight, ShieldAlert, Sparkles } from 'lucide-react'
import { useRiskOverview } from '../hooks/useRiskOverview'
import { BarChart, PriorityCasesTable, ScoreRing, TrendChart } from '../components'

function formatCurrency(value) {
  const amount = Number(value || 0)
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(1)}K`
  return `$${amount.toFixed(0)}`
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
    type: item.case_type || 'Risk review',
    owner: item.owner || 'Unassigned',
    score: item.severity || 'low',
    status: item.status || 'Open',
    tone: severityTone(item.severity),
  }
}
export default function Overview() {
  const { data, loading, error } = useRiskOverview()
  if (loading) return <section className="page-content"><p className="empty-state">Loading portfolio data...</p></section>
  if (error) return <section className="page-content"><p className="empty-state empty-state--warning">Could not load dashboard: {error.message}</p></section>

  const trend = Array.isArray(data.monthly_case_trend) ? data.monthly_case_trend : []
  const openRate = data.total_cases ? Math.round((data.open_cases / data.total_cases) * 100) : 0
  const trendValues = trend.map((point) => point.count)
  const trendLabels = trend.map((point) => point.month)
  const ringTone = openRate > 50 ? 'red' : openRate > 25 ? 'orange' : 'green'
  const recentCases = (data.recent_cases?.length ? data.recent_cases : [
    { id: 'CASE-1042', customer_id: 'Northstar Capital', case_type: 'Fraud investigation', owner: 'A. Patel', severity: 'high', status: 'Open' },
    { id: 'CASE-1041', customer_id: 'Meridian Retail', case_type: 'Credit risk review', owner: 'R. Shah', severity: 'medium', status: 'Review' },
  ]).map(toCaseRow)

  return (
    <section className="page-content">
      {data.isMock && <p className="empty-state empty-state--warning">Backend unavailable; showing local sample data.</p>}
      <section className="page-heading">
        <div><p className="eyebrow">WORKSPACE / OVERVIEW <span className="live-pill"><i />Demo</span></p>
          <h1>Portfolio overview</h1>
          <p className="heading-copy">Monitor investigation cases, exposure, and portfolio risk signals.</p>
        </div>
        <button className="primary-button" onClick={() => window.alert('Analysis requires the risk-model backend.')}><Sparkles size={16} />Run new analysis</button>
      </section>
      <section className="metric-grid" aria-label="Portfolio metrics">
        <article className="metric-card metric-card--score">
          <div className="metric-card__top"><span className="metric-label">Open case rate</span></div>
          <div className="score-content"><ScoreRing score={openRate} label="Open case rate" tone={ringTone} suffix="% open" />
            <div><strong className="metric-value">{data.open_cases} open</strong><p className="metric-change">of {data.total_cases} total cases</p></div>
          </div>
        </article>
        <article className="metric-card">
          <div className="metric-card__top"><span className="metric-label">Exposure under review</span><span className="metric-icon metric-icon--orange"><Activity size={17} /></span></div>
          <strong className="metric-value">{formatCurrency(data.exposure_under_review)}</strong><p className="metric-change">Across active investigations</p>
        </article>
        <article className="metric-card">
          <div className="metric-card__top"><span className="metric-label">Transactions monitored</span><span className="metric-icon metric-icon--green"><ArrowUpRight size={17} /></span></div>
          <strong className="metric-value">{Number(data.total_transactions || 0).toLocaleString()}</strong><p className="metric-change">Risk-scored transactions</p>
        </article>
        <article className="metric-card">
          <div className="metric-card__top"><span className="metric-label">High-risk cases</span><span className="metric-icon metric-icon--red"><ShieldAlert size={17} /></span></div>
          <strong className="metric-value">{data.case_breakdown?.high || 0}</strong><p className="metric-change">Prioritized for analyst review</p>
        </article>
      </section>
      <section className="dashboard-grid">
        <article className="panel"><div className="panel-heading"><div><h2>Case volume trend</h2><p>Recent monthly investigations</p></div></div><TrendChart values={trendValues} labels={trendLabels} /></article>
        <article className="panel"><div className="panel-heading"><div><h2>Risk distribution</h2><p>Cases grouped by severity</p></div></div><BarChart data={data.case_breakdown || {}} /></article>
      </section>
      <article className="panel cases-panel"><div className="panel-heading"><div><h2>Priority cases</h2><p>Recent investigations that may need attention</p></div></div><PriorityCasesTable cases={recentCases} /></article>
    </section>
  )
}
