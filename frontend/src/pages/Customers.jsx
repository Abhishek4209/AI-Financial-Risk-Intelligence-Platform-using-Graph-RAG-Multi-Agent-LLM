
import { ArrowUpRight, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  createCustomer,
  friendlyErrorMessage,
  getCustomers,
  isNetworkError,
} from '../services/riskApi'
import {
  BackendOfflineNotice,
  CustomerDetailsModal,
  Modal,
} from '../components'
import { useToast } from '../hooks/useToast'

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [addingCustomer, setAddingCustomer] = useState(false)
  const [selectedCustomerId, setSelectedCustomerId] = useState(null)
  const [customerError, setCustomerError] = useState(null)
  const [saving, setSaving] = useState(false)
  const { notify } = useToast()

  useEffect(() => {
    setError(null)
    getCustomers().then(setCustomers).catch(setError)
  }, [reloadKey])

  async function handleAddCustomer(event) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const name = String(formData.get('name') || '').trim()
    const segment = String(formData.get('segment') || '').trim()
    setSaving(true)
    setCustomerError(null)

    try {
      const customer = await createCustomer({
        name,
        segment: segment || null,
      })
      setCustomers((current) => [customer, ...current])
      setAddingCustomer(false)
      notify(`${customer.name} was added to the portfolio.`, {
        tone: 'success',
      })
    } catch (submitError) {
      setCustomerError(submitError)
    } finally {
      setSaving(false)
    }
  }

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

        <button
          type="button"
          className="primary-button"
          onClick={() => {
            setCustomerError(null)
            setAddingCustomer(true)
          }}
        >
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
                onClick={() => setSelectedCustomerId(customer.id)}
              >
                <ArrowUpRight size={15} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {addingCustomer && (
        <Modal
          title="Add customer"
          onClose={() => {
            if (!saving) setAddingCustomer(false)
          }}
        >
          <form className="modal-form" onSubmit={handleAddCustomer}>
            <label className="risk-form__field">
              <span>Customer name</span>
              <input name="name" required maxLength={160} autoFocus />
            </label>
            <label className="risk-form__field">
              <span>Segment</span>
              <input name="segment" maxLength={64} placeholder="Retail, SME, etc." />
            </label>
            {customerError && (
              <p className="empty-state empty-state--warning" role="alert">
                {friendlyErrorMessage(customerError, 'Could not add customer.')}
              </p>
            )}
            <div className="modal-actions">
              <button
                type="button"
                className="select-button"
                onClick={() => setAddingCustomer(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button type="submit" className="primary-button" disabled={saving}>
                {saving ? 'Adding...' : 'Add customer'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {selectedCustomerId && (
        <CustomerDetailsModal
          customerId={selectedCustomerId}
          onClose={() => setSelectedCustomerId(null)}
        />
      )}

      {customerError && !addingCustomer && !selectedCustomerId && (
        <p className="empty-state empty-state--warning" role="alert">
          {friendlyErrorMessage(customerError, 'Could not load customer details.')}
        </p>
      )}
    </section>
  )
}
