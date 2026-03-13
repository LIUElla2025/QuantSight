import { useState, useEffect, useRef } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'

const API = 'http://localhost:8000'

export default function Dashboard() {
  const [accountData, setAccountData] = useState<any>(null)
  const [symbol, setSymbol] = useState("00700")
  const [quote, setQuote] = useState<any>(null)
  const [strategies, setStrategies] = useState<any[]>([])
  const [orderQty, setOrderQty] = useState("")
  const [orderLoading, setOrderLoading] = useState(false)
  const [orderMsg, setOrderMsg] = useState("")

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)

  // 获取账户信息
  useEffect(() => {
    fetch(`${API}/api/account`)
      .then(r => r.json())
      .then(d => { if (d.success) setAccountData(d.data) })
      .catch(() => {})

    // 获取运行中策略
    fetch(`${API}/api/strategy/instances`)
      .then(r => r.json())
      .then(d => { if (d.success) setStrategies(d.data) })
      .catch(() => {})
  }, [])

  // 初始化图表
  useEffect(() => {
    if (!chartContainerRef.current) return
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8b8b93',
      },
      grid: {
        vertLines: { color: '#27272a' },
        horzLines: { color: '#27272a' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 380,
    })

    const cs = chart.addSeries(CandlestickSeries, {
      upColor: '#00e676', downColor: '#ff3d00',
      borderVisible: false,
      wickUpColor: '#00e676', wickDownColor: '#ff3d00',
    })

    chartRef.current = chart
    candlestickSeriesRef.current = cs

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)
    return () => { window.removeEventListener('resize', handleResize); chart.remove() }
  }, [])

  // 拉取行情 + K线
  const handleFetchQuote = () => {
    fetch(`${API}/api/quote/${symbol}`)
      .then(r => r.json())
      .then(d => { if (d.success) setQuote(d.data) })

    fetch(`${API}/api/klines/${symbol}`)
      .then(r => r.json())
      .then(d => {
        if (d.success && candlestickSeriesRef.current && d.data.length > 0) {
          const sorted = d.data.sort((a: any, b: any) =>
            new Date(a.time).getTime() - new Date(b.time).getTime()
          )
          candlestickSeriesRef.current.setData(sorted)
          chartRef.current.timeScale().fitContent()
        }
      })
  }

  // 下单
  const handleOrder = (action: string) => {
    const qty = parseInt(orderQty)
    if (!qty || qty <= 0) { setOrderMsg("请输入有效的股数"); return }
    setOrderLoading(true)
    setOrderMsg("")
    fetch(`${API}/api/order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, action, quantity: qty, order_type: "MKT" })
    })
      .then(r => r.json())
      .then(d => {
        if (d.success) setOrderMsg(`${action === 'BUY' ? '买入' : '卖出'}成功！`)
        else setOrderMsg(`下单失败: ${d.error}`)
      })
      .catch(e => setOrderMsg(`错误: ${e.message}`))
      .finally(() => setOrderLoading(false))
  }

  const equity = accountData?.[0]?.equity
  const unrealizedPnl = accountData?.[0]?.unrealized_pnl || 0

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">交易看板</h1>
        <div style={{ color: "var(--text-muted)", display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="status-dot"></span> 老虎证券已连接
        </div>
      </header>

      <div className="dashboard-grid">
        {/* 账户总览 */}
        <div className="widget account-overview">
          <div>
            <div className="widget-title">总资产权益</div>
            <div className="account-value">
              {equity ? `$${equity.toLocaleString()}` : '连接中...'}
            </div>
            {accountData?.[0] && (
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                可用资金: ${accountData[0].available_funds?.toLocaleString() || '—'}
                &nbsp;·&nbsp;
                购买力: ${accountData[0].buying_power?.toLocaleString() || '—'}
              </div>
            )}
          </div>
          <div className={`account-change ${unrealizedPnl >= 0 ? 'positive' : 'negative'}`}>
            {unrealizedPnl >= 0 ? '+' : ''}{unrealizedPnl.toLocaleString()} 未实现盈亏
          </div>
        </div>

        {/* K线图表 */}
        <div className="widget chart-widget">
          <div className="widget-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>实时 K 线 {quote ? `(${symbol})` : ''}</span>
            {quote && (
              <span style={{ color: (quote.change_rate || 0) >= 0 ? "var(--accent-green)" : "var(--accent-red)" }}>
                最新价: {quote.latest_price} ({quote.change_rate ? (quote.change_rate * 100).toFixed(2) : '0.00'}%)
              </span>
            )}
          </div>
          <div ref={chartContainerRef} style={{ width: '100%', height: '380px', flex: 1 }} />
        </div>

        {/* 交易面板 */}
        <div className="widget trading-widget">
          <div className="widget-title">快速交易</div>

          <label className="input-label">股票代码</label>
          <input
            type="text" className="trade-input" value={symbol}
            onChange={e => setSymbol(e.target.value)}
            placeholder="港股如 00700, 美股如 AAPL"
          />

          <button className="btn btn-fetch" onClick={handleFetchQuote}>
            拉取行情
          </button>

          <label className="input-label">下单数量</label>
          <input
            type="number" className="trade-input" value={orderQty}
            onChange={e => setOrderQty(e.target.value)}
            placeholder="股数"
          />

          <div className="trade-buttons">
            <button className="btn btn-buy" onClick={() => handleOrder('BUY')} disabled={orderLoading}>
              买入
            </button>
            <button className="btn btn-sell" onClick={() => handleOrder('SELL')} disabled={orderLoading}>
              卖出
            </button>
          </div>

          {orderMsg && (
            <div style={{ marginTop: 12, fontSize: 13, color: orderMsg.includes('成功') ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {orderMsg}
            </div>
          )}
        </div>

        {/* 运行中的策略 */}
        {strategies.length > 0 && (
          <div className="widget" style={{ gridColumn: '1 / -1' }}>
            <div className="widget-title">运行中的策略</div>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>策略</th>
                    <th>股票</th>
                    <th>状态</th>
                    <th>持仓</th>
                    <th>已实现盈亏</th>
                    <th>未实现盈亏</th>
                    <th>最新信号</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map(s => (
                    <tr key={s.id}>
                      <td>{s.strategy_name}</td>
                      <td>{s.symbol}</td>
                      <td>
                        <span className={`status-badge ${s.status}`}>{s.status === 'running' ? '运行中' : s.status === 'error' ? '异常' : '已停止'}</span>
                      </td>
                      <td>{s.position_qty}股</td>
                      <td className={s.realized_pnl >= 0 ? 'text-green' : 'text-red'}>{s.realized_pnl.toLocaleString()}</td>
                      <td className={s.unrealized_pnl >= 0 ? 'text-green' : 'text-red'}>{s.unrealized_pnl.toLocaleString()}</td>
                      <td style={{ fontSize: 12, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.last_signal || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
