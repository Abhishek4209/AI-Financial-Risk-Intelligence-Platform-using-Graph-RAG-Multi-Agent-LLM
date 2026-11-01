
import { ArrowUpRight, Search, ShieldAlert } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  createCase,
  friendlyErrorMessage,
  getCases,
  getCustomers,
  isNetworkError,
} from '../services/riskApi'
import {
  BackendOfflineNotice,
  CaseDetailsModal,
  Modal,
} from '../components'
import { useToast } from '../hooks/useToast'

function severityTone(severity) {
  if (severity === 'high') return 'high'
  if (severity === 'medium') return 'medium'
  return 'low'
}

function toCaseRow(item) {
  return {
    id: item.id,
    name: item.customer_id || 'Unassigned customer',
    type: item.case_type,
    owner: item.owner || 'Unassigned',
    score: item.severity,
    status: item.status,
    tone: severityTone(item.severity),
    case_type: item.case_type,
    severity: item.severity,
    customer_id: item.customer_id,
    summary: item.summary,
    created_at: item.created_at,
  }
}

export default function RiskCases() {
  const [cases, setCases] = useState([])
  const [customers, setCustomers] = useState([])
  const [customersLoading, setCustomersLoading] = useState(true)
  const [error, setError] = useState(null)
  const [customerError, setCustomerError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [query, setQuery] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [selectedCase, setSelectedCase] = useState(null)
  const { notify } = useToast()

  useEffect(() => {
    setError(null)
    setCustomerError(null)

    getCases()
      .then((rows) => setCases(rows.map(toCaseRow)))
      .catch(setError)

    setCustomersLoading(true)
    getCustomers({ page_size: 100 })
      .then(setCustomers)
      .catch(setCustomerError)
      .finally(() => setCustomersLoading(false))
  }, [reloadKey])

  const customerNames = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer.name])),
    [customers],
  )
  const filteredCases = cases.filter((item) =>
    [
      customerNames.get(item.name) || item.name,
      item.type,
      item.owner,
      item.status,
    ]
      .join(' ')
      .toLowerCase()
      .includes(query.trim().toLowerCase()),
  )

  async function handleCreateCase(event) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    setSaving(true)
    setCreateError(null)

    try {
      await createCase({
        customer_id: String(formData.get('customer_id')),
        case_type: String(formData.get('case_type')),
        reason: String(formData.get('reason')).trim(),
      })
      setCreating(false)
      setReloadKey((key) => key + 1)
      notify('Risk case opened.', { tone: 'success' })
    } catch (submitError) {
      setCreateError(submitError)
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / CASE MANAGEMENT</p>
          <h1>Risk cases</h1>
          <p className="heading-copy">
            Review, assign, and track portfolio risk investigations.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={() => {
            setCreateError(null)
            setCreating(true)
          }}
        >
          <ShieldAlert size={16} />
          Open a case
        </button>
      </div>

      {error &&
        (isNetworkError(error) ? (
          <BackendOfflineNotice
            label="risk cases"
            onRetry={() => setReloadKey((key) => key + 1)}
          />
        ) : (
          <p className="empty-state empty-state--warning">
            Could not load cases: {error.message}
          </p>
        ))}

      <div className="panel cases-panel">
        <div className="panel-heading">
          <div>
            <h2>Active investigations</h2>
            <p>
              {cases.length} cases currently in your workspace
            </p>
          </div>

          <label className="filter-control">
            <Search size={15} />
            <input
              type="search"
              aria-label="Search cases"
              placeholder="Search cases"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Case type</th>
                <th>Owner</th>
                <th>Risk score</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>

            <tbody>
              {filteredCases.map((item) => (
                <tr key={item.id || item.name}>
                  <td>
                    <div className="account-cell">
                      <span className="company-avatar">
                        {(customerNames.get(item.name) || item.name)
                          .slice(0, 2)
                          .toUpperCase()}
                      </span>
                      <strong>{customerNames.get(item.name) || item.name}</strong>
                    </div>
                  </td>

                  <td>{item.type}</td>
                  <td>{item.owner}</td>

                  <td>
                    <span
                      className={`table-score table-score--${item.tone}`}
                    >
                      {item.score}
                    </span>
                  </td>

                  <td>
                    <span className={`status status--${item.tone}`}>
                      {item.status}
                    </span>
                  </td>

                  <td>
                    <button
                      className="text-button"
                      aria-label={`Open ${customerNames.get(item.name) || item.name}`}
                      onClick={() => setSelectedCase(item)}
                    >
                      Open
                      <ArrowUpRight size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredCases.length === 0 && (
            <p className="empty-state">
              {query ? 'No cases match that search.' : 'No cases recorded yet.'}
            </p>
          )}
        </div>
      </div>

      {customerError && (
        <p className="empty-state empty-state--warning" role="alert">
          Could not load customers for case creation:{' '}
          {friendlyErrorMessage(customerError)}
        </p>
      )}

      {creating && (
        <Modal title="Open a risk case" onClose={() => {
          if (!saving) setCreating(false)
        }}>
          {customersLoading ? (
            <p className="empty-state" aria-live="polite">
              Loading customers…
            </p>
          ) : customerError ? (
            <div>
              <p className="empty-state empty-state--warning" role="alert">
                {friendlyErrorMessage(customerError, 'Could not load customers.')}
              </p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="select-button"
                  onClick={() => setReloadKey((key) => key + 1)}
                >
                  Retry
                </button>
              </div>
            </div>
          ) : customers.length === 0 ? (
            <>
              <p className="empty-state">
                Add a customer before opening a case.
              </p>
              <div className="modal-actions">
                <Link className="primary-button" to="/customers">
                  Go to customers
                </Link>
              </div>
            </>
          ) : (
            <form className="modal-form" onSubmit={handleCreateCase}>
              <label className="risk-form__field">
                <span>Customer</span>
                <select name="customer_id" required defaultValue="">
                  <option value="" disabled>Select a customer</option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="risk-form__field">
                <span>Case type</span>
                <select name="case_type" required defaultValue="fraud">
                  <option value="fraud">Fraud</option>
                  <option value="credit">Credit risk</option>
                  <option value="compliance">Compliance</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label className="risk-form__field">
                <span>Reason</span>
                <textarea name="reason" required maxLength={4000} rows={4} />
              </label>
              {createError && (
                <p className="empty-state empty-state--warning" role="alert">
                  {friendlyErrorMessage(createError, 'Could not open case.')}
                </p>
              )}
              <div className="modal-actions">
                <button
                  type="button"
                  className="select-button"
                  onClick={() => setCreating(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button type="submit" className="primary-button" disabled={saving}>
                  {saving ? 'Opening...' : 'Open case'}
                </button>
              </div>
            </form>
          )}
        </Modal>
      )}

      {selectedCase && (
        <CaseDetailsModal
          caseDetails={selectedCase}
          onClose={() => setSelectedCase(null)}
        />
      )}
    </section>
  )
}
