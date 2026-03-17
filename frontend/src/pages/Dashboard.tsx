import { useState, useEffect } from 'react'

const API = 'http://localhost:8000'

// API 认证：从 localStorage 读取密钥，POST/DELETE 请求自动携带
function authHeaders(): Record<string, string> {
  const key = localStorage.getItem('quantsight_api_key') || ''
  return key ? { 'X-API-Key': key } : {}
}

export default function Dashboard() {
  const [accountData, setAccountData] = useState<any>(null)
  const [strategies, setStrategies] = useState<any[]>([])
  const [portfolio, setPortfolio] = useState<any>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  const [positions, setPositions] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [posLoading, setPosLoading] = useState(false)
  const [evaluations, setEvaluations] = useState<any[]>([])
  const [healthStatus, setHealthStatus] = useState<any>(null)

  const refresh = () => {
    fetch(`${API}/api/account`)
      .then(r => r.json())
      .then(d => { if (d.success) setAccountData(d.data) })
      .catch(() => {})

    fetch(`${API}/api/strategy/instances`)
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          setStrategies(d.data)
          setIsRunning(d.data.some((s: any) => s.status === 'running'))
        }
      })
      .catch(() => {})

    fetch(`${API}/api/portfolio/summary`)
      .then(r => r.json())
      .then(d => { if (d.success) setPortfolio(d.data) })
      .catch(() => {})

    fetch(`${API}/api/strategy/evaluate`)
      .then(r => r.json())
      .then(d => { if (d.success) setEvaluations(d.data) })
      .catch(() => {})

    fetch(`${API}/api/health`)
      .then(r => r.json())
      .then(d => setHealthStatus(d))
      .catch(() => {})

    setPosLoading(true)
    Promise.all([
      fetch(`${API}/api/positions`).then(r => r.json()),
      fetch(`${API}/api/orders`).then(r => r.json()),
    ])
      .then(([posRes, ordRes]) => {
        if (posRes.success) setPositions(posRes.data)
        if (ordRes.success) setOrders(ordRes.data)
      })
      .catch(() => {})
      .finally(() => setPosLoading(false))
  }

  useEffect(() => { refresh() }, [])
  useEffect(() => {
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [])

  const handleStart = () => {
    setActionLoading(true)
    setStatusMsg('')
    fetch(`${API}/api/auto-trade/start`, { method: 'POST', headers: authHeaders() })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          setStatusMsg(d.message)
          setIsRunning(true)
          refresh()
        } else {
          setStatusMsg(`启动失败: ${d.error}`)
        }
      })
      .catch(e => setStatusMsg(`错误: ${e.message}`))
      .finally(() => setActionLoading(false))
  }

  const handleStop = () => {
    setActionLoading(true)
    fetch(`${API}/api/auto-trade/stop`, { method: 'POST', headers: authHeaders() })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          setStatusMsg(d.message)
          setIsRunning(false)
          refresh()
        }
      })
      .finally(() => setActionLoading(false))
  }

  const handleOptimize = () => {
    fetch(`${API}/api/strategy/auto-optimize`, { method: 'POST', headers: authHeaders() })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          const a = d.data
          setStatusMsg(a.action === 'replaced'
            ? `策略优化: 淘汰 ${a.removed.strategy_name}, 替换为 ${a.replaced_with}`
            : (a.reason || '所有策略表现正常'))
          refresh()
        }
      })
  }

  const equity = accountData?.[0]?.equity || 0
  const cash = accountData?.[0]?.cash || 0
  const buyingPower = accountData?.[0]?.buying_power || 0
  const totalRealizedPnl = strategies.reduce((sum, s) => sum + (s.realized_pnl || 0), 0)
  const totalUnrealizedPnl = strategies.reduce((sum, s) => sum + (s.unrealized_pnl || 0), 0)
  const totalPnl = totalRealizedPnl + totalUnrealizedPnl
  const totalTrades = strategies.reduce((sum, s) => sum + (s.total_trades || 0), 0)
  const runningCount = strategies.filter(s => s.status === 'running').length
  const errorCount = strategies.filter(s => s.status === 'error').length
  const totalMV = positions.reduce((sum, p) => sum + (p.market_value || 0), 0)
  const totalPosPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0)

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">QuantSight 全自动交易</h1>
        <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            className="status-dot"
            style={{
              backgroundColor: healthStatus?.tiger_api
                ? 'var(--accent-green)'
                : healthStatus ? 'var(--accent-red)' : 'var(--text-muted)'
            }}
            title={healthStatus?.tiger_api ? 'Tiger API 正常' : 'Tiger API 连接中...'}
          ></span>
          {isRunning ? `${runningCount} 个策略运行中` : '已停止'}
          {errorCount > 0 && <span style={{ color: 'var(--accent-red)', marginLeft: 8 }}>{errorCount} 个异常</span>}
          {healthStatus?.push_connected && (
            <span style={{ color: 'var(--accent-green)', fontSize: 11 }}>· 推送已连</span>
          )}
          <button className="btn btn-sm" style={{ backgroundColor: 'var(--border-color)', color: 'white', marginLeft: 12 }} onClick={refresh}>
            刷新
          </button>
        </div>
      </header>

      <div className="page-content">
        {/* 风控警告 */}
        {portfolio?.emergency_stopped && (
          <div className="widget" style={{ borderColor: 'var(--accent-red)', background: 'rgba(255,61,0,0.1)', padding: 20 }}>
            <div style={{ color: 'var(--accent-red)', fontWeight: 700, fontSize: 18, marginBottom: 8 }}>
              风控触发 — 所有策略已紧急停止
            </div>
            <div style={{ color: 'var(--text-muted)', marginBottom: 12 }}>
              总亏损超过阈值，系统自动保护资金。请检查账户后手动重置。
            </div>
            <button className="btn btn-primary" onClick={() => {
              fetch(`${API}/api/portfolio/reset-emergency`, { method: 'POST', headers: authHeaders() }).then(() => refresh())
            }}>
              重置风控并重新启动
            </button>
          </div>
        )}

        {/* ═══ 自动交易 ═══ */}
        <div className="widget" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20, fontWeight: 600, letterSpacing: 1 }}>
            自动交易
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 24 }}>
            {!isRunning ? (
              <button
                onClick={handleStart}
                disabled={actionLoading}
                style={{
                  width: 180, height: 180, borderRadius: '50%',
                  border: '3px solid var(--accent-green)',
                  background: 'rgba(0, 230, 118, 0.1)',
                  color: 'var(--accent-green)',
                  fontSize: 22, fontWeight: 700,
                  cursor: actionLoading ? 'wait' : 'pointer',
                  transition: 'all 0.3s',
                }}
              >
                {actionLoading ? '启动中...' : '开始赚钱'}
              </button>
            ) : (
              <>
                <button
                  onClick={handleStop}
                  disabled={actionLoading}
                  style={{
                    width: 180, height: 180, borderRadius: '50%',
                    border: '3px solid var(--accent-red)',
                    background: 'rgba(255, 61, 0, 0.1)',
                    color: 'var(--accent-red)',
                    fontSize: 22, fontWeight: 700,
                    cursor: actionLoading ? 'wait' : 'pointer',
                    transition: 'all 0.3s',
                  }}
                >
                  {actionLoading ? '停止中...' : '停止交易'}
                </button>
                <button
                  onClick={handleOptimize}
                  style={{
                    width: 80, height: 80, borderRadius: '50%',
                    border: '2px solid var(--accent-blue, #4fc3f7)',
                    background: 'rgba(79, 195, 247, 0.1)',
                    color: 'var(--accent-blue, #4fc3f7)',
                    fontSize: 12, fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  智能优化
                </button>
              </>
            )}
          </div>
          <div style={{ marginTop: 12, color: 'var(--text-muted)', fontSize: 13 }}>
            {isRunning
              ? '智能仓位 · 追踪止损 · 风控保护 · 盘中15秒/分钟级监控'
              : '港股蓝筹精选 · 顶级量化策略 · 全自动风控'
            }
          </div>
          {statusMsg && (
            <div style={{ marginTop: 10, fontSize: 13, color: statusMsg.includes('失败') || statusMsg.includes('错误') ? 'var(--accent-red)' : 'var(--accent-green)' }}>
              {statusMsg}
            </div>
          )}
        </div>

        {/* 账户概览 */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">账户总资产</div>
            <div className="metric-value">${equity.toLocaleString()}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">可用现金</div>
            <div className="metric-value">${cash.toLocaleString()}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">购买力</div>
            <div className="metric-value">${buyingPower.toLocaleString()}</div>
          </div>
          <div className="metric-card" style={{ borderColor: totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            <div className="metric-label">总盈亏</div>
            <div className={`metric-value ${totalPnl >= 0 ? 'text-green' : 'text-red'}`} style={{ fontSize: 28 }}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toLocaleString()}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">已实现盈亏</div>
            <div className={`metric-value ${totalRealizedPnl >= 0 ? 'text-green' : 'text-red'}`}>
              {totalRealizedPnl >= 0 ? '+' : ''}${totalRealizedPnl.toLocaleString()}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">总交易次数</div>
            <div className="metric-value">{totalTrades}</div>
          </div>
        </div>

        {/* 策略运行状态 */}
        {strategies.length > 0 && (
          <div className="widget">
            <div className="widget-title">策略运行状态（{runningCount}/{strategies.length} 运行中）</div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>策略</th><th>股票</th><th>状态</th><th>持仓</th>
                    <th>已实现盈亏</th><th>未实现盈亏</th><th>交易次数</th>
                    <th>Sharpe</th><th>连亏</th>
                    <th>最新信号</th><th>最近检查</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map(s => {
                    const ev = evaluations.find(e => e.id === s.id)
                    const sharpe = ev?.sharpe ?? null
                    const consecLoss = s.consecutive_losses ?? ev?.max_consec_losses ?? 0
                    return (
                      <tr key={s.id}>
                        <td>{s.strategy_name}</td>
                        <td style={{ fontWeight: 600 }}>{s.symbol}</td>
                        <td>
                          <span className={`status-badge ${s.status}`}>
                            {s.status === 'running' ? '运行中' : s.status === 'error' ? '异常' : '已停止'}
                          </span>
                        </td>
                        <td>{s.position_qty}股</td>
                        <td className={s.realized_pnl >= 0 ? 'text-green' : 'text-red'}>
                          ${s.realized_pnl?.toLocaleString()}
                        </td>
                        <td className={s.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}>
                          ${s.unrealized_pnl?.toLocaleString()}
                        </td>
                        <td>{s.total_trades}</td>
                        <td style={{
                          color: sharpe === null ? 'var(--text-muted)'
                            : sharpe >= 1 ? 'var(--accent-green)'
                            : sharpe >= 0 ? 'white'
                            : 'var(--accent-red)',
                          fontWeight: 600
                        }}>
                          {sharpe !== null ? sharpe.toFixed(2) : '—'}
                        </td>
                        <td style={{
                          color: consecLoss >= 3 ? 'var(--accent-red)' : consecLoss > 0 ? 'orange' : 'var(--text-muted)',
                          fontWeight: consecLoss >= 3 ? 700 : 400
                        }}>
                          {consecLoss > 0 ? `${consecLoss}连亏` : '—'}
                        </td>
                        <td style={{ fontSize: 12, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {s.last_signal || '等待信号...'}
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.last_check || '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {strategies.some(s => s.error_msg) && (
              <div style={{ marginTop: 12 }}>
                {strategies.filter(s => s.error_msg).map(s => (
                  <div key={s.id} style={{ color: 'var(--accent-red)', fontSize: 12, padding: '4px 0' }}>
                    [{s.strategy_name}] {s.error_msg}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 最近交易记录 */}
        {strategies.some(s => s.trade_history?.length > 0) && (
          <div className="widget">
            <div className="widget-title">最近交易记录</div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr><th>时间</th><th>股票</th><th>操作</th><th>价格</th><th>数量</th><th>盈亏</th><th>原因</th></tr>
                </thead>
                <tbody>
                  {strategies
                    .flatMap(s => (s.trade_history || []).map((t: any) => ({ ...t, symbol: s.symbol })))
                    .sort((a, b) => b.time?.localeCompare(a.time))
                    .slice(0, 30)
                    .map((t, i) => (
                      <tr key={i}>
                        <td>{t.time}</td>
                        <td style={{ fontWeight: 600 }}>{t.symbol}</td>
                        <td className={t.action === 'BUY' ? 'text-green' : 'text-red'}>
                          {t.action === 'BUY' ? '买入' : '卖出'}
                        </td>
                        <td>${t.price}</td>
                        <td>{t.quantity}</td>
                        <td className={(t.pnl || 0) >= 0 ? 'text-green' : 'text-red'}>
                          {t.pnl != null ? `$${t.pnl}` : '—'}
                        </td>
                        <td style={{ fontSize: 12, maxWidth: 300 }}>{t.reason}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ═══ 持仓盈亏 ═══ */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-label">持仓数量</div>
            <div className="metric-value">{positions.length}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">总市值</div>
            <div className="metric-value">${totalMV.toLocaleString()}</div>
          </div>
          <div className="metric-card" style={{ borderColor: totalPosPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            <div className="metric-label">未实现盈亏</div>
            <div className={`metric-value ${totalPosPnl >= 0 ? 'text-green' : 'text-red'}`}>
              {totalPosPnl >= 0 ? '+' : ''}${totalPosPnl.toLocaleString()}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">今日订单</div>
            <div className="metric-value">{orders.length}</div>
          </div>
        </div>

        {/* 持仓明细 */}
        <div className="widget">
          <div className="widget-title">持仓明细</div>
          {posLoading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>加载中...</div>
          ) : positions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>暂无持仓</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>股票</th><th>数量</th><th>成本价</th><th>最新价</th>
                    <th>市值</th><th>未实现盈亏</th><th>已实现盈亏</th><th>收益率</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p, i) => {
                    const returnRate = p.average_cost > 0
                      ? ((p.latest_price - p.average_cost) / p.average_cost * 100)
                      : 0
                    return (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{p.symbol}</td>
                        <td>{p.quantity}</td>
                        <td>${p.average_cost?.toFixed(2)}</td>
                        <td>${p.latest_price?.toFixed(2)}</td>
                        <td>${p.market_value?.toLocaleString()}</td>
                        <td className={p.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}>
                          {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl?.toFixed(2)}
                        </td>
                        <td className={p.realized_pnl >= 0 ? 'text-green' : 'text-red'}>
                          ${p.realized_pnl?.toFixed(2)}
                        </td>
                        <td className={returnRate >= 0 ? 'text-green' : 'text-red'}>
                          {returnRate >= 0 ? '+' : ''}{returnRate.toFixed(2)}%
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 订单历史 */}
        <div className="widget">
          <div className="widget-title">订单历史</div>
          {posLoading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>加载中...</div>
          ) : orders.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>暂无订单记录</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>订单号</th><th>股票</th><th>方向</th><th>类型</th>
                    <th>委托量</th><th>成交量</th><th>委托价</th><th>成交价</th><th>状态</th><th>时间</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o, i) => (
                    <tr key={i}>
                      <td style={{ fontSize: 12 }}>{o.order_id}</td>
                      <td style={{ fontWeight: 600 }}>{o.symbol}</td>
                      <td className={o.action === 'BUY' ? 'text-green' : 'text-red'}>
                        {o.action === 'BUY' ? '买入' : '卖出'}
                      </td>
                      <td>{o.order_type === 'MKT' ? '市价' : '限价'}</td>
                      <td>{o.quantity}</td>
                      <td>{o.filled_quantity}</td>
                      <td>{o.limit_price ? `$${o.limit_price}` : '—'}</td>
                      <td>{o.avg_fill_price ? `$${o.avg_fill_price}` : '—'}</td>
                      <td>
                        <span className={`status-badge ${o.status?.toLowerCase?.() === 'filled' ? 'running' : 'stopped'}`}>
                          {o.status}
                        </span>
                      </td>
                      <td style={{ fontSize: 12 }}>{o.order_time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
