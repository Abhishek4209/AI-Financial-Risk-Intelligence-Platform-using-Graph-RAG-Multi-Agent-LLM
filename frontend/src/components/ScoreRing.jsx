export default function ScoreRing({ score = 68, label = 'Portfolio risk score' }) {
  return (
    <div className="score-ring" aria-label={`${label}: ${score} out of 100`}>
      <div className="score-ring__inner">
        <strong>{score}</strong>
        <span>/ 100</span>
      </div>
    </div>
  )
}
