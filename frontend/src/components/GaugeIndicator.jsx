const LEVEL_LABEL = { low: 'Low', medium: 'Medium', high: 'High' }

export default function GaugeIndicator({
  score = 0,
  level = 'low',
  readoutLabel = 'Risk',
}) {
  const clamped = Math.max(0, Math.min(100, score))
  const angle = -90 + (clamped / 100) * 180

  return (
    <div
      className="gauge"
      role="img"
      aria-label={`${readoutLabel} indicator: ${LEVEL_LABEL[level] || level}, score ${clamped} out of 100`}
    >
      <div className="gauge__arc">
        <span
          className="gauge__needle"
          style={{ transform: `rotate(${angle}deg)` }}
        />
        <span className="gauge__hub" />
      </div>

      <div className="gauge__zones">
        <span>Low</span>
        <span>Medium</span>
        <span>High</span>
      </div>

      <div className="gauge__readout">
        <strong className={`gauge__level gauge__level--${level}`}>
          {LEVEL_LABEL[level] || level}
        </strong>
        <span>{clamped} / 100</span>
      </div>
    </div>
  )
}