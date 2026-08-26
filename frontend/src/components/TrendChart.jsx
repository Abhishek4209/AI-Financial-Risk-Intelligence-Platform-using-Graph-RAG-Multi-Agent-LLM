const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

export default function TrendChart({ values = [62, 58, 61, 49, 43, 42.6] }) {
  const finalValue = values[values.length - 1] ?? 0

  return (
    <div className="trend-chart" aria-label="Risk exposure trend from January to June">
      <div className="chart-y-axis"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div>
      <div className="chart-plot">
        <div className="chart-grid"><i /><i /><i /><i /><i /></div>
        <svg viewBox="0 0 660 220" preserveAspectRatio="none" role="img" aria-label="Risk exposure has decreased over six months">
          <defs>
            <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#e6a23c" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#e6a23c" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,62 C44,72 66,90 110,86 S172,72 220,106 S282,125 330,120 S392,95 440,131 S500,162 550,154 S612,145 660,172 L660,220 L0,220 Z" fill="url(#areaFill)" />
          <path d="M0,62 C44,72 66,90 110,86 S172,72 220,106 S282,125 330,120 S392,95 440,131 S500,162 550,154 S612,145 660,172" fill="none" stroke="#d88725" strokeWidth="3" vectorEffect="non-scaling-stroke" />
          <circle cx="660" cy="172" r="5" fill="#fffdf7" stroke="#d88725" strokeWidth="3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="chart-x-axis">{months.map((month) => <span key={month}>{month}</span>)}</div>
      </div>
      <span className="sr-only">Current value: {finalValue}</span>
    </div>
  )
}
