
import { ArrowUpRight, FileSearch, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import {
  friendlyErrorMessage,
  isNetworkError,
  uploadDocument,
} from '../services/riskApi'
import { useToast } from '../hooks/useToast'
import { BackendOfflineNotice } from '../components'

export default function Documents() {
  const fileInputRef = useRef(null)
  const [uploads, setUploads] = useState([])
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)

  const { notify } = useToast()

  async function handleFileChange(event) {
    const file = event.target.files?.[0]

    if (!file) return

    setUploading(true)
    setError(null)

    try {
      const result = await uploadDocument(file)

      setUploads((current) => [result, ...current])

      notify(
        `${result.document_name} indexed with ${result.chunks_indexed} chunks.`,
        { tone: 'success' },
      )
    } catch (uploadError) {
      setError(uploadError)

      notify(
        friendlyErrorMessage(
          uploadError,
          'Document upload failed.',
        ),
        { tone: 'error' },
      )
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE / KNOWLEDGE</p>
          <h1>Documents</h1>
          <p className="heading-copy">
            Upload and index the evidence behind every risk decision.
          </p>
        </div>

        <button
          className="primary-button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          <Upload size={16} />
          {uploading ? 'Uploading...' : 'Upload document'}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          hidden
          accept=".pdf,.docx,.txt,.md,.csv,.xlsx,.xls"
          onChange={handleFileChange}
        />
      </div>

      {error &&
        (isNetworkError(error) ? (
          <BackendOfflineNotice label="document uploads" />
        ) : (
          <p className="empty-state empty-state--warning">
            Upload failed: {error.message}
          </p>
        ))}

      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Indexed this session</h2>
            <p>
              Chunked, embedded, and added to the retrieval index
            </p>
          </div>
        </div>

        {uploads.length === 0 && (
          <p className="empty-state">
            No documents uploaded yet in this session.
          </p>
        )}

        <div className="activity-list">
          {uploads.map((doc) => (
            <div className="activity-item" key={doc.document_id}>
              <span className="activity-icon activity-icon--purple">
                <FileSearch size={16} />
              </span>

              <p>
                <strong>{doc.document_name}</strong>
                <span>
                  {doc.status} - {doc.chunks_indexed} chunks
                  {doc.vector_indexed ? ' - vector indexed' : ''}
                </span>
              </p>

              <ArrowUpRight size={15} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
