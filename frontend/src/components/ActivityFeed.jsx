export default function ActivityFeed({ items = [] }) {
  return (
    <div className="activity-feed">
      {items.map((item, index) => {
        const Icon = item.icon

        return (
          <div className="activity-item" key={item.id || index}>
            <span
              className={`activity-icon activity-icon--${item.tone || 'purple'}`}
            >
              {Icon && <Icon size={16} />}
            </span>

            <div className="activity-item__content">
              <p>{item.title}</p>
              {item.description && <span>{item.description}</span>}
              {item.time && <small>{item.time}</small>}
            </div>
          </div>
        )
      })}
    </div>
  )
}