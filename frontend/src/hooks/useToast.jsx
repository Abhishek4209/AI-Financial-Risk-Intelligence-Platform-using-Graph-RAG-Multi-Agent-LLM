
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react'

const ToastContext = createContext(null)

const ICON_BY_TONE = {
  success: CheckCircle2,
  error: TriangleAlert,
  info: Info,
}

function createToastId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const dismiss = useCallback((id) => {
    setToasts((current) =>
      current.filter((toast) => toast.id !== id)
    )
  }, [])

  const notify = useCallback(
    (message, { tone = 'info', duration = 4500 } = {}) => {
      const id = createToastId()

      setToasts((current) => [
        ...current,
        { id, message, tone },
      ])

      if (duration) {
        setTimeout(() => dismiss(id), duration)
      }

      return id
    },
    [dismiss]
  )

  const value = useMemo(
    () => ({ notify, dismiss }),
    [notify, dismiss]
  )

  return (
    <ToastContext.Provider value={value}>
      {children}

      <div className="toast-stack" aria-live="polite">
        {toasts.map((toast) => {
          const Icon = ICON_BY_TONE[toast.tone] || Info

          return (
            <div
              className={`toast toast--${toast.tone}`}
              key={toast.id}
            >
              <output>
                <Icon size={16} />
                <span>{toast.message}</span>
              </output>

              <button
                type="button"
                aria-label="Dismiss notification"
                onClick={() => dismiss(toast.id)}
              >
                <X size={14} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)

  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }

  return context
}
