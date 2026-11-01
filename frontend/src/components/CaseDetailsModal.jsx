import Modal from './Modal'

export default function CaseDetailsModal({ caseDetails, onClose }) {
  return (
    <Modal title="Risk case" onClose={onClose}>
      <dl className="detail-list">
        <div>
          <dt>Type</dt>
          <dd>{caseDetails.case_type}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{caseDetails.status}</dd>
        </div>
        <div>
          <dt>Severity</dt>
          <dd>{caseDetails.severity}</dd>
        </div>
        <div>
          <dt>Customer</dt>
          <dd>{caseDetails.customer_id || 'Unassigned'}</dd>
        </div>
        <div>
          <dt>Summary</dt>
          <dd>{caseDetails.summary || 'No summary provided'}</dd>
        </div>
        {caseDetails.created_at && (
          <div>
            <dt>Created</dt>
            <dd>{new Date(caseDetails.created_at).toLocaleString()}</dd>
          </div>
        )}
      </dl>
    </Modal>
  )
}
