
import { AnimatePresence, motion } from 'framer-motion'
import {
  Bell,
  ChevronDown,
  CircleHelp,
  FileSearch,
  Gauge,
  LayoutDashboard,
  Menu,
  Moon,
  MoreHorizontal,
  Scale,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  Sun,
  Users,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import { ToastProvider } from './hooks/useToast'
import Overview from './pages/Overview'
import RuntimeDashboard from './pages/RuntimeDashboard'
import RiskCases from './pages/RiskCases'
import Customers from './pages/Customers'
import Documents from './pages/Documents'
import CreditRisk from './pages/CreditRisk'
import FraudDetection from './pages/FraudDetection'
import Compliance from './pages/Compliance'

const NAV_ITEMS = [
  { label: 'Overview', path: '/', icon: LayoutDashboard, Page: Overview },
  { label: 'Runtime dashboard', path: '/runtime', icon: Gauge, Page: RuntimeDashboard },
  { label: 'Risk cases', path: '/cases', icon: ShieldAlert, Page: RiskCases },
  { label: 'Credit risk', path: '/credit-risk', icon: Scale, Page: CreditRisk },
  { label: 'Fraud detection', path: '/fraud-detection', icon: ShieldAlert, Page: FraudDetection },
  { label: 'Compliance', path: '/compliance', icon: Search, Page: Compliance },
  { label: 'Customers', path: '/customers', icon: Users, Page: Customers },
  { label: 'Documents', path: '/documents', icon: FileSearch, Page: Documents },
]

function activeLabelFor(pathname) {
  return NAV_ITEMS.find((item) => item.path === pathname)?.label || 'Overview'
}

function Breadcrumb() {
  const location = useLocation()

  return (
    <div className="breadcrumb">
      <span>Workspace</span>
      <b>/</b>
      <strong>{activeLabelFor(location.pathname)}</strong>
    </div>
  )
}

function AnimatedRoutes() {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
      >
        <Routes location={location}>
          {NAV_ITEMS.map(({ path, Page }) => (
            <Route key={path} path={path} element={<Page />} />
          ))}
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

function App() {
  const [mobileNav, setMobileNav] = useState(false)
  const { theme, toggleTheme } = useTheme()

  return (
    <ToastProvider>
      <div className="app-shell">
        <aside className={`sidebar ${mobileNav ? 'sidebar--open' : ''}`}>
          <div className="brand-row">
            <div className="brand-mark">
              <span />
            </div>

            <div>
              <strong>ledgerline</strong>
              <small>risk intelligence</small>
            </div>

            <button
              className="icon-button sidebar-close"
              onClick={() => setMobileNav(false)}
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
          </div>

          <div className="workspace-switcher">
            <span className="workspace-avatar">A</span>
            <span>
              <b>Atlas Financial</b>
              <small>Enterprise workspace</small>
            </span>
            <ChevronDown size={15} />
          </div>

          <nav className="main-nav" aria-label="Main navigation">
            <p className="nav-label">Workspace</p>

            {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
              <NavLink
                key={label}
                to={path}
                end={path === '/'}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'nav-item--active' : ''}`
                }
                onClick={() => setMobileNav(false)}
              >
                {({ isActive }) => (
                  <>
                    <Icon size={18} strokeWidth={isActive ? 2.4 : 1.8} />
                    <span>{label}</span>
                  </>
                )}
              </NavLink>
            ))}

            <p className="nav-label nav-label--spaced">System</p>

            <button className="nav-item">
              <SlidersHorizontal size={18} />
              <span>Settings</span>
            </button>

            <button className="nav-item">
              <CircleHelp size={18} />
              <span>Help center</span>
            </button>
          </nav>

          <div className="sidebar-foot">
            <div className="status-dot">
              <span />
              All systems operational
            </div>

            <div className="user-row">
              <div className="user-avatar">JM</div>
              <span>
                <b>Jordan Miller</b>
                <small>Risk lead</small>
              </span>
              <MoreHorizontal size={17} />
            </div>
          </div>
        </aside>

        <main className="main-content">
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              onClick={() => setMobileNav(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>

            <Breadcrumb />

            <div className="topbar-actions">
              <button className="search-button">
                <Search size={17} />
                <span>Search anything</span>
                <kbd>Cmd K</kbd>
              </button>

              <button
                className="icon-button theme-toggle"
                onClick={toggleTheme}
                aria-label="Toggle color theme"
              >
                {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
              </button>

              <button
                className="icon-button notification-button"
                aria-label="Notifications"
              >
                <Bell size={19} />
                <i />
              </button>

              <div className="topbar-avatar">JM</div>
            </div>
          </header>

          <AnimatedRoutes />
        </main>
      </div>
    </ToastProvider>
  )
}

export default App
