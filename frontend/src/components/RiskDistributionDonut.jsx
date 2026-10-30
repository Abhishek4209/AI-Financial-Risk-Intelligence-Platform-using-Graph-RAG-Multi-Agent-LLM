import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const COLOR_BY_TONE = {
  high: '#c75950',
  medium: '#d88725',
  low: '#3d8069',
  informational: '#7b8a98',
}

export default function RiskDistributionDonut({ data = {} }) {
  const entries = Object.entries(data).filter(([, value]) => value > 0)
  const total = entries.reduce((sum, [, value]) => sum + value, 0)

  if (!total) {
    return <p className="empty-state">No data recorded yet.</p>
  }

  const chartData = entries.map(([name, value]) => ({ name, value }))

  return (
    <div className="risk-donut" aria-label="Risk distribution donut chart">
      <div className="risk-donut__plot">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              innerRadius={62}
              outerRadius={92}
              paddingAngle={3}
              stroke="none"
            >
              {chartData.map((entry) => (
                <Cell
                  key={entry.name}
                  fill={COLOR_BY_TONE[entry.name] || '#8d958d'}
                />
              ))}
            </Pie>

            <Tooltip
              formatter={(value, name) => [
                `${value} (${((value / total) * 100).toFixed(0)}%)`,
                name,
              ]}
              contentStyle={{
                fontSize: 11,
                borderRadius: 6,
                border: '1px solid var(--line)',
              }}
            />
          </PieChart>
        </ResponsiveContainer>

        <div className="risk-donut__center">
          <strong>{total}</strong>
          <span>total</span>
        </div>
      </div>

      <div className="risk-donut__legend">
        {chartData.map((entry) => (
          <span key={entry.name}>
            <i className={`dot dot--${entry.name}`} />
            {entry.name} <b>{entry.value}</b>
          </span>
        ))}
      </div>
    </div>
  )
}