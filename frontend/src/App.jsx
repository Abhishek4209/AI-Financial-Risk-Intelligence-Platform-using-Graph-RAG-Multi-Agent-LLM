import { useState } from 'react'
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  ChevronDown,
  CircleHelp,
  FileSearch,
  LayoutDashboard,
  Menu,
  MoreHorizontal,
  PanelLeftClose,
  Search,
  ShieldAlert,
  SlidersHorizontal,
  Sparkles,
  Users,
  X,
} from 'lucide-react'

const navItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Risk cases', icon: ShieldAlert, count: '12' },
  { label: 'Customers', icon: Users },
  { label: 'Documents', icon: FileSearch },
]

const cases = [
  { name: 'Northstar Logistics', type: 'Credit review', owner: 'A. Sharma', score: 82, status: 'Needs review', tone: 'high' },
  { name: 'Meridian Wholesale', type: 'Fraud investigation', owner: 'J. Wilson', score: 74, status: 'In progress', tone: 'medium' },
  { name: 'Atlas Energy Partners', type: 'Compliance check', owner: 'M. Chen', score: 61, status: 'Monitoring', tone: 'low' },
  { name: 'Verity Health Systems', type: 'Credit review', owner: 'R. Patel', score: 57, status: 'Monitoring', tone: 'low' },
]

function ScoreRing() {
  return (
    <div className="score-ring" aria-label="Portfolio risk score 68 out of 100">
      <div className="score-ring__inner">
        <strong>68</strong>
        <span>/ 100</span>
      </div>
    </div>
  )
}

function TrendChart() {
  return (
    <div className="trend-chart" aria-label="Risk exposure trend from January to June">
      <div className="chart-y-axis"><span>80</span><span>60</span><span>40</span><span>20</span><span>0</span></div>
      <div className="chart-plot">
        <div className="chart-grid"><i /><i /><i /><i /><i /></div>
        <svg viewBox="0 0 660 220" preserveAspectRatio="none" role="img" aria-label="Risk exposure has decreased over six months">
          <defs>
            <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#e6a23c" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#e6a23c" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,62 C44,72 66,90 110,86 S172,72 220,106 S282,125 330,120 S392,95 440,131 S500,162 550,154 S612,145 660,172 L660,220 L0,220 Z" fill="url(#areaFill)" />
          <path d="M0,62 C44,72 66,90 110,86 S172,72 220,106 S282,125 330,120 S392,95 440,131 S500,162 550,154 S612,145 660,172" fill="none" stroke="#d88725" strokeWidth="3" vectorEffect="non-scaling-stroke" />
          <circle cx="660" cy="172" r="5" fill="#fffdf7" stroke="#d88725" strokeWidth="3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="chart-x-axis"><span>Jan</span><span>Feb</span><span>Mar</span><span>Apr</span><span>May</span><span>Jun</span></div>
      </div>
    </div>
  )
}

