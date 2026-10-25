const WIDTH = 660
const HEIGHT = 220
const AXIS_BOTTOM = 198
export default function TrendChart({ values = [], labels = [] }) {
if (!values.length) return <p className="empty-state">No case history recorded yet.</p>
const maxValue = Math.max(...values, 1)
const stepX = values.length > 1 ? WIDTH / (values.length - 1) : 0
const points = values.map((value, index) => ({
x: values.length > 1 ? index * stepX : WIDTH / 2,
y: AXIS_BOTTOM - (value / maxValue) * AXIS_BOTTOM,
}))
const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`).join(' ')
const lastPoint = points.at(-1)
const areaPath = `${linePath} L${lastPoint.x},${HEIGHT} L0,${HEIGHT} Z`
const finalValue = values.at(-1) ?? 0
return (
<div className="trend-chart" aria-label="Case volume trend over recent months">
<div className="chart-y-axis">
<span>{maxValue}</span>
<span>{Math.round(maxValue / 2)}</span>
<span>0</span>
</div>
<div className="chart-plot">
<div className="chart-grid"><i /><i /><i /><i /><i /></div>
<svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img" aria-label="Case volume by month">
<defs>
<linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
<stop offset="0%" stopColor="#e6a23c" stopOpacity="0.28" />
<stop offset="100%" stopColor="#e6a23c" stopOpacity="0" />
</linearGradient>
</defs>
<path d={areaPath} fill="url(#areaFill)" />
<path d={linePath} fill="none" stroke="#d88725" strokeWidth="3" vectorEffect="non-scaling-stroke" />
{points.map((point, index) => (
<circle key={labels[index] || index} cx={point.x} cy={point.y} r="4" fill="#fffdf7" stroke="#d88725"
strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
))}
</svg>
<div className="chart-x-axis">{labels.map((label) => <span key={label}>{label}</span>)}</div>
</div>
<span className="sr-only">Current value: {finalValue}</span>
</div>
)
}
