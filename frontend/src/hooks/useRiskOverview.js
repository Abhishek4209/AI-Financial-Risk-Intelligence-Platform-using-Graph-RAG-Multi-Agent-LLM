import { useEffect, useState } from 'react'
import { getOverview } from '../services/riskApi'

export function useRiskOverview() {
  const [state, setState] = useState({ data: null, loading: true, error: null })

  useEffect(() => {
    let active = true

    getOverview().then(
      (data) => active && setState({ data, loading: false, error: null }),
      (error) => active && setState({ data: null, loading: false, error }),
    )

    return () => {
      active = false
    }
  }, [])

  return state
}
