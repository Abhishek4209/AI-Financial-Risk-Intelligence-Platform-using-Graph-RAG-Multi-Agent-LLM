
import { ArrowUpRight, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getCustomers, isNetworkError } from '../services/riskApi'
import { BackendOfflineNotice } from '../components'

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    setError(null)
    getCustomers().then(setCustomers).catch(setError)
  }, [reloadKey])

  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / RELATIONSHIPS</p>
          <h1>Customers</h1>
          <p className="heading-copy">
            Keep a clear view of every account in your portfolio.
          </p>
        </div>

        <button type="button" className="primary-button">
          <Users size={16} />
          Add customer
        </button>
      </div>

      {error &&
        (isNetworkError(error) ? (
          <BackendOfflineNotice
            label="customers"
            onRetry={() => setReloadKey((key) => key + 1)}
          />
        ) : (
          <p className="empty-state empty-state--warning">
            Could not load customers: {error.message}
          </p>
        ))}

      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Portfolio accounts</h2>
            <p>
              {customers.length} accounts connected to this workspace
            </p>
          </div>
        </div>

        {customers.length === 0 && !error && (
          <p className="empty-state">
            No customers recorded yet.
          </p>
        )}

        <div className="activity-list">
          {customers.map((customer) => (
            <div className="activity-item" key={customer.id}>
              <span className="activity-icon activity-icon--green">
                <Users size={16} />
              </span>

              <p>
                <strong>{customer.name}</strong>
                <span>
                  {customer.segment || 'Portfolio account'}
                </span>
              </p>

              <button
                type="button"
                className="text-button"
                aria-label={`Open ${customer.name}`}
              >
                <ArrowUpRight size={15} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
