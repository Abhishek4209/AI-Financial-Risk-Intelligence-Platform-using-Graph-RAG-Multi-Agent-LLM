import {
  CheckCircle2,
  ClipboardCopy,
  Download,
  FileSearch,
  Gauge,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from 'lucide-react'
import { useState } from 'react'
import RiskBadge from './RiskBadge'
const RISK_BANDS = ['HIGH', 'MEDIUM', 'LOW', 'BELOW_MODEL_THRESHOLD']
// Parses the backend's structured markdown (## title, ### sections, "- key: value" bullets,
// "> " disclaimer) into renderable sections; falls back to plain prose if nothing matches.
function parseReport(markdown = '') {
  const lines = markdown.split('\n')
  let title = ''
  let generatedAt = ''
  const sections = []
  const disclaimerLines = []
  let current = null
  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) continue
    if (line.startsWith('## ')) { title = line.slice(3).trim(); continue }
    if (line.startsWith('Generated:')) { generatedAt = line.replace('Generated:', '').trim(); contin
ue }
    if (line.startsWith('### ')) {
      current = { heading: line.replace(/^###\s*\d*\.?\s*/, '').trim(), bullets: [], paragraphs: [] 
}
      sections.push(current)
      continue
    }
    if (line.startsWith('>')) { disclaimerLines.push(line.replace(/^>\s*/, '')); continue }
    if (line.startsWith('- ')) {
      current?.bullets.push(line.slice(2).trim())
      continue
    }
    current?.paragraphs.push(line)
  }
  return { title, generatedAt, sections, disclaimer: disclaimerLines.join(' '), raw: markdown }
}
function findRiskBand(bullets = []) {
  for (const bullet of bullets) {
    const match = RISK_BANDS.find((band) => bullet.toUpperCase().includes(band))
    if (match) return match
  }
  return null
}
function sectionIcon(heading = '') {
  const value = heading.toLowerCase()
  if (value.includes('prediction')) return Gauge
  if (value.includes('evidence')) return FileSearch
  if (value.includes('explanation')) return Sparkles
  if (value.includes('review')) return ShieldAlert
  return CheckCircle2
}
function ModelPredictionSection({ section }) {
  const band = findRiskBand(section.bullets)
  return (
    <div className="ai-report__facts">
      {band && <RiskBadge band={band} />}
      <dl className="fact-grid">
        {section.bullets.map((bullet) => {
          const [key, ...rest] = bullet.split(':')
          return (
            <div className="fact-grid__row" key={bullet}>
              <dt>{key.trim()}</dt>
              <dd>{rest.join(':').trim()}</dd>
            </div>
          )
        })}
      </dl>
    </div>
  )
}
// Parses the backend's "**source**: text" bullet format without regex backtracking risk.
function splitEvidenceBullet(bullet) {
  if (bullet.startsWith('**')) {
    const closingIndex = bullet.indexOf('**', 2)
    if (closingIndex !== -1) {
      const source = bullet.slice(2, closingIndex)
      const text = bullet.slice(closingIndex + 2).trimStart().replace(/^:\s*/, '')
      return { source, text }
    }
  }
  return { source: null, text: bullet }
}
function EvidenceSection({ section }) {
  if (!section.bullets.length) return <p className="empty-state">No regulatory or document evidence was re
trieved; evidence is insufficient.</p>
  return (
    <div className="ai-report__evidence">
      {section.bullets.map((bullet, index) => {
        const { source, text } = splitEvidenceBullet(bullet)
        return (
          <div className="evidence-item" key={'${bullet}-${index}'}>
            <strong>{source || 'Source ${index + 1}'}</strong>
            <p>{text}</p>
          </div>
        )
      })}
    </div>
  )
}
function HumanReviewSection({ section }) {
  const flagged = section.bullets.some((bullet) => /true/i.test(bullet))
  return (
    <div className={'ai-report__alert ${flagged ? 'ai-report__alert--warning' : 'ai-report__alert--positive'
}'}>
      {flagged ? <TriangleAlert size={18} /> : <ShieldCheck size={18} />}
      <p>{flagged ? 'This case is recommended for human review before any action is taken.' : 'No human revi
ew flag was raised for this case.'}</p>
    </div>
  )
}
function GenericSection({ section }) {
  return (
    <>
      {section.paragraphs.map((paragraph, index) => <p className="ai-report__paragraph" key={'${paragraph
}-${index}'}>{paragraph}</p>)}
      {section.bullets.length > 0 && (
        <ul className="ai-report__list">
          {section.bullets.map((bullet, index) => <li key={'${bullet}-${index}'}>{bullet}</li>)}
        </ul>
      )}
    </>
  )
}
function renderSectionBody(section) {
  const heading = section.heading.toLowerCase()
  if (heading.includes('prediction')) return <ModelPredictionSection section={section} />
  if (heading.includes('evidence')) return <EvidenceSection section={section} />
  if (heading.includes('review')) return <HumanReviewSection section={section} />
  return <GenericSection section={section} />
}
export default function AIAnalysisReport({ report }) {
  const [copied, setCopied] = useState(false)
  if (!report?.content) return null
  const parsed = parseReport(report.content)
  const hasStructure = parsed.sections.length > 0
  async function handleCopy() {
    await navigator.clipboard.writeText(report.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  function handleDownload() {
    const blob = new Blob([report.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = '${report.case_id || 'investigation'}-report.md'
    anchor.click()
    URL.revokeObjectURL(url)
  }
  return (
    <article className="ai-report">
      <div className="ai-report__header">
        <div>
          <p className="eyebrow">AI-GENERATED INTELLIGENCE REPORT</p>
          <h3>{parsed.title || 'Analysis report'}</h3>
          {parsed.generatedAt && <p className="heading-copy">Generated {new Date(parsed.generatedAt).toLoc
aleString()}</p>}
        </div>
        <div className="ai-report__actions">
          <button type="button" className="select-button" onClick={handleCopy}><ClipboardCopy size={14} />{c
opied ? 'Copied' : 'Copy'}</button>
          <button type="button" className="select-button" onClick={handleDownload}><Download size={14} />Dow
nload</button>
        </div>
      </div>
      {hasStructure ? (
        parsed.sections.map((section) => {
          const Icon = sectionIcon(section.heading)
          return (
            <section className="ai-report__section" key={section.heading}>
              <h4><Icon size={15} />{section.heading}</h4>
              {renderSectionBody(section)}
            </section>
          )
        })
      ) : (
        <p className="ai-report__paragraph">{parsed.raw}</p>
      )}
      {parsed.disclaimer && (
        <div className="ai-report__disclaimer">
          <TriangleAlert size={14} />
          <span>{parsed.disclaimer}</span>
        </div>
      )}
    </article>
  )
}
