const TONES = ['high', 'medium', 'low', 'informational']
export default function BarChart({ data = {}, unit = '' }) {
  const entries = Object.entries(data)
  const total = entries.reduce((sum, [, value]) => sum + value, 0)
  if (!total) return <p className="empty-state">No data recorded yet.</p>
  return (
    <div className="bar-chart" aria-label="Distribution chart">
      {entries.map(([label, value], index) => {
        const percent = total ? (value / total) * 100 : 0
        const tone = TONES[index % TONES.length]
        return (
          <div className="bar-chart__row" key={label}>
            <span className="bar-chart__label"><i className={'dot dot--${tone}'} />{label}</span>
            <div className="bar-chart__track">
              <span className={'bar-chart__fill bar-chart__fill--${tone}'} style={{ width: '${percent}%' }} 
/>
            </div>
            <span className="bar-chart__value">{value}{unit} <small>({percent.toFixed(0)}%)</small></spa
n>
          </div>
        )
      })}
    </div>
  )
}
