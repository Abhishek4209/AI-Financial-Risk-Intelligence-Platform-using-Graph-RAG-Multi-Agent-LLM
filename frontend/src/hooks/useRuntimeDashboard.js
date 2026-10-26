
import { useEffect, useState } from 'react'
import { getCases, getCustomers, getOverview } from '../services/riskApi'

const TONE_RANK = { low: 0, medium: 1, high: 2 }
const LOW_MAX = 100 / 3
const HIGH_MIN = 200 / 3

function severityTone(severity) {
  if (severity === 'high') return 'high'
  if (severity === 'medium') return 'medium'
  return 'low'
}

function categoryOf(caseType = '') {
  const value = caseType.toLowerCase()

  if (value.includes('fraud')) return 'fraud'
  if (value.includes('credit')) return 'credit'
  if (value.includes('complian')) return 'compliance'

  return 'other'
}

function buildIndicator(cases) {
  const counts = { low: 0, medium: 0, high: 0 }

  cases.forEach((item) => {
    counts[severityTone(item.severity)] += 1
  })

  const total = cases.length
  const score = total
    ? Math.round(((counts.high + counts.medium * 0.5) / total) * 100)
    : 0

  let level = 'low'

  if (score >= HIGH_MIN) {
    level = 'high'
  } else if (score >= LOW_MAX) {
    level = 'medium'
  }

  return { counts, total, score, level }
}

export function useRuntimeDashboard() {
  const [state, setState] = useState({
    data: null,
    loading: true,
    error: null,
  })

  useEffect(() => {
    let active = true

    Promise.all([
      getOverview(),
      getCases({ page_size: 100 }).catch(() => []),
      getCustomers({ page_size: 100 }).catch(() => []),
    ]).then(
      ([overview, cases, customers]) => {
        if (!active) return

        const byCategory = {
          fraud: [],
          credit: [],
          compliance: [],
          other: [],
        }

        cases.forEach((item) => {
          byCategory[categoryOf(item.case_type)].push(item)
        })

        const worstByCustomer = new Map()
        const casesByCustomer = new Map()

        cases.forEach((item) => {
          if (!item.customer_id) return

          casesByCustomer.set(
            item.customer_id,
            (casesByCustomer.get(item.customer_id) || 0) + 1
          )

          const tone = severityTone(item.severity)
          const current = worstByCustomer.get(item.customer_id)

          if (!current || TONE_RANK[tone] > TONE_RANK[current]) {
            worstByCustomer.set(item.customer_id, tone)
          }
        })

        const customerRows = customers.map((customer) => ({
          id: customer.id,
          name: customer.name,
          segment: customer.segment || 'Portfolio account',
          level: worstByCustomer.get(customer.id) || 'low',
          caseCount: casesByCustomer.get(customer.id) || 0,
        }))

        setState({
          data: {
            overview,
            indicators: {
              overall: buildIndicator(cases),
              fraud: buildIndicator(byCategory.fraud),
              credit: buildIndicator(byCategory.credit),
              compliance: buildIndicator(byCategory.compliance),
            },
            customerRows,
          },
          loading: false,
          error: null,
        })
      },
      (error) => {
        if (active) {
          setState({
            data: null,
            loading: false,
            error,
          })
        }
      }
    )

    return () => {
      active = false
    }
  }, [])

  return state
}
