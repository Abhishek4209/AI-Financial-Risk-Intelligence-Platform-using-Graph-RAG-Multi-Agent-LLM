const TONE_BY_BAND = { HIGH: 'high', MEDIUM: 'medium', LOW: 'low', BELOW_MODEL_THRESHOLD: 'low' }
export default function RiskBadge({ band }) {
const tone = TONE_BY_BAND[band] || 'medium'
return <span className={`status status--${tone}`}>{band?.replaceAll('_', ' ')}</span>
}
