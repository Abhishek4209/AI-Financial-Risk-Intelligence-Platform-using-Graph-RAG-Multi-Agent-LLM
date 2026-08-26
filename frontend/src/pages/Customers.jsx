import { ArrowUpRight, Users } from 'lucide-react'

const customers = ['Northstar Logistics', 'Meridian Wholesale', 'Atlas Energy Partners', 'Verity Health Systems']

export default function Customers() {
  return <section className="page-content"><div className="page-heading"><div><p className="eyebrow">WORKSPACE / RELATIONSHIPS</p><h1>Customers</h1><p className="heading-copy">Keep a clear view of every account in your portfolio.</p></div><button className="primary-button"><Users size={16} />Add customer</button></div><div className="panel"><div className="panel-heading"><div><h2>Portfolio accounts</h2><p>{customers.length} accounts connected to this workspace</p></div></div><div className="activity-list">{customers.map((customer) => <div className="activity-item" key={customer}><span className="activity-icon activity-icon--green"><Users size={16} /></span><p><strong>{customer}</strong><span>Portfolio account</span></p><button className="text-button" aria-label={`Open ${customer}`}><ArrowUpRight size={15} /></button></div>)}</div></div></section>
}
