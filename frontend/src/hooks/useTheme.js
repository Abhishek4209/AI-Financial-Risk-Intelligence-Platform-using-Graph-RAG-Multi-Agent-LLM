
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'ledgerline-theme'

function getInitialTheme() {
  if (typeof window === 'undefined') return 'light'

  const stored = window.localStorage.getItem(STORAGE_KEY)

  if (stored === 'light' || stored === 'dark') {
    return stored
  }

  return window.matchMedia?.('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

export function useTheme() {
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  function toggleTheme() {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }

  return { theme, toggleTheme }
}
