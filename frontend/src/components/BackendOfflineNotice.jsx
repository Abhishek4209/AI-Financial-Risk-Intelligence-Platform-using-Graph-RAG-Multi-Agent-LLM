import { PlugZap, RotateCw } from 'lucide-react'
export default function BackendOfflineNotice({
  label = 'this data',
  message,
  onRetry,
  title = 'Backend unreachable',
}) {
  return (
    <div className="offline-notice">
      <span className="offline-notice__icon"><PlugZap size={18} /></span>
      <div>
        <strong>{title}</strong>
        <p>
          {message ||
            `Could not connect to the API, so ${label} can't be loaded right now. Start the backend service, then retry.`}
        </p>
      </div>
      {onRetry && <button type="button" className="select-button" onClick={onRetry}><RotateCw size={13} />Re
try</button>}
    </div>
  )
}
