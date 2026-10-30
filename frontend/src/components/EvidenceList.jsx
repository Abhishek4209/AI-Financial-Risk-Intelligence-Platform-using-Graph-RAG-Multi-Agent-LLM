export default function EvidenceList({ evidence = [] }) {
  if (!evidence.length) {
    return <p className="empty-state">No evidence was retrieved; this is explicitly insufficient to support 
a conclusion.</p>
  }
  return (
    <div className="evidence-list">
      {evidence.map((item, index) => (
        <div className="evidence-item" key={'${item.source}-${index}'}>
          <strong>
            {item.organization ? '${item.organization}: ' : ''}
            {item.source}
            {item.page != null ? ', page ${item.page}' : ''}
          </strong>
          <p>{item.text}</p>
        </div>
      ))}
    </div>
  )
}
