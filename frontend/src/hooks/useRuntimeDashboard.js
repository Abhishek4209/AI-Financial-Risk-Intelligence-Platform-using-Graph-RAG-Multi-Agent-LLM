import { useEffect, useState } from 'react'
import { getCases, getCustomers, getOverview } from '../services/riskApi'

const TONE_RANK = { low: 0, medium: 1, high: 2 }

function severityTone(severity) {
  const value = String(severity || '').toLowerCase()
  if (value === 'high' || value === 'critical') return 'high'
  if (value === 'medium' || value === 'moderate') return 'medium'
  return 'low'
}

function categoryOf(caseType = '') {
  const value = String(caseType).toLowerCase()
  if (value.includes('fraud')) return 'fraud'
  if (value.includes('credit')) return 'credit'
  if (value.includes('complian')) return 'compliance'
  return 'other'
}

function buildIndicator(cases) {
  const counts = { low: 0, medium: 0, high: 0 }
  cases.forEach((item) => { counts[severityTone(item.severity)] += 1 })
  const total = cases.length
  const score = total ? Math.round(((counts.high + counts.medium * 0.5) / total) * 100) : 0
  const level = score >= (200 / 3) ? 'high' : score >= (100 / 3) ? 'medium' : 'low'
  return { counts, total, score, level }
}

export function useRuntimeDashboard() {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    let active = true

    Promise.all([
      getOverview(),
      getCases({ page_size: 100 }).catch(() => []),
      getCustomers({ page_size: 100 }).catch(() => []),
    ])
      .then(([overview, rawCases, rawCustomers]) => {
        if (!active) return
        const cases = Array.isArray(rawCases) ? rawCases : (rawCases?.items || rawCases?.cases || [])
        const customers = Array.isArray(rawCustomers) ? rawCustomers : (rawCustomers?.items || rawCustomers?.customers || [])
        const byCategory = { fraud: [], credit: [], compliance: [], other: [] }
        cases.forEach((item) => byCategory[categoryOf(item.case_type || item.type)].push(item))

        const worstByCustomer = new Map()
        const casesByCustomer = new Map()
        cases.forEach((item) => {
          if (item.customer_id == null) return
          const id = String(item.customer_id)
          casesByCustomer.set(id, (casesByCustomer.get(id) || 0) + 1)
          const tone = severityTone(item.severity)
          const current = worstByCustomer.get(id)
          if (!current || TONE_RANK[tone] > TONE_RANK[current]) worstByCustomer.set(id, tone)
        })

        const customerRows = customers.map((customer) => {
          const id = String(customer.id ?? customer.customer_id ?? '')
          return {
            id: id || customer.name,
            name: customer.name || customer.customer_name || `Customer ${id}`,
            segment: customer.segment || 'Portfolio account',
            level: worstByCustomer.get(id) || 'low',
            caseCount: casesByCustomer.get(id) || 0,
          }
        })
        const categories = Object.fromEntries(
          Object.entries(byCategory).map(([key, items]) => [key, { ...buildIndicator(items) }]),
        )
        setState({
          data: {
            overview,
            cases,
            customers,
            byCategory,
            customerRows,
            indicator: buildIndicator(cases),
            indicators: {
              overall: buildIndicator(cases),
              fraud: categories.fraud,
              credit: categories.credit,
              compliance: categories.compliance,
            },
          },
          loading: false,
          error: null,
        })
      })
      .catch((error) => {
        if (!active) return
        setState({ data: null, loading: false, error })
      })

    return () => { active = false }
  }, [])

  return state
}
