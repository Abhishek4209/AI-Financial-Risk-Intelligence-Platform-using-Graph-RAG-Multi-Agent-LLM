import { useEffect, useState } from 'react'
import { friendlyErrorMessage, getCustomer } from '../services/riskApi'
import Modal from './Modal'

export default function CustomerDetailsModal({ customerId, onClose }) {
  const [customer, setCustomer] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true

    getCustomer(customerId)
      .then((result) => {
        if (active) setCustomer(result)
      })
      .catch((requestError) => {
        if (active) setError(requestError)
      })

    return () => {
      active = false
    }
  }, [customerId])

  return (
    <Modal title={customer?.name || 'Customer details'} onClose={onClose}>
      {!customer && !error && (
        <p className="empty-state" aria-live="polite">
          Loading customer details…
        </p>
      )}
      {error && (
        <p className="empty-state empty-state--warning" role="alert">
          {friendlyErrorMessage(error, 'Could not load customer details.')}
        </p>
      )}
      {customer && (
        <dl className="detail-list">
          <div>
            <dt>Segment</dt>
            <dd>{customer.segment || 'Not specified'}</dd>
          </div>
          <div>
            <dt>Customer ID</dt>
            <dd>{customer.id}</dd>
          </div>
          {customer.created_at && (
            <div>
              <dt>Added</dt>
              <dd>{new Date(customer.created_at).toLocaleString()}</dd>
            </div>
          )}
        </dl>
      )}
    </Modal>
  )
}
