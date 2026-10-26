const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Detect network errors when the backend cannot be reached.
export function isNetworkError(error) {
  return (
    error instanceof TypeError ||
    /failed to fetch|networkerror|load failed/i.test(error?.message || '')
  );
}

export function friendlyErrorMessage(
  error,
  fallback = 'Something went wrong.'
) {
  if (isNetworkError(error)) {
    return `Backend unreachable at ${API_BASE_URL}. Start the API and try again.`;
  }

  return error?.message || fallback;
}

// Used when the backend is unreachable, so the dashboard can render in local development.
export const mockOverview = {
  total_cases: 4,
  open_cases: 2,
  total_transactions: 128,
  case_breakdown: {
    high: 1,
    medium: 1,
    informational: 2,
  },
  exposure_under_review: 24800000,
  monthly_case_trend: [
    { month: 'May 2026', count: 1 },
    { month: 'Jun 2026', count: 1 },
    { month: 'Jul 2026', count: 0 },
    { month: 'Aug 2026', count: 1 },
    { month: 'Sep 2026', count: 0 },
    { month: 'Oct 2026', count: 1 },
  ],
  recent_cases: [],
  isMock: true,
};

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));

    const error = new Error(
      body.detail || `Request failed with status ${response.status}`
    );

    error.status = response.status;
    throw error;
  }

  return response.json();
}

function postJson(path, payload) {
  return request(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export async function getOverview({ useMock = true } = {}) {
  try {
    return await request('/api/overview');
  } catch (error) {
    if (!useMock) {
      throw error;
    }

    return mockOverview;
  }
}

export async function getCases(params = {}) {
  const query = new URLSearchParams(params).toString();
  const suffix = query ? `?${query}` : '';

  return request('/api/cases' + suffix);
}

export async function createCase(payload) {
  return postJson('/api/cases', payload);
}

export async function getCustomers(params = {}) {
  const query = new URLSearchParams(params).toString();
  const suffix = query ? `?${query}` : '';

  return request('/api/customers' + suffix);
}

export async function assessCreditRisk({ dataset, applicant }) {
  return postJson('/predict/credit-risk', {
    dataset,
    applicant,
  });
}

export async function assessFraud({ transaction, accountId }) {
  return postJson('/predict/fraud', {
    transaction,
    account_id: accountId || null,
  });
}

// Scores a transaction with saved local fraud models.
export async function predictFraudModels({ transaction }) {
  return postJson('/predict/fraud-models', {
    transaction,
  });
}

export async function investigateTransaction({
  transaction,
  accountId,
  caseId,
}) {
  return postJson('/investigation', {
    transaction,
    account_id: accountId || null,
    case_id: caseId || null,
  });
}

export async function askCompliance(question, topK = 5) {
  return postJson('/compliance/query', {
    question,
    top_k: topK,
  });
}

export async function askRag(question, topK = 5) {
  return postJson('/rag/query', {
    question,
    top_k: topK,
  });
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  return request('/api/documents', {
    method: 'POST',
    body: formData,
  });
}
