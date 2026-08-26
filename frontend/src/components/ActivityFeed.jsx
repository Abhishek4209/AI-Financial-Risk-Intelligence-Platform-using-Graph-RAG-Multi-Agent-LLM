import { FileSearch, ShieldAlert, Users } from 'lucide-react'

const iconMap = { report: FileSearch, customer: Users, case: ShieldAlert }

export default function ActivityFeed({ items = [] }) {
  return (
    <div className="activity-list">
      {items.map((item) => {
        const Icon = iconMap[item.kind] || FileSearch
        return (
          <div className="activity-item" key={item.id || `${item.title}-${item.time}`}>
            <span className={`activity-icon activity-icon--${item.tone || 'purple'}`}><Icon size={16} /></span>
            <p><strong>{item.title}</strong><span>{item.description}</span></p>
            <time>{item.time}</time>
          </div>
        )
      })}
    </div>
  )
}
