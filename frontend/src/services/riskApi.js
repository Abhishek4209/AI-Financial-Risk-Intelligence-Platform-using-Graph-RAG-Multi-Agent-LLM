const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const mockOverview = {
  total_cases: 24,
  open_cases: 9,
  total_transactions: 12840,
  case_breakdown: { high: 5, medium: 8, informational: 11 },
  exposure_under_review: 24800000,
  monthly_case_trend: [
    { month: 'May', count: 8 }, { month: 'Jun', count: 11 },
    { month: 'Jul', count: 9 }, { month: 'Aug', count: 14 },
    { month: 'Sep', count: 12 }, { month: 'Oct', count: 17 },
  ],
  recent_cases: [],
  isMock: true,
}

const mockCases = [
  { id: 'CASE-1042', customer_id: 'Northstar Capital', case_type: 'Fraud investigation', owner: 'A. Patel', severity: 'high', status: 'Open' },
  { id: 'CASE-1041', customer_id: 'Meridian Retail', case_type: 'Credit risk review', owner: 'R. Shah', severity: 'medium', status: 'Review' },
  { id: 'CASE-1040', customer_id: 'Bluehaven Group', case_type: 'Compliance review', owner: 'S. Rao', severity: 'low', status: 'Monitoring' },
  { id: 'CASE-1039', customer_id: 'Cedar Financial', case_type: 'Fraud investigation', owner: 'A. Patel', severity: 'high', status: 'Open' },
]
const mockCustomers = [
  { id: 'Northstar Capital', name: 'Northstar Capital', segment: 'Institutional' },
  { id: 'Meridian Retail', name: 'Meridian Retail', segment: 'Retail' },
  { id: 'Bluehaven Group', name: 'Bluehaven Group', segment: 'Commercial' },
  { id: 'Cedar Financial', name: 'Cedar Financial', segment: 'Institutional' },
]

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { Accept: 'application/json', ...options.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed with status ${response.status}`)
  }
  if (response.status === 204) return null
  return response.json()
}

function postJson(path, payload) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export async function getOverview({ useMock = true } = {}) {
  try {
    return await request('/api/overview')
  } catch (error) {
    if (!useMock) throw error
    return mockOverview
  }
}

export async function getCases(params = {}) {
  try {
    const query = new URLSearchParams(params).toString()
    const result = await request(`/api/cases${query ? `?${query}` : ''}`)
    return Array.isArray(result) ? result : (result.items || result.cases || [])
  } catch {
    return mockCases
  }
}

export async function createCase(payload) {
  return postJson('/api/cases', payload)
}

export async function getCustomers(params = {}) {
  try {
    const query = new URLSearchParams(params).toString()
    const result = await request(`/api/customers${query ? `?${query}` : ''}`)
    return Array.isArray(result) ? result : (result.items || result.customers || [])
  } catch {
    return mockCustomers
  }
}

export async function assessCreditRisk({ dataset, applicant }) {
  try {
    return await postJson('/predict/credit-risk', { dataset, applicant })
  } catch {
    const riskScore = Math.min(96, Math.max(8, Math.round(
      (Number(applicant.PAY_0 || 0) > 1 ? 68 : 28) +
      (Number(applicant.debt_to_income || 0) > 35 ? 18 : 0) +
      (Number(applicant.credit_score_low || 700) < 600 ? 24 : 0),
    )))
    return {
      dataset,
      risk_score: riskScore,
      risk_band: riskScore >= 67 ? 'HIGH' : riskScore >= 34 ? 'MEDIUM' : 'LOW',
      probability: riskScore / 100,
      drivers: [
        { feature: dataset === 'taiwan' ? 'PAY_0' : 'debt_to_income', shap_value: 0.42 },
        { feature: 'credit_history', shap_value: 0.24 },
        { feature: 'payment_amount', shap_value: -0.13 },
      ],
      isDemo: true,
    }
  }
}

export async function assessFraudRisk(transaction) {
  try {
    return await postJson('/predict/fraud', transaction)
  } catch {
    const amount = Number(transaction.amount || 0)
    const originBalance = Number(transaction.oldbalanceOrg || 0)
    const score = Math.min(98, Math.max(7, Math.round((amount > 100000 ? 75 : 22) + (originBalance < amount ? 17 : 0))))
    return {
      risk_score: score,
      risk_band: score >= 67 ? 'HIGH' : score >= 34 ? 'MEDIUM' : 'LOW',
      probability: score / 100,
      drivers: [
        { feature: 'transaction_amount', shap_value: amount > 100000 ? 0.51 : 0.12 },
        { feature: 'origin_balance', shap_value: originBalance < amount ? 0.37 : -0.11 },
      ],
      evidence: [],
      isDemo: true,
    }
  }
}

export async function askCompliance(question) {
  try {
    return await postJson('/api/compliance/ask', { question })
  } catch {
    return {
      answer: 'This local demo has no regulatory retrieval backend connected. Connect the API and indexed regulatory documents to receive a source-grounded answer.',
      grounded: false,
      evidence_sufficient: false,
      sources: [],
      isDemo: true,
    }
  }
}

export async function uploadDocument(file) {
  try {
    const formData = new FormData()
    formData.append('file', file)
    return await request('/api/documents/upload', { method: 'POST', body: formData })
  } catch {
    return {
      document_id: `${file.name}-${Date.now()}`,
      document_name: file.name,
      status: 'Selected (demo only)',
      chunks_indexed: 0,
      vector_indexed: false,
      isDemo: true,
    }
  }
}
