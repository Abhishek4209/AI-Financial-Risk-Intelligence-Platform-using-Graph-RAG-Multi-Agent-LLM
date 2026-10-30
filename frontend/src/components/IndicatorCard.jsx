import GaugeIndicator from './GaugeIndicator'

const ICON_TONE = {
  low: 'green',
  medium: 'orange',
  high: 'red',
}

export default function IndicatorCard({
  title,
  description,
  icon: Icon,
  score = 0,
  level = 'low',
  counts = {},
  total = 0,
}) {
  return (
    <article className="indicator-card">
      <div className="indicator-card__top">
        <div>
          <span className="metric-label">{title}</span>
          {description && (
            <p className="indicator-card__description">{description}</p>
          )}
        </div>

        {Icon && (
          <span
            className={`metric-icon metric-icon--${ICON_TONE[level] || 'orange'}`}
          >
            <Icon size={17} />
          </span>
        )}
      </div>

      <GaugeIndicator score={score} level={level} readoutLabel={title} />

      <div className="indicator-card__counts">
        <span>
          <i className="dot dot--green" /> Low <b>{counts.low || 0}</b>
        </span>
        <span>
          <i className="dot dot--orange" /> Medium{' '}
          <b>{counts.medium || 0}</b>
        </span>
        <span>
          <i className="dot dot--red" /> High <b>{counts.high || 0}</b>
        </span>
      </div>

      <p className="indicator-card__total">
        {total} case{total === 1 ? '' : 's'} analyzed
      </p>
    </article>
  )
}