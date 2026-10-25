import { ArrowUpRight, FileSearch, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { uploadDocument } from '../services/riskApi'

export default function Documents() {
  const fileInputRef = useRef(null)
  const [uploads, setUploads] = useState([])
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)

  async function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true); setError(null)
    try {
      const result = await uploadDocument(file)
      setUploads((current) => [result, ...current])
    } catch (uploadError) { setError(uploadError) }
    finally { setUploading(false); event.target.value = '' }
  }

  return (
    <section className="page-content">
      <div className="page-heading">
        <div><p className="eyebrow">WORKSPACE / KNOWLEDGE</p><h1>Documents</h1><p className="heading-copy">Select a document to test the upload flow. Indexing requires a connected backend.</p></div>
        <button className="primary-button" onClick={() => fileInputRef.current?.click()} disabled={uploading}><Upload size={16} />{uploading ? 'Uploading...' : 'Upload document'}</button>
        <input ref={fileInputRef} type="file" hidden accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.xls" onChange={handleFileChange} />
      </div>
      {error && <p className="empty-state empty-state--warning">Upload failed: {error.message}</p>}
      <div className="panel">
        <div className="panel-heading"><div><h2>Selected this session</h2><p>Files appear here for this browser session.</p></div></div>
        {uploads.length === 0 && <p className="empty-state">No documents selected yet.</p>}
        <div className="activity-list">
          {uploads.map((doc) => <div className="activity-item" key={doc.document_id}>
            <span className="activity-icon activity-icon--purple"><FileSearch size={16} /></span>
            <p><strong>{doc.document_name}</strong><span>{doc.status} - {doc.chunks_indexed || 0} chunks{doc.vector_indexed ? ' - vector indexed' : ''}</span></p>
            <ArrowUpRight size={15} />
          </div>)}
        </div>
      </div>
    </section>
  )
}
