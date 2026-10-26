const TONE_COLORS = { orange: '#d88725', green: '#3d8069', red: '#c75950' }
export default function ScoreRing({ score = 0, label = 'Score', tone = 'orange', suffix = '/ 100' }) {
  const clamped = Math.max(0, Math.min(100, score))
  const color = TONE_COLORS[tone] || TONE_COLORS.orange
  return (
    <div
      className="score-ring"
      style={{ background: 'conic-gradient(${color} 0 ${clamped}%, #f0e7d4 ${clamped}% 100%)' }}
      aria-label={'${label}: ${score} out of 100'}
    >
      <div className="score-ring__inner">
        <strong>{score}</strong>
        <span>{suffix}</span>
      </div>
    </div>
  )
}
