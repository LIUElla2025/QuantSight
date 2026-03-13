import { useState, useEffect } from 'react'

const API = 'http://localhost:8000'

export default function Positions() {
  const [positions, setPositions] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [tab, setTab] = useState<'positions' | 'orders'>('positions')
  const [loading, setLoading] = useState(true)

  const refresh = () => {
    setLoading(true)
    Promise.all([
      fetch(`${API}/api/positions`).then(r => r.json()),
      fetch(`${API}/api/orders`).then(r => r.json()),
    ])
      .then(([posRes, ordRes]) => {
        if (posRes.success) setPositions(posRes.data)
        if (ordRes.success) setOrders(ordRes.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])

  const totalMV = positions.reduce((sum, p) => sum + (p.market_value || 0), 0)
  const totalPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0)

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">持仓与订单</h1>
        <button className="btn btn-sm" style={{ backgroundColor: 'var(--border-color)', color: 'white' }} onClick={refresh}>
          刷新
        </button>
      </header>

      <div className="page-content">
        {/* 汇总 */}
        <div className="metrics-grid" style={{ marginBottom: 24 }}>
          <div className="metric-card">
            <div className="metric-label">持仓数量</div>
            <div className="metric-value">{positions.length}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">总市值</div>
            <div className="metric-value">${totalMV.toLocaleString()}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">未实现盈亏</div>
            <div className={`metric-value ${totalPnl >= 0 ? 'text-green' : 'text-red'}`}>
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toLocaleString()}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">今日订单</div>
            <div className="metric-value">{orders.length}</div>
          </div>
        </div>

        {/* Tab 切换 */}
        <div className="tab-bar">
          <button className={`tab ${tab === 'positions' ? 'active' : ''}`} onClick={() => setTab('positions')}>
            持仓明细
          </button>
          <button className={`tab ${tab === 'orders' ? 'active' : ''}`} onClick={() => setTab('orders')}>
            订单历史
          </button>
        </div>

        <div className="widget" style={{ marginTop: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>加载中...</div>
          ) : tab === 'positions' ? (
            positions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>暂无持仓</div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>股票</th>
                      <th>数量</th>
                      <th>成本价</th>
                      <th>最新价</th>
                      <th>市值</th>
                      <th>未实现盈亏</th>
                      <th>已实现盈亏</th>
                      <th>收益率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p, i) => {
                      const returnRate = p.average_cost > 0 ? ((p.latest_price - p.average_cost) / p.average_cost * 100) : 0
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
            )
          ) : (
            orders.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>暂无订单记录</div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>订单号</th>
                      <th>股票</th>
                      <th>方向</th>
                      <th>类型</th>
                      <th>委托量</th>
                      <th>成交量</th>
                      <th>委托价</th>
                      <th>成交价</th>
                      <th>状态</th>
                      <th>时间</th>
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
            )
          )}
        </div>
      </div>
    </>
  )
}
