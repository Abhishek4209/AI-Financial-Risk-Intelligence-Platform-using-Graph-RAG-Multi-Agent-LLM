import { useState } from 'react'
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  FileText,
  LoaderCircle,
  MessageSquareText,
  Scale,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import {
  askCompliance,
  friendlyErrorMessage,
  isNetworkError,
} from '../services/riskApi'
import { useToast } from '../hooks/useToast'
import { BackendOfflineNotice } from '../components'
import './Compliance.css'

const exampleQuestions = [
  'What is KYC and why is it important?',
  'What is AML?',
  'What is the purpose of FATF guidelines?',
  'What is the difference between suspicious and high-value transactions?',
  'What should I do when a compliance alert is triggered?',
]

function getGroundingLabel(result) {
  if (!result) return 'Not confirmed'
  if (!result.evidence_sufficient) return 'Insufficient evidence'
  return result.grounded ? 'Grounded in evidence' : 'Not grounded'
}

function ComplianceSources({ sources = [] }) {
  if (!sources.length) {
    return (
      <p className="compliance-no-sources">
        No source citations were returned for this response.
      </p>
    )
  }

  return (
    <ul className="compliance-source-list">
      {sources.map((source, index) => (
        <li key={`${source}-${index}`}>{source}</li>
      ))}
    </ul>
  )
}

