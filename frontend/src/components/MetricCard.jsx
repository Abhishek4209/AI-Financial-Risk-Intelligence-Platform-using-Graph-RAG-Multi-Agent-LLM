import { ArrowDownRight, ArrowUpRight } from 'lucide-react'

export default function MetricCard({ label, value, change, direction = 'down', tone = 'positive', icon: Icon, children }) {
  const ChangeIcon = direction === 'up' ? ArrowUpRight : ArrowDownRight

  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span className="metric-label">{label}</span>
        {Icon && <span className={`metric-icon metric-icon--${tone}`}><Icon size={17} /></span>}
      </div>
      <strong className="metric-value">{value}</strong>
      {change && <p className={`metric-change metric-change--${tone}`}><ChangeIcon size={15} /> {change} <span>vs last month</span></p>}
      {children}
    </article>
  )
}
