const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const mockOverview = {
  portfolioRiskScore: 68,
  exposureUnderReview: 24.8,
  exposureThresholdPercent: 68,
  openCases: 42,
  caseBreakdown: { high: 8, medium: 19, low: 15 },
  trend: [62, 58, 61, 49, 43, 42.6],
  distribution: { low: 48.2, medium: 24.9, high: 13.3 },
  cases: [
    { name: 'Northstar Logistics', type: 'Credit review', owner: 'A. Sharma', score: 82, status: 'Needs review', tone: 'high' },
    { name: 'Meridian Wholesale', type: 'Fraud investigation', owner: 'J. Wilson', score: 74, status: 'In progress', tone: 'medium' },
    { name: 'Atlas Energy Partners', type: 'Compliance check', owner: 'M. Chen', score: 61, status: 'Monitoring', tone: 'low' },
    { name: 'Verity Health Systems', type: 'Credit review', owner: 'R. Patel', score: 57, status: 'Monitoring', tone: 'low' },
  ],
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { Accept: 'application/json', ...options.headers },
  })
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
  return response.json()
}

export async function getOverview({ useMock = true } = {}) {
  try {
    return await request('/api/overview')
  } catch (error) {
    if (!useMock) throw error
    return { ...mockOverview, isMock: true }
  }
}

export async function getRiskCases() {
  const overview = await getOverview()
  return overview.cases
}