export default function Compliance() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const { notify } = useToast()
  const latestResult = history[0]

  async function handleSubmit(event) {
    event?.preventDefault()
    const submittedQuestion = question.trim()

    if (!submittedQuestion || loading) return

    setLoading(true)
    setError(null)

    try {
      const result = await askCompliance(submittedQuestion)
      setHistory((current) => [
        { question: submittedQuestion, ...result },
        ...current,
      ])
      setQuestion('')
    } catch (submitError) {
      setError(submitError)
      notify(
        friendlyErrorMessage(submitError, 'Compliance query failed.'),
        { tone: 'error' },
      )
    } finally {
      setLoading(false)
    }
  }

  function chooseExample(example) {
    setQuestion(example)
    setError(null)
  }

  return (
    <section className="page-content compliance-page">
      <header className="compliance-header">
        <div className="compliance-header__main">
          <div className="compliance-header__icon" aria-hidden="true">
            <Scale size={27} />
          </div>
          <div>
            <p className="eyebrow">WORKSPACE / COMPLIANCE</p>
            <h1>Regulatory Q&amp;A</h1>
            <p className="heading-copy">
              Get source-backed answers from your indexed regulatory and
              compliance documents.
            </p>
          </div>
        </div>
        <span className="compliance-workspace-badge">
          <CheckCircle2 size={15} />
          Compliance workspace
        </span>
      </header>

      <div className="compliance-layout">
        <aside className="compliance-sidebar">
          <section className="panel compliance-question-card">
            <h2 className="compliance-section-title">
              <MessageSquareText size={17} />
              Ask a Question
            </h2>
            <form onSubmit={handleSubmit}>
              <label className="compliance-sr-only" htmlFor="compliance-question">
                Ask a compliance question
              </label>
              <textarea
                id="compliance-question"
                className="compliance-textarea"
                placeholder="e.g. What KYC documentation is required for high-risk customers?"
                value={question}
                onChange={(event) => {
                  setQuestion(event.target.value)
                  if (error) setError(null)
                }}
                maxLength={2000}
                required
              />
              <button
                type="submit"
                className="primary-button compliance-submit"
                disabled={loading || !question.trim()}
              >
                {loading ? (
                  <LoaderCircle className="compliance-spinner" size={16} />
                ) : (
                  <Search size={16} />
                )}
                {loading ? 'Searching documents...' : 'Ask question'}
              </button>
            </form>

            {error && (
              <div className="compliance-error" role="alert">
                {isNetworkError(error) ? (
                  <BackendOfflineNotice
                    label="compliance answers"
                    onRetry={handleSubmit}
                  />
                ) : (
                  <p>{friendlyErrorMessage(error, 'Compliance query failed.')}</p>
                )}
              </div>
            )}

            <h3 className="compliance-examples-heading">
              <Sparkles size={15} />
              Popular Examples
            </h3>
            <div className="compliance-examples">
              {exampleQuestions.map((example) => (
                <button
                  type="button"
                  className="compliance-example"
                  key={example}
                  onClick={() => chooseExample(example)}
                >
                  <span>{example}</span>
                  <ArrowRight size={14} aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>

          <section className="compliance-powered">
            <div className="compliance-powered__icon" aria-hidden="true">
              <BookOpen size={22} />
            </div>
            <div>
              <h2>Powered by RAG</h2>
              <p>
                Answers use retrieved regulatory documents. Review the cited
                sources to verify the information.
              </p>
            </div>
          </section>
        </aside>

        <div className="compliance-results">
          <section className="panel compliance-answer-panel" aria-live="polite">
            {loading ? (
              <div className="compliance-welcome compliance-welcome--loading">
                <div className="compliance-welcome__icon" aria-hidden="true">
                  <LoaderCircle className="compliance-spinner" size={27} />
                </div>
                <h2>Searching regulatory documents</h2>
                <p>
                  Retrieving relevant evidence and preparing a source-backed
                  answer for your question.
                </p>
              </div>
            ) : latestResult ? (
              <div className="compliance-answer">
                <div className="compliance-answer__heading">
                  <div className="compliance-answer__icon" aria-hidden="true">
                    <FileText size={19} />
                  </div>
                  <div>
                    <p className="compliance-answer__eyebrow">LATEST RESPONSE</p>
                    <h2>{latestResult.question}</h2>
                  </div>
                  <span
                    className={`compliance-grounding ${
                      latestResult.grounded && latestResult.evidence_sufficient
                        ? 'compliance-grounding--supported'
                        : 'compliance-grounding--caution'
                    }`}
                  >
                    {latestResult.grounded && latestResult.evidence_sufficient
                      ? <CheckCircle2 size={14} />
                      : <ShieldCheck size={14} />}
                    {getGroundingLabel(latestResult)}
                  </span>
                </div>
                <p
                  className={`compliance-answer__text ${
                    !latestResult.grounded
                      ? 'compliance-answer__text--ungrounded'
                      : ''
                  }`}
                >
                  {latestResult.answer}
                </p>
                {!latestResult.evidence_sufficient && (
                  <p className="compliance-insufficient" role="status">
                    There was not enough retrieved evidence to support a
                    conclusion. Check the indexed documents or try a more
                    specific question.
                  </p>
                )}
                <div className="compliance-citations">
                  <h3>
                    Sources
                    <span>{latestResult.sources?.length ?? 0}</span>
                  </h3>
                  <ComplianceSources sources={latestResult.sources} />
                </div>
              </div>
            ) : (
              <div className="compliance-welcome">
                <div className="compliance-welcome__icon" aria-hidden="true">
                  <BookOpen size={29} />
                </div>
                <h2>Your regulatory answers, in one place</h2>
                <p>
                  Ask about KYC, AML, FATF guidelines, suspicious transactions,
                  or other requirements. Answers and references from your
                  indexed documents will appear here.
                </p>
                <span className="compliance-grounding compliance-grounding--supported">
                  <CheckCircle2 size={14} />
                  Answers are grounded in retrieved evidence
                </span>
                <p className="compliance-welcome__hint">
                  Choose a popular example or enter a question to get started.
                </p>
              </div>
            )}
          </section>

          <section className="compliance-metrics" aria-label="Query status">
            <div className="compliance-metric">
              <span><FileText size={15} /> Documents found</span>
              <strong>
                {latestResult ? `${latestResult.retrieved_count ?? 0} sources` : '— sources'}
              </strong>
            </div>
            <div className="compliance-metric">
              <span><Search size={15} /> Retrieval status</span>
              <strong>
                {loading ? 'Searching' : latestResult ? 'Complete' : 'Waiting for query'}
              </strong>
            </div>
            <div className="compliance-metric">
              <span><ShieldCheck size={15} /> Answer grounded</span>
              <strong>{getGroundingLabel(latestResult)}</strong>
            </div>
            <div className="compliance-metric">
              <span><BookOpen size={15} /> Source citations</span>
              <strong>
                {latestResult
                  ? `${latestResult.sources?.length ?? 0} citations`
                  : 'Unavailable'}
              </strong>
            </div>
          </section>

          {history.length > 1 && (
            <section className="panel compliance-history">
              <h2>Previous questions</h2>
              {history.slice(1).map((entry, index) => (
                <details
                  className="compliance-history__entry"
                  key={`${entry.question}-${index}`}
                >
                  <summary>{entry.question}</summary>
                  <p>{entry.answer}</p>
                  <span>{getGroundingLabel(entry)}</span>
                  <ComplianceSources sources={entry.sources} />
                </details>
              ))}
            </section>
          )}
        </div>
      </div>
    </section>
  )
}
