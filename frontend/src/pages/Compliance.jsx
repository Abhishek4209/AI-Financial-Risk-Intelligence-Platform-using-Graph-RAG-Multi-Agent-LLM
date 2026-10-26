
import { useState } from 'react'
import { Search } from 'lucide-react'
import {
  askCompliance,
  friendlyErrorMessage,
  isNetworkError,
} from '../services/riskApi'
import { useToast } from '../hooks/useToast'
import { BackendOfflineNotice, EvidenceList } from '../components'

export default function Compliance() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const { notify } = useToast()

  async function handleSubmit(event) {
    event?.preventDefault()

    if (!question.trim()) return

    setLoading(true)
    setError(null)

    try {
      const result = await askCompliance(question)

      setHistory((current) => [
        { question, ...result },
        ...current,
      ])

      setQuestion('')
    } catch (submitError) {
      setError(submitError)

      notify(
        friendlyErrorMessage(
          submitError,
          'Compliance query failed.',
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
          <p className="eyebrow">WORKSPACE / COMPLIANCE</p>
          <h1>Regulatory Q&amp;A</h1>
          <p className="heading-copy">
            Answers are grounded only in retrieved regulatory documents;
            insufficient evidence is stated explicitly.
          </p>
        </div>
      </section>

      <article className="panel">
        <form className="rag-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="e.g. What KYC documentation is required for high-risk customers?"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />

          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            <Search size={16} />
            {loading ? 'Searching...' : 'Ask'}
          </button>
        </form>

        {error &&
          (isNetworkError(error) ? (
            <BackendOfflineNotice
              label="compliance answers"
              onRetry={handleSubmit}
            />
          ) : (
            <p className="empty-state empty-state--warning">
              {error.message}
            </p>
          ))}

        <div className="rag-history">
          {history.length === 0 && !loading && (
            <p className="empty-state">
              No questions asked yet.
            </p>
          )}

          {history.map((entry, index) => (
            <div
              className="rag-entry"
              key={`${entry.question}-${index}`}
            >
              <p className="rag-entry__question">
                {entry.question}
              </p>

              <p
                className={`rag-entry__answer ${
                  entry.grounded
                    ? ''
                    : 'rag-entry__answer--ungrounded'
                }`}
              >
                {entry.answer}
              </p>

              {!entry.evidence_sufficient && (
                <p className="empty-state empty-state--warning">
                  Insufficient evidence was retrieved for this question.
                </p>
              )}

              {entry.sources?.length > 0 && (
                <EvidenceList
                  evidence={entry.sources.map((source) => ({
                    source,
                    text: '',
                  }))}
                />
              )}
            </div>
          ))}
        </div>
      </article>
    </section>
  )
}
