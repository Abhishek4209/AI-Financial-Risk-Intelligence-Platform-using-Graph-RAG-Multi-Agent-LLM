import { useState } from 'react'
import {
  ChevronDown, CircleHelp, FileSearch, Gauge, LayoutDashboard, Scale,
  Search, ShieldAlert, SlidersHorizontal, Users, X,
} from 'lucide-react'
import Overview from './pages/Overview'
import RuntimeDashboard from './pages/RuntimeDashboard'
import RiskCases from './pages/RiskCases'
import Customers from './pages/Customers'
import Documents from './pages/Documents'
import CreditRisk from './pages/CreditRisk'
import FraudDetection from './pages/FraudDetection'
import Compliance from './pages/Compliance'

const NAV_ITEMS = [
  { label: 'Overview', icon: LayoutDashboard, Page: Overview },
  { label: 'Runtime dashboard', icon: Gauge, Page: RuntimeDashboard },
  { label: 'Risk cases', icon: ShieldAlert, Page: RiskCases },
  { label: 'Credit risk', icon: Scale, Page: CreditRisk },
  { label: 'Fraud detection', icon: ShieldAlert, Page: FraudDetection },
  { label: 'Compliance', icon: Search, Page: Compliance },
  { label: 'Customers', icon: Users, Page: Customers },
  { label: 'Documents', icon: FileSearch, Page: Documents },
]

export default function App() {
  const [activeNav, setActiveNav] = useState('Overview')
  const [mobileNav, setMobileNav] = useState(false)
  const ActivePage = NAV_ITEMS.find((item) => item.label === activeNav)?.Page || Overview

  return (
    <div className="app-shell">
      {mobileNav && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <aside className={`sidebar ${mobileNav ? 'sidebar--open' : ''}`}>
        <div className="brand-row">
          <div className="brand-mark"><span /></div>
          <div><strong>ledgerline</strong><small>risk intelligence</small></div>
          <button className="icon-button sidebar-close" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="workspace-switcher">
          <span className="workspace-avatar">A</span>
          <span><b>Atlas Financial</b><small>Enterprise workspace</small></span>
          <ChevronDown size={15} />
        </div>
        <nav className="main-nav" aria-label="Main navigation">
          <p className="nav-label">Workspace</p>
          {NAV_ITEMS.map(({ label, icon: Icon }) => (
            <button key={label} className={`nav-item ${activeNav === label ? 'nav-item--active' : ''}`} onClick={() => {
              setActiveNav(label)
              setMobileNav(false)
            }}>
              <Icon size={18} strokeWidth={activeNav === label ? 2.4 : 1.8} />
              <span>{label}</span>
            </button>
          ))}
          <p className="nav-label nav-label--spaced">System</p>
          <button className="nav-item" onClick={() => window.alert('Settings are not connected in this demo.')}><SlidersHorizontal size={18} /><span>Settings</span></button>
          <button className="nav-item" onClick={() => window.alert('Help center is not connected in this demo.')}><CircleHelp size={18} /><span>Help center</span></button>
        </nav>
        <div className="sidebar-footer"><span className="workspace-avatar">AU</span><span><b>Analyst workspace</b><small>Local demo mode</small></span></div>
      </aside>
      <main className="main-content">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><span>☰</span></button>
          <span className="topbar-breadcrumb">Risk Intelligence <span>/</span> {activeNav}</span>
          <span className="topbar-status"><i /> Demo environment</span>
        </header>
        <ActivePage />
      </main>
    </div>
  )
}