function App() {
  const [activeNav, setActiveNav] = useState('Overview')
  const [mobileNav, setMobileNav] = useState(false)

  return (
    <div className="app-shell">
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
          {navItems.map(({ label, icon: Icon, count }) => (
            <button key={label} className={`nav-item ${activeNav === label ? 'nav-item--active' : ''}`} onClick={() => { setActiveNav(label); setMobileNav(false) }}>
              <Icon size={18} strokeWidth={activeNav === label ? 2.4 : 1.8} />
              <span>{label}</span>
              {count && <em>{count}</em>}
            </button>
          ))}
          <p className="nav-label nav-label--spaced">System</p>
          <button className="nav-item"><SlidersHorizontal size={18} /><span>Settings</span></button>
          <button className="nav-item"><CircleHelp size={18} /><span>Help center</span></button>
        </nav>
        <div className="sidebar-foot">
          <div className="status-dot"><span />All systems operational</div>
          <div className="user-row"><div className="user-avatar">JM</div><span><b>Jordan Miller</b><small>Risk lead</small></span><MoreHorizontal size={17} /></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="breadcrumb"><span>Workspace</span><b>/</b><strong>{activeNav}</strong></div>
          <div className="topbar-actions">
            <button className="search-button"><Search size={17} /><span>Search anything</span><kbd>⌘ K</kbd></button>
            <button className="icon-button notification-button" aria-label="Notifications"><Bell size={19} /><i /></button>
            <div className="topbar-avatar">JM</div>
          </div>
        </header>

        <div className="page-content">
          <section className="page-heading">
            <div><p className="eyebrow">Monday, 24 June 2024 <span className="live-pill"><i />Live</span></p><h1>Good morning, Jordan.</h1><p className="heading-copy">Here is your portfolio at a glance. Two cases need your attention.</p></div>
            <button className="primary-button"><Sparkles size={16} />Run new analysis</button>
          </section>

          <section className="metric-grid" aria-label="Portfolio metrics">
            <article className="metric-card metric-card--score"><div className="metric-card__top"><span className="metric-label">Portfolio risk score</span><button className="card-menu" aria-label="Portfolio score options"><MoreHorizontal size={18} /></button></div><div className="score-content"><ScoreRing /><div><strong className="metric-value">Moderate</strong><p className="metric-change metric-change--positive"><ArrowDownRight size={15} /> 8.4% <span>vs last month</span></p></div></div></article>
            <article className="metric-card"><div className="metric-card__top"><span className="metric-label">Exposure under review</span><span className="metric-icon metric-icon--orange"><Activity size={17} /></span></div><strong className="metric-value">$24.8M</strong><p className="metric-change metric-change--negative"><ArrowUpRight size={15} /> 3.2% <span>vs last month</span></p><div className="mini-bar"><span style={{ width: '68%' }} /></div><small className="metric-footnote">68% of review threshold</small></article>
            <article className="metric-card"><div className="metric-card__top"><span className="metric-label">Open risk cases</span><span className="metric-icon metric-icon--red"><ShieldAlert size={17} /></span></div><strong className="metric-value">42</strong><p className="metric-change metric-change--positive"><ArrowDownRight size={15} /> 12.5% <span>vs last month</span></p><div className="case-breakdown"><span><i className="dot dot--red" />High <b>8</b></span><span><i className="dot dot--orange" />Medium <b>19</b></span><span><i className="dot dot--green" />Low <b>15</b></span></div></article>
          </section>

          <section className="insight-banner"><div className="insight-icon"><Sparkles size={18} /></div><div><strong>AI insight</strong><p>Credit exposure in the logistics sector has risen 14% this quarter. Three accounts may need a refreshed assessment.</p></div><button className="text-button">View insight <ArrowUpRight size={15} /></button></section>

          <section className="dashboard-grid">
            <article className="panel trend-panel"><div className="panel-heading"><div><h2>Risk exposure trend</h2><p>Aggregate exposure score over the past 6 months</p></div><button className="select-button">Last 6 months <ChevronDown size={15} /></button></div><div className="chart-legend"><span><i className="legend-line" />Exposure score</span><span className="legend-total">Current <b>42.6</b></span></div><TrendChart /></article>
            <article className="panel distribution-panel"><div className="panel-heading"><div><h2>Risk distribution</h2><p>By portfolio value</p></div><button className="card-menu" aria-label="Risk distribution options"><MoreHorizontal size={18} /></button></div><div className="distribution-body"><div className="donut-chart"><div><strong>$86.4M</strong><span>Total portfolio</span></div></div><div className="distribution-legend"><div><i className="dot dot--green" /><span>Low risk</span><b>$48.2M</b><small>56%</small></div><div><i className="dot dot--orange" /><span>Medium risk</span><b>$24.9M</b><small>29%</small></div><div><i className="dot dot--red" /><span>High risk</span><b>$13.3M</b><small>15%</small></div></div></div></article>
          </section>

          <section className="panel cases-panel"><div className="panel-heading"><div><h2>Priority cases</h2><p>Cases requiring review across your portfolio</p></div><div className="panel-actions"><button className="filter-button"><SlidersHorizontal size={15} /> Filter</button><button className="text-button">View all <ArrowUpRight size={15} /></button></div></div><div className="table-wrap"><table><thead><tr><th>Account</th><th>Case type</th><th>Owner</th><th>Risk score</th><th>Status</th><th aria-label="Actions" /></tr></thead><tbody>{cases.map((item) => <tr key={item.name}><td><div className="account-cell"><span className="company-avatar">{item.name.split(' ').map((word) => word[0]).slice(0, 2).join('')}</span><strong>{item.name}</strong></div></td><td>{item.type}</td><td>{item.owner}</td><td><span className={`table-score table-score--${item.tone}`}>{item.score}</span></td><td><span className={`status status--${item.tone}`}>{item.status}</span></td><td><button className="card-menu" aria-label={`Open ${item.name} actions`}><MoreHorizontal size={18} /></button></td></tr>)}</tbody></table></div></section>

          <section className="activity-section"><div className="section-heading"><div><h2>Recent activity</h2><p>Latest changes from your workspace</p></div><button className="text-button">See activity log <ArrowUpRight size={15} /></button></div><div className="activity-list"><div className="activity-item"><span className="activity-icon activity-icon--purple"><FileSearch size={16} /></span><p><strong>Risk report generated</strong><span>for Northstar Logistics by AI analyst</span></p><time>12 min ago</time></div><div className="activity-item"><span className="activity-icon activity-icon--green"><Users size={16} /></span><p><strong>New customer added</strong><span>Meridian Wholesale was added to your portfolio</span></p><time>1 hr ago</time></div><div className="activity-item"><span className="activity-icon activity-icon--orange"><ShieldAlert size={16} /></span><p><strong>Case status updated</strong><span>Atlas Energy Partners moved to monitoring</span></p><time>3 hrs ago</time></div></div></section>
        </div>
      </main>
    </div>
  )
}

export default App
