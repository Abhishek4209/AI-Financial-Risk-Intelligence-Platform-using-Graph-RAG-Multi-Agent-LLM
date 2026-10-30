
import { useState } from 'react'
import { ShieldAlert, Sparkles } from 'lucide-react'
import {
  assessCreditRisk,
  friendlyErrorMessage,
  isNetworkError,
} from '../services/riskApi'
import { useToast } from '../hooks/useToast'
import {
  BackendOfflineNotice,
  RiskBadge,
  ShapDriverChart,
} from '../components'

const TAIWAN_DEFAULTS = {
  LIMIT_BAL: 200000,
  SEX: 1,
  EDUCATION: 2,
  MARRIAGE: 1,
  AGE: 35,
  PAY_0: 0,
  PAY_2: 0,
  PAY_3: 0,
  PAY_4: 0,
  PAY_5: 0,
  PAY_6: 0,
  BILL_AMT1: 15000,
  BILL_AMT2: 14000,
  BILL_AMT3: 13000,
  BILL_AMT4: 12000,
  BILL_AMT5: 11000,
  BILL_AMT6: 10000,
  PAY_AMT1: 2000,
  PAY_AMT2: 2000,
  PAY_AMT3: 2000,
  PAY_AMT4: 2000,
  PAY_AMT5: 2000,
  PAY_AMT6: 2000,
}

const LENDING_DEFAULTS = {
  loan_amount: 15000,
  annual_income: 65000,
  debt_to_income: 18.5,
  credit_score_low: 680,
  credit_score_high: 684,
  installment: 450,
  delinquencies_2yr: 0,
  inquiries_6m: 1,
  open_accounts: 8,
  public_records: 0,
  revolving_balance: 8500,
  revolving_utilization: 42.1,
  total_accounts: 14,
}

export default function CreditRisk() {
  const [dataset, setDataset] = useState('taiwan')
  const [applicant, setApplicant] = useState(TAIWAN_DEFAULTS)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const { notify } = useToast()

  function handleDatasetChange(nextDataset) {
    setDataset(nextDataset)
    setApplicant(
      nextDataset === 'taiwan'
        ? TAIWAN_DEFAULTS
        : LENDING_DEFAULTS,
    )
    setResult(null)
    setError(null)
  }

  function handleFieldChange(field, value) {
    setApplicant((current) => ({
      ...current,
      [field]: Number(value),
    }))
  }

  async function handleSubmit(event) {
    event?.preventDefault()
    setLoading(true)
    setError(null)

    try {
      setResult(await assessCreditRisk({ dataset, applicant }))
      notify('Credit risk assessment complete.', {
        tone: 'success',
      })
    } catch (submitError) {
      setError(submitError)
      notify(
        friendlyErrorMessage(
          submitError,
          'Credit risk assessment failed.',
        ),
        { tone: 'error' },
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="page-content">
      <section className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / CREDIT RISK</p>
          <h1>Credit risk assessment</h1>
          <p className="heading-copy">
            Scores the applicant with the dataset's own trained model;
            this is decision support, not an automated lending decision.
          </p>
        </div>
      </section>

      <div className="dashboard-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <h2>Applicant inputs</h2>
              <p>Values map directly to the model's trained features</p>
            </div>
          </div>

          <div className="form-tabs">
            <button
              type="button"
              className={`select-button ${
                dataset === 'taiwan' ? 'select-button--active' : ''
              }`}
              onClick={() => handleDatasetChange('taiwan')}
            >
              Taiwan credit card
            </button>

            <button
              type="button"
              className={`select-button ${
                dataset === 'lending_club'
                  ? 'select-button--active'
                  : ''
              }`}
              onClick={() => handleDatasetChange('lending_club')}
            >
              Lending Club
            </button>
          </div>

          <form className="risk-form" onSubmit={handleSubmit}>
            {Object.entries(applicant).map(([field, value]) => (
              <label className="risk-form__field" key={field}>
                <span>{field}</span>
                <input
                  type="number"
                  step="any"
                  value={value}
                  onChange={(event) =>
                    handleFieldChange(field, event.target.value)
                  }
                />
              </label>
            ))}

            <button
              type="submit"
              className="primary-button"
              disabled={loading}
            >
              <ShieldAlert size={16} />
              {loading ? 'Scoring...' : 'Score applicant'}
            </button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <h2>Model result</h2>
              <p>Probability, risk band, and SHAP evidence</p>
            </div>
          </div>

          {error &&
            (isNetworkError(error) ? (
              <BackendOfflineNotice
                label="a credit risk score"
                onRetry={handleSubmit}
              />
            ) : (
              <p className="empty-state empty-state--warning">
                {error.message}
              </p>
            ))}

          {!result && !error && (
            <p className="empty-state">
              Submit the form to run the model.
            </p>
          )}

          {result && (
            <>
              <div className="result-summary">
                <strong className="metric-value">
                  {(result.default_probability * 100).toFixed(1)}%
                </strong>
                <RiskBadge band={result.risk_band} />
              </div>

              <div className="ai-summary-card">
                <span className="ai-summary-card__icon">
                  <Sparkles size={15} />
                </span>
                <p>{result.interpretation}</p>
              </div>

              {result.recommended_for_review && (
                <p className="empty-state empty-state--warning">
                  Recommended for human review.
                </p>
              )}

              <h3 className="panel-subheading">Top model factors</h3>
              <ShapDriverChart drivers={result.shap_drivers} />
            </>
          )}
        </article>
      </div>
    </section>
  )
}
