import { PlugZap, RotateCw } from 'lucide-react'
export default function BackendOfflineNotice({ label = 'this data', onRetry }) {
  return (
    <div className="offline-notice">
      <span className="offline-notice__icon"><PlugZap size={18} /></span>
      <div>
        <strong>Backend unreachable</strong>
        <p>Could not connect to the API, so {label} can&apos;t be loaded right now. Start the backend servic
e, then retry.</p>
      </div>
      {onRetry && <button type="button" className="select-button" onClick={onRetry}><RotateCw size={13} />Re
try</button>}
    </div>
  )
}
