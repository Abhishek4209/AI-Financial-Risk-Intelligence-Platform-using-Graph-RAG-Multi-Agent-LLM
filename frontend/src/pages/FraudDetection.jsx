
import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import {
  friendlyErrorMessage,
  isNetworkError,
  predictFraudModels,
} from '../services/riskApi'
import { useToast } from '../hooks/useToast'
import { BackendOfflineNotice, RiskBadge } from '../components'

const TRANSACTION_TYPES = [
  'CASH_IN',
  'CASH_OUT',
  'DEBIT',
  'PAYMENT',
  'TRANSFER',
]

// Labels only; the dataset key itself comes from the saved model artifact, not from this UI.
const MODEL_LABELS = {
  paysim: 'PaySim mobile-money model',
  ieee_cis: 'IEEE-CIS transaction model',
}

const DEFAULT_TRANSACTION = {
  step: 49,
  type: 'TRANSFER',
  amount: 850000,
  oldbalanceOrg: 900000,
  newbalanceOrig: 50000,
  oldbalanceDest: 10000,
  newbalanceDest: 860000,
}

export default function FraudDetection() {
  const [transaction, setTransaction] = useState(DEFAULT_TRANSACTION)
  const [outcome, setOutcome] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const { notify } = useToast()

  function handleFieldChange(field, value) {
    setTransaction((current) => ({
      ...current,
      [field]: field === 'type' ? value : Number(value),
    }))
  }

  async function handleSubmit(event) {
    event?.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await predictFraudModels({ transaction })
      setOutcome(response)
      notify('Model scoring complete.', { tone: 'success' })
    } catch (submitError) {
      setError(submitError)
      notify(
        friendlyErrorMessage(
          submitError,
          'Model scoring failed.',
        ),
        { tone: 'error' },
      )
    } finally {
      setLoading(false)
    }
  }

  const predictions = outcome?.predictions ?? []

  return (
    <section className="page-content">
      <section className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / FRAUD DETECTION</p>
          <h1>Transaction fraud investigation</h1>
          <p className="heading-copy">
            Scores the transaction with every saved local fraud model;
            no retrieval, no generated report, no external API.
          </p>
        </div>
      </section>

      <div className="dashboard-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <h2>Transaction details</h2>
              <p>PaySim-shaped transaction fields</p>
            </div>
          </div>

          <form className="risk-form" onSubmit={handleSubmit}>
            <label className="risk-form__field">
              <span>step (hour index)</span>
              <input
                type="number"
                value={transaction.step}
                onChange={(event) =>
                  handleFieldChange('step', event.target.value)
                }
              />
            </label>

            <label className="risk-form__field">
              <span>type</span>
              <select
                value={transaction.type}
                onChange={(event) =>
                  handleFieldChange('type', event.target.value)
                }
              >
                {TRANSACTION_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>

            <label className="risk-form__field">
              <span>amount</span>
              <input
                type="number"
                value={transaction.amount}
                onChange={(event) =>
                  handleFieldChange('amount', event.target.value)
                }
              />
            </label>

            <label className="risk-form__field">
              <span>oldbalanceOrg</span>
              <input
                type="number"
                value={transaction.oldbalanceOrg}
                onChange={(event) =>
                  handleFieldChange('oldbalanceOrg', event.target.value)
                }
              />
            </label>

            <label className="risk-form__field">
              <span>newbalanceOrig</span>
              <input
                type="number"
                value={transaction.newbalanceOrig}
                onChange={(event) =>
                  handleFieldChange('newbalanceOrig', event.target.value)
                }
              />
            </label>

            <label className="risk-form__field">
              <span>oldbalanceDest</span>
              <input
                type="number"
                value={transaction.oldbalanceDest}
                onChange={(event) =>
                  handleFieldChange('oldbalanceDest', event.target.value)
                }
              />
            </label>

            <label className="risk-form__field">
              <span>newbalanceDest</span>
              <input
                type="number"
                value={transaction.newbalanceDest}
                onChange={(event) =>
                  handleFieldChange('newbalanceDest', event.target.value)
                }
              />
            </label>

            <button
              type="submit"
              className="primary-button"
              disabled={loading}
            >
              <ShieldAlert size={16} />
              {loading ? 'Scoring...' : 'Score transaction'}
            </button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <h2>Model predictions</h2>
              <p>Individual output from each saved fraud model</p>
            </div>
          </div>

          {error &&
            (isNetworkError(error) ? (
              <BackendOfflineNotice
                label="fraud model scoring"
                onRetry={handleSubmit}
              />
            ) : (
              <p className="empty-state empty-state--warning">
                {error.message}
              </p>
            ))}

          {!predictions.length && !error && (
            <p className="empty-state">
              Submit the form to run the fraud models.
            </p>
          )}

          {predictions.map((prediction) => (
            <div
              key={prediction.dataset}
              className="model-prediction"
            >
              <h3 className="panel-subheading">
                {MODEL_LABELS[prediction.dataset] ?? prediction.dataset}
              </h3>

              <p className="heading-copy">
                {prediction.model_file}
              </p>

              {prediction.status === 'ok' ? (
                <>
                  <div className="result-summary">
                    <strong className="metric-value">
                      {(prediction.fraud_risk_score * 100).toFixed(2)}%
                    </strong>
                    <RiskBadge band={prediction.risk_level} />
                  </div>

                  <p className="heading-copy">
                    {prediction.interpretation}
                  </p>
                </>
              ) : (
                <p className="empty-state empty-state--warning">
                  Not connected: {prediction.reason}
                </p>
              )}
            </div>
          ))}
        </article>
      </div>
    </section>
  )
}
