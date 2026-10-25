import { useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import { assessFraudRisk } from '../services/riskApi'
import { EvidenceList, RiskBadge, ShapDriverChart } from '../components'

const INITIAL_TRANSACTION = {
  step: 1, type: 'TRANSFER', amount: 125000,
  oldbalanceOrg: 150000, newbalanceOrig: 25000,
  oldbalanceDest: 5000, newbalanceDest: 130000, account_id: '',
}
const TRANSACTION_TYPES = ['PAYMENT', 'TRANSFER', 'CASH_OUT', 'DEBIT', 'CASH_IN']
export default function FraudDetection() {
  const [transaction, setTransaction] = useState(INITIAL_TRANSACTION)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  function handleFieldChange(field, value) {
    setTransaction((current) => ({ ...current, [field]: field === 'type' || field === 'account_id' ? value : Number(value) }))
  }
  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true); setError(null); setResult(null)
    try { setResult(await assessFraudRisk(transaction)) }
    catch (submitError) { setError(submitError) }
    finally { setLoading(false) }
  }
  return (
    <section className="page-content">
      <section className="page-heading"><div><p className="eyebrow">WORKSPACE / FRAUD DETECTION</p><h1>Transaction fraud investigation</h1><p className="heading-copy">Review transaction signals. Demo results are illustrative and never block a transaction.</p></div></section>
      <div className="dashboard-grid">
        <article className="panel">
          <div className="panel-heading"><div><h2>Transaction details</h2><p>PaySim-shaped transaction fields</p></div></div>
          <form className="risk-form" onSubmit={handleSubmit}>
            <label className="risk-form__field"><span>step (hour index)</span><input type="number" value={transaction.step} onChange={(event) => handleFieldChange('step', event.target.value)} /></label>
            <label className="risk-form__field"><span>type</span><select value={transaction.type} onChange={(event) => handleFieldChange('type', event.target.value)}>{TRANSACTION_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
            {['amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest'].map((field) => <label className="risk-form__field" key={field}><span>{field}</span><input type="number" value={transaction[field]} onChange={(event) => handleFieldChange(field, event.target.value)} /></label>)}
            <label className="risk-form__field"><span>account_id (optional)</span><input type="text" value={transaction.account_id} onChange={(event) => handleFieldChange('account_id', event.target.value)} placeholder="Account reference" /></label>
            <button className="primary-button" type="submit" disabled={loading}><ShieldAlert size={16} />{loading ? 'Analyzing...' : 'Analyze transaction'}</button>
          </form>
          {error && <p className="empty-state empty-state--warning">{error.message}</p>}
        </article>
        <article className="panel">
          <div className="panel-heading"><div><h2>Fraud risk result</h2><p>Risk score, key factors, and evidence.</p></div></div>
          {!result ? <p className="empty-state">Submit transaction details to view a result.</p> : <>
            {result.isDemo && <p className="empty-state empty-state--warning">Demo result: backend model unavailable.</p>}
            <p className="metric-label">Risk band</p><RiskBadge band={result.risk_band || result.band || 'MEDIUM'} />
            <strong className="metric-value">{result.risk_score ?? result.score ?? Math.round((result.probability || 0) * 100)} / 100</strong>
            <ShapDriverChart drivers={result.drivers || result.shap_values || []} />
            <EvidenceList evidence={result.evidence || []} />
          </>}
        </article>
      </div>
    </section>
  )
}
