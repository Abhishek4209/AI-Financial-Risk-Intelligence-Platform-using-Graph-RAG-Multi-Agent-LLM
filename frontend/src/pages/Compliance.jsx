import { useState } from 'react'
import { Search } from 'lucide-react'
import { askCompliance } from '../services/riskApi'
import { EvidenceList } from '../components'

export default function Compliance() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!question.trim()) return
    setLoading(true); setError(null)
    try {
      const result = await askCompliance(question.trim())
      setHistory((current) => [{ question: question.trim(), ...result }, ...current])
      setQuestion('')
    } catch (submitError) { setError(submitError) }
    finally { setLoading(false) }
  }

  return (
    <section className="page-content">
      <section className="page-heading"><div><p className="eyebrow">WORKSPACE / COMPLIANCE</p><h1>Regulatory Q&amp;A</h1><p className="heading-copy">Ask questions about regulatory requirements. Connect the retrieval backend for source-grounded answers.</p></div></section>
      <article className="panel">
        <form className="rag-form" onSubmit={handleSubmit}>
          <input type="text" placeholder="e.g. What KYC documentation is required for high-risk customers?" value={question} onChange={(event) => setQuestion(event.target.value)} />
          <button type="submit" className="primary-button" disabled={loading || !question.trim()}><Search size={16} />{loading ? 'Searching...' : 'Ask'}</button>
        </form>
        {error && <p className="empty-state empty-state--warning">{error.message}</p>}
        <div className="rag-history">
          {history.length === 0 && !loading && <p className="empty-state">No questions asked yet.</p>}
          {history.map((entry, index) => (
            <div className="rag-entry" key={`${entry.question}-${index}`}>
              <p className="rag-entry__question">{entry.question}</p>
              <p className={`rag-entry__answer ${entry.grounded ? '' : 'rag-entry__answer--ungrounded'}`}>{entry.answer}</p>
              {!entry.evidence_sufficient && <p className="empty-state empty-state--warning">Insufficient evidence was retrieved for this question.</p>}
              <EvidenceList evidence={(entry.sources || []).map((source) => typeof source === 'string' ? ({ source, text: '' }) : source)} />
            </div>
          ))}
        </div>
      </article>
    </section>
  )
}
