import { useState, useEffect } from 'react'

const API = 'http://localhost:8000'

interface AvailableStrategy {
  key: string
  name: string
  description: string
}

interface StrategyInstance {
  id: string
  strategy_key: string
  strategy_name: string
  symbol: string
  params: Record<string, any>
  status: string
  position_qty: number
  realized_pnl: number
  unrealized_pnl: number
  total_trades: number
  last_signal: string | null
  last_check: string | null
  created_at: string
  trade_history: any[]
  error_msg: string | null
}

export default function Strategies() {
  const [available, setAvailable] = useState<AvailableStrategy[]>([])
  const [instances, setInstances] = useState<StrategyInstance[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState('')
  const [symbol, setSymbol] = useState('00700')
  const [customParams, setCustomParams] = useState('')
  const [creating, setCreating] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const refresh = () => {
    fetch(`${API}/api/strategies`).then(r => r.json()).then(d => { if (d.success) setAvailable(d.data) })
    fetch(`${API}/api/strategy/instances`).then(r => r.json()).then(d => { if (d.success) setInstances(d.data) })
  }

  useEffect(() => { refresh() }, [])

  // 自动刷新运行中实例状态
  useEffect(() => {
    const hasRunning = instances.some(i => i.status === 'running')
    if (!hasRunning) return
    const timer = setInterval(() => {
      fetch(`${API}/api/strategy/instances`).then(r => r.json()).then(d => { if (d.success) setInstances(d.data) })
    }, 5000)
    return () => clearInterval(timer)
  }, [instances])

  const handleCreate = () => {
    if (!selectedStrategy) return
    setCreating(true)
    let params = null
    if (customParams.trim()) {
      try { params = JSON.parse(customParams) } catch { alert('参数格式错误，请使用 JSON'); setCreating(false); return }
    }
    fetch(`${API}/api/strategy/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy_key: selectedStrategy, symbol, params })
    })
      .then(r => r.json())
      .then(d => {
        if (d.success) { refresh(); setCustomParams('') }
        else alert(d.error)
      })
      .finally(() => setCreating(false))
  }

  const handleAction = (id: string, action: 'start' | 'stop' | 'delete') => {
    if (action === 'delete') {
      fetch(`${API}/api/strategy/${id}`, { method: 'DELETE' }).then(() => refresh())
    } else {
      fetch(`${API}/api/strategy/${id}/${action}`, { method: 'POST' }).then(() => refresh())
    }
  }

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">策略管理</h1>
        <div style={{ color: 'var(--text-muted)' }}>创建、配置和管理自动交易策略</div>
      </header>

      <div className="page-content">
        {/* 创建策略 */}
        <div className="widget">
          <div className="widget-title">创建新策略</div>
          <div className="form-row">
            <div className="form-group">
              <label className="input-label">选择策略</label>
              <select className="trade-input" value={selectedStrategy} onChange={e => setSelectedStrategy(e.target.value)}>
                <option value="">-- 选择策略 --</option>
                {available.map(s => (
                  <option key={s.key} value={s.key}>{s.name} — {s.description}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="input-label">股票代码</label>
              <input className="trade-input" value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="00700" />
            </div>

            <div className="form-group">
              <label className="input-label">自定义参数 (JSON, 可选)</label>
              <input className="trade-input" value={customParams} onChange={e => setCustomParams(e.target.value)}
                placeholder='{"short_period": 5, "long_period": 20, "quantity": 200}' />
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleCreate} disabled={creating || !selectedStrategy} style={{ marginTop: 12 }}>
            {creating ? '创建中...' : '创建策略实例'}
          </button>
        </div>

        {/* 策略实例列表 */}
        <div className="widget">
          <div className="widget-title">策略实例 ({instances.length})</div>
          {instances.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', padding: 20, textAlign: 'center' }}>
              还没有策略实例，请在上方创建
            </div>
          ) : (
            <div className="strategy-list">
              {instances.map(inst => (
                <div key={inst.id} className="strategy-card">
                  <div className="strategy-card-header">
                    <div>
                      <div className="strategy-card-name">{inst.strategy_name}</div>
                      <div className="strategy-card-meta">
                        {inst.symbol} · ID: {inst.id} · 创建于 {inst.created_at}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <span className={`status-badge ${inst.status}`}>
                        {inst.status === 'running' ? '运行中' : inst.status === 'error' ? '异常' : '已停止'}
                      </span>
                    </div>
                  </div>

                  <div className="strategy-card-stats">
                    <div className="stat">
                      <div className="stat-label">持仓</div>
                      <div className="stat-value">{inst.position_qty}股</div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">已实现盈亏</div>
                      <div className={`stat-value ${inst.realized_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        ${inst.realized_pnl.toLocaleString()}
                      </div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">未实现盈亏</div>
                      <div className={`stat-value ${inst.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}`}>
                        ${inst.unrealized_pnl.toLocaleString()}
                      </div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">交易次数</div>
                      <div className="stat-value">{inst.total_trades}</div>
                    </div>
                    <div className="stat">
                      <div className="stat-label">最新信号</div>
                      <div className="stat-value" style={{ fontSize: 12, maxWidth: 200 }}>{inst.last_signal || '—'}</div>
                    </div>
                  </div>

                  {inst.error_msg && (
                    <div style={{ color: 'var(--accent-red)', fontSize: 13, padding: '8px 0' }}>
                      错误: {inst.error_msg}
                    </div>
                  )}

                  <div className="strategy-card-actions">
                    {inst.status !== 'running' && (
                      <button className="btn btn-sm btn-buy" onClick={() => handleAction(inst.id, 'start')}>启动</button>
                    )}
                    {inst.status === 'running' && (
                      <button className="btn btn-sm btn-sell" onClick={() => handleAction(inst.id, 'stop')}>停止</button>
                    )}
                    <button className="btn btn-sm" style={{ backgroundColor: 'var(--border-color)', color: 'white' }}
                      onClick={() => setExpandedId(expandedId === inst.id ? null : inst.id)}>
                      {expandedId === inst.id ? '收起' : '交易记录'}
                    </button>
                    {inst.status !== 'running' && (
                      <button className="btn btn-sm" style={{ backgroundColor: '#4a1c1c', color: '#ff6b6b' }}
                        onClick={() => { if (confirm('确定删除？')) handleAction(inst.id, 'delete') }}>
                        删除
                      </button>
                    )}
                  </div>

                  {/* 展开交易记录 */}
                  {expandedId === inst.id && inst.trade_history.length > 0 && (
                    <div className="table-container" style={{ marginTop: 12 }}>
                      <table className="data-table">
                        <thead>
                          <tr><th>时间</th><th>操作</th><th>价格</th><th>数量</th><th>盈亏</th><th>原因</th></tr>
                        </thead>
                        <tbody>
                          {inst.trade_history.map((t, i) => (
                            <tr key={i}>
                              <td>{t.time}</td>
                              <td className={t.action === 'BUY' ? 'text-green' : 'text-red'}>{t.action === 'BUY' ? '买入' : '卖出'}</td>
                              <td>${t.price}</td>
                              <td>{t.quantity}</td>
                              <td className={t.pnl >= 0 ? 'text-green' : 'text-red'}>{t.pnl != null ? `$${t.pnl}` : '—'}</td>
                              <td style={{ fontSize: 12 }}>{t.reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* 参数展示 */}
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                    参数: {JSON.stringify(inst.params)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
