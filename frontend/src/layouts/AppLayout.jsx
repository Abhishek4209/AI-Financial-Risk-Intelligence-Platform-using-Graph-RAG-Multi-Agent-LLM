import { Menu, X } from 'lucide-react'
import { useState } from 'react'

export default function AppLayout({ sidebar, children }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="app-shell">
      <button className="icon-button mobile-menu" onClick={() => setOpen(true)} aria-label="Open navigation">
        <Menu size={20} />
      </button>
      <aside className={`sidebar ${open ? 'sidebar--open' : ''}`}>
        <button className="icon-button sidebar-close" onClick={() => setOpen(false)} aria-label="Close navigation">
          <X size={18} />
        </button>
        {sidebar}
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
