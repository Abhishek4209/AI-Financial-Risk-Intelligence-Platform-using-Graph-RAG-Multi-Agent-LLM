
import { useEffect, useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import {
  friendlyErrorMessage,
  getIeeeFraudModelSchema,
  isNetworkError,
  predictFraudModels,
} from '../services/riskApi'
import { useToast } from '../hooks/useToast'
import {
  BackendOfflineNotice,
  RiskBadge,
  ShapDriverChart,
} from '../components'

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

function ModelFeatureInput({ feature, value, onChange }) {
  const label = `${feature.name}${feature.required ? ' (required)' : ''}`

  return (
    <label className="risk-form__field" key={feature.name}>
      <span>{label}</span>
      {feature.input_type === 'category' ? (
        <select
          value={value ?? ''}
          onChange={(event) => onChange(feature.name, event.target.value)}
        >
          <option value="">Select category</option>
          {feature.categories.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      ) : (
        <input
          type="number"
          step="any"
          value={value ?? ''}
          onChange={(event) =>
            onChange(
              feature.name,
              event.target.value === '' ? '' : Number(event.target.value),
            )
          }
        />
      )}
    </label>
  )
}

function RawFeatureInput({ field, value, onChange }) {
  return (
    <label className="risk-form__field" key={field.name}>
      <span>
        {field.name}
        {field.required ? ' (required for preprocessing)' : ''}
      </span>
      <input
        type={field.input_type === 'number' ? 'number' : 'text'}
        step={field.input_type === 'number' ? 'any' : undefined}
        value={value ?? ''}
        onChange={(event) =>
          onChange(
            field.name,
            field.input_type === 'number'
              ? event.target.value === ''
                ? ''
                : Number(event.target.value)
              : event.target.value,
          )
        }
      />
    </label>
  )
}

export default function FraudDetection() {
  const [transaction, setTransaction] = useState(DEFAULT_TRANSACTION)
  const [ieeeFeatures, setIeeeFeatures] = useState({})
  const [ieeeSchema, setIeeeSchema] = useState(null)
  const [ieeeSchemaError, setIeeeSchemaError] = useState(null)
  const [schemaLoading, setSchemaLoading] = useState(true)
  const [outcome, setOutcome] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const { notify } = useToast()

  useEffect(() => {
    let active = true

    getIeeeFraudModelSchema()
      .then((schema) => {
        if (active) {
          setIeeeSchema(schema)
          setIeeeSchemaError(null)
        }
      })
      .catch((schemaError) => {
        if (active) {
          setIeeeSchemaError(schemaError)
        }
      })
      .finally(() => {
        if (active) {
          setSchemaLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [])

  function handleFieldChange(field, value) {
    setTransaction((current) => ({
      ...current,
      [field]: field === 'type' ? value : Number(value),
    }))
  }

  function handleIeeeFieldChange(field, value) {
    setIeeeFeatures((current) => ({
      ...current,
      [field]: value,
    }))
  }

  async function handleSubmit(event) {
    event?.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await predictFraudModels({
        transaction,
        ieeeFeatures: Object.fromEntries(
          Object.entries(ieeeFeatures).filter(([, value]) => value !== ''),
        ),
      })
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
  const primaryFeatures =
    ieeeSchema?.features.filter(
      (feature) => feature.required && !feature.derived,
    ) ?? []
  const additionalFeatures =
    ieeeSchema?.features.filter(
      (feature) => !feature.required && !feature.derived,
    ) ?? []

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
              <p>PaySim and IEEE-CIS inputs stay separate</p>
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

            <div style={{ gridColumn: '1 / -1' }}>
              <h3 className="panel-subheading">IEEE-CIS transaction inputs</h3>
              {schemaLoading && (
                <p className="empty-state">
                  Loading the saved model's feature schema...
                </p>
              )}
              {ieeeSchemaError && (
                <p className="empty-state empty-state--warning">
                  IEEE-CIS model unavailable:{' '}
                  {friendlyErrorMessage(
                    ieeeSchemaError,
                    'Could not load its feature schema.',
                  )}
                </p>
              )}
              {ieeeSchema && (
                <p className="heading-copy">
                  Connected to {ieeeSchema.model_file};{' '}
                  {ieeeSchema.feature_count} trained model features loaded.
                  Optional blank numeric features use the training value (
                  {ieeeSchema.missing_value_sentinel}); blank categories use
                  the saved missing category when available.
                </p>
              )}
            </div>

            {primaryFeatures.map((feature) => (
              <ModelFeatureInput
                key={feature.name}
                feature={feature}
                value={ieeeFeatures[feature.name]}
                onChange={handleIeeeFieldChange}
              />
            ))}

            {ieeeSchema?.raw_inputs.map((field) => (
              <RawFeatureInput
                key={field.name}
                field={field}
                value={ieeeFeatures[field.name]}
                onChange={handleIeeeFieldChange}
              />
            ))}

            {ieeeSchema && additionalFeatures.length > 0 && (
              <details
                style={{ gridColumn: '1 / -1' }}
                className="ieee-additional-features"
              >
                <summary>
                  Additional trained inputs ({additionalFeatures.length})
                </summary>
                <p className="heading-copy">
                  Enter available IEEE-CIS values only. Blank numeric values
                  follow the model's saved missing-value preprocessing.
                </p>
                <div className="risk-form">
                  {additionalFeatures.map((feature) => (
                    <ModelFeatureInput
                      key={feature.name}
                      feature={feature}
                      value={ieeeFeatures[feature.name]}
                      onChange={handleIeeeFieldChange}
                    />
                  ))}
                </div>
              </details>
            )}

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
              <p>Probability, risk band, and SHAP evidence</p>
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
                  <h4 className="panel-subheading">Top model factors</h4>
                  {prediction.shap_error ? (
                    <p className="empty-state empty-state--warning">
                      SHAP evidence unavailable: {prediction.shap_error}
                    </p>
                  ) : (
                    <ShapDriverChart
                      drivers={prediction.shap_drivers}
                    />
                  )}
                </>
              ) : (
                <p className="empty-state empty-state--warning">
                  Could not score this model: {prediction.reason}
                </p>
              )}
            </div>
          ))}
        </article>
      </div>
    </section>
  )
}
