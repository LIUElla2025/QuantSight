import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Strategies from './pages/Strategies'
import Backtest from './pages/Backtest'
import Positions from './pages/Positions'
import Settings from './pages/Settings'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="dashboard-container">
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="logo">
            <div className="logo-icon"></div>
            QuantSight
          </div>
          <nav className="nav-menu">
            <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              交易看板
            </NavLink>
            <NavLink to="/strategies" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              策略管理
            </NavLink>
            <NavLink to="/backtest" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              策略回测
            </NavLink>
            <NavLink to="/positions" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              持仓订单
            </NavLink>
            <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              系统设置
            </NavLink>
          </nav>
          <div className="sidebar-footer">
            <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              QuantSight v1.0<br />
              量化自动交易平台<br />
              老虎证券 OpenAPI
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/backtest" element={<Backtest />} />
            <Route path="/positions" element={<Positions />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
