
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
import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useTheme } from './hooks/useTheme'
import { Modal } from './components'
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
  const [dialog, setDialog] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const { theme, toggleTheme } = useTheme()

  useEffect(() => {
    function handleShortcut(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setDialog('search')
      }
    }

    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

  const matchingPages = NAV_ITEMS.filter((item) =>
    item.label.toLowerCase().includes(searchQuery.trim().toLowerCase()),
  )

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

          <button
            type="button"
            className="workspace-switcher"
            onClick={() => setDialog('workspace')}
            aria-label="Select workspace"
          >
            <span className="workspace-avatar">A</span>
            <span>
              <b>Atlas Financial</b>
              <small>Enterprise workspace</small>
            </span>
            <ChevronDown size={15} />
          </button>

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

            <button
              type="button"
              className="nav-item"
              onClick={() => setDialog('settings')}
            >
              <SlidersHorizontal size={18} />
              <span>Settings</span>
            </button>

            <button
              type="button"
              className="nav-item"
              onClick={() => setDialog('help')}
            >
              <CircleHelp size={18} />
              <span>Help center</span>
            </button>
          </nav>

          <div className="sidebar-foot">
            <div className="status-dot">
              <span />
              All systems operational
            </div>

            <button
              type="button"
              className="user-row"
              onClick={() => setDialog('profile')}
              aria-label="Open Abhishek Upadhyay profile"
            >
              <div className="user-avatar">AU</div>
              <span>
                <b>Abhishek Upadhyay</b>
                <small>Risk lead</small>
              </span>
              <MoreHorizontal size={17} />
            </button>
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
              <button
                type="button"
                className="search-button"
                onClick={() => setDialog('search')}
                aria-label="Search pages"
              >
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
                onClick={() => setDialog('notifications')}
              >
                <Bell size={19} />
                <i />
              </button>

              <button
                type="button"
                className="topbar-avatar"
                aria-label="Open Abhishek Upadhyay profile"
                onClick={() => setDialog('profile')}
              >
                AU
              </button>
            </div>
          </header>

          <AnimatedRoutes />
        </main>

        {dialog === 'search' && (
          <Modal title="Search workspace" onClose={() => setDialog(null)}>
            <label className="risk-form__field">
              <span>Find a page</span>
              <input
                type="search"
                autoFocus
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search pages"
              />
            </label>
            <nav className="modal-link-list" aria-label="Search results">
              {matchingPages.map(({ label, path, icon: Icon }) => (
                <NavLink
                  key={path}
                  to={path}
                  onClick={() => {
                    setDialog(null)
                    setSearchQuery('')
                  }}
                >
                  <Icon size={16} />
                  {label}
                </NavLink>
              ))}
              {matchingPages.length === 0 && (
                <p className="empty-state">No matching pages.</p>
              )}
            </nav>
          </Modal>
        )}

        {dialog === 'settings' && (
          <Modal title="Settings" onClose={() => setDialog(null)}>
            <div className="settings-row">
              <div>
                <strong>Appearance</strong>
                <p>Current theme: {theme}</p>
              </div>
              <button
                type="button"
                className="select-button"
                onClick={toggleTheme}
              >
                {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                Switch to {theme === 'dark' ? 'light' : 'dark'} theme
              </button>
            </div>
          </Modal>
        )}

        {dialog === 'help' && (
          <Modal title="Help center" onClose={() => setDialog(null)}>
            <p className="modal-copy">
              Choose a workspace page to get started. Risk scores are decision
              support and should be reviewed by an analyst.
            </p>
            <nav className="modal-link-list" aria-label="Help page links">
              {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
                <NavLink key={path} to={path} onClick={() => setDialog(null)}>
                  <Icon size={16} />
                  {label}
                </NavLink>
              ))}
            </nav>
          </Modal>
        )}

        {dialog === 'workspace' && (
          <Modal title="Workspace" onClose={() => setDialog(null)}>
            <div className="workspace-option" aria-current="true">
              <span className="workspace-avatar">A</span>
              <span>
                <strong>Atlas Financial</strong>
                <small>Active workspace</small>
              </span>
            </div>
            <p className="modal-copy">
              This is the only workspace configured for this account.
            </p>
          </Modal>
        )}

        {dialog === 'notifications' && (
          <Modal title="Notifications" onClose={() => setDialog(null)}>
            <p className="empty-state">You’re all caught up. No new notifications.</p>
          </Modal>
        )}

        {dialog === 'profile' && (
          <Modal title="Your profile" onClose={() => setDialog(null)}>
            <dl className="detail-list">
              <div>
                <dt>Name</dt>
                <dd>Abhishek Upadhyay</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>Risk lead</dd>
              </div>
              <div>
                <dt>Workspace</dt>
                <dd>Atlas Financial</dd>
              </div>
            </dl>
          </Modal>
        )}
      </div>
    </ToastProvider>
  )
}

export default App
