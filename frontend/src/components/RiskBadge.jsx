import { CircleAlert, ShieldAlert, ShieldCheck } from 'lucide-react'
const TONE_BY_BAND = { HIGH: 'high', MEDIUM: 'medium', LOW: 'low', BELOW_MODEL_THRESHOLD: 'low' }
const ICON_BY_TONE = { low: ShieldCheck, medium: CircleAlert, high: ShieldAlert }
export default function RiskBadge({ band, showIcon = true }) {
  const tone = TONE_BY_BAND[band] || 'medium'
  const Icon = ICON_BY_TONE[tone]
  return (
    <span className={'status status--${tone}'}>
      {showIcon && <Icon size={12} />}
      {band?.replaceAll('_', ' ')}
    </span>
  )
}
