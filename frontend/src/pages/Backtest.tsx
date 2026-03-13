import { useState, useEffect, useRef } from 'react'
import { createChart, ColorType, AreaSeries } from 'lightweight-charts'

const API = 'http://localhost:8000'

interface BacktestResult {
  strategy_name: string
  symbol: string
  start_date: string
  end_date: string
  initial_capital: number
  final_capital: number
  total_return: number
  annual_return: number
  max_drawdown: number
  sharpe_ratio: number
  win_rate: number
  total_trades: number
  profit_trades: number
  loss_trades: number
  avg_profit: number
  avg_loss: number
  profit_factor: number
  trade_log: any[]
  equity_curve: { time: string; equity: number }[]
}

export default function Backtest() {
  const [strategies, setStrategies] = useState<any[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState('')
  const [symbol, setSymbol] = useState('AAPL')
  const [days, setDays] = useState('200')
  const [capital, setCapital] = useState('1000000')
  const [customParams, setCustomParams] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState('')

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<any>(null)

  useEffect(() => {
    fetch(`${API}/api/strategies`).then(r => r.json()).then(d => { if (d.success) setStrategies(d.data) })
  }, [])

  // 渲染权益曲线
  useEffect(() => {
    if (!result || !chartContainerRef.current) return

    // 清除旧图表
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove()
      chartInstanceRef.current = null
    }

    const chart = createChart(chartContainerRef.current, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b8b93' },
      grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
      width: chartContainerRef.current.clientWidth,
      height: 300,
    })

    const series = chart.addSeries(AreaSeries, {
      topColor: result.total_return >= 0 ? 'rgba(0, 230, 118, 0.3)' : 'rgba(255, 61, 0, 0.3)',
      bottomColor: result.total_return >= 0 ? 'rgba(0, 230, 118, 0.0)' : 'rgba(255, 61, 0, 0.0)',
      lineColor: result.total_return >= 0 ? '#00e676' : '#ff3d00',
      lineWidth: 2,
    })

    series.setData(result.equity_curve.map(e => ({ time: e.time, value: e.equity })))
    chart.timeScale().fitContent()
    chartInstanceRef.current = chart

    const handleResize = () => {
      if (chartContainerRef.current) chart.applyOptions({ width: chartContainerRef.current.clientWidth })
    }
    window.addEventListener('resize', handleResize)
    return () => { window.removeEventListener('resize', handleResize) }
  }, [result])

  const handleRun = () => {
    if (!selectedStrategy) return
    setLoading(true)
    setError('')
    setResult(null)

    let params = null
    if (customParams.trim()) {
      try { params = JSON.parse(customParams) } catch { setError('参数格式错误'); setLoading(false); return }
    }

    fetch(`${API}/api/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        strategy_key: selectedStrategy,
        symbol,
        params,
        initial_capital: parseFloat(capital),
        days: parseInt(days),
      })
    })
      .then(r => r.json())
      .then(d => {
        if (d.success) setResult(d.data)
        else setError(d.error)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">策略回测</h1>
        <div style={{ color: 'var(--text-muted)' }}>用历史数据验证策略，先回测再实盘</div>
      </header>

      <div className="page-content">
        {/* 回测配置 */}
        <div className="widget">
          <div className="widget-title">回测配置</div>
          <div className="form-row">
            <div className="form-group">
              <label className="input-label">策略</label>
              <select className="trade-input" value={selectedStrategy} onChange={e => setSelectedStrategy(e.target.value)}>
                <option value="">-- 选择策略 --</option>
                {strategies.map(s => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="input-label">股票代码</label>
              <input className="trade-input" value={symbol} onChange={e => setSymbol(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="input-label">回测天数</label>
              <input className="trade-input" type="number" value={days} onChange={e => setDays(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="input-label">初始资金</label>
              <input className="trade-input" type="number" value={capital} onChange={e => setCapital(e.target.value)} />
            </div>
          </div>
          <div className="form-row" style={{ marginTop: 8 }}>
            <div className="form-group" style={{ flex: 3 }}>
              <label className="input-label">自定义参数 (JSON, 可选)</label>
              <input className="trade-input" value={customParams} onChange={e => setCustomParams(e.target.value)}
                placeholder='例如 {"short_period": 5, "long_period": 20}' />
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleRun} disabled={loading || !selectedStrategy} style={{ marginTop: 16 }}>
            {loading ? '回测运行中...' : '开始回测'}
          </button>

          {error && <div style={{ color: 'var(--accent-red)', marginTop: 12 }}>{error}</div>}
        </div>

        {/* 回测结果 */}
        {result && (
          <>
            {/* 核心指标 */}
            <div className="widget">
              <div className="widget-title">
                {result.strategy_name} · {result.symbol} · {result.start_date} ~ {result.end_date}
              </div>
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-label">总收益率</div>
                  <div className={`metric-value ${result.total_return >= 0 ? 'text-green' : 'text-red'}`}>
                    {result.total_return >= 0 ? '+' : ''}{result.total_return}%
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">年化收益率</div>
                  <div className={`metric-value ${result.annual_return >= 0 ? 'text-green' : 'text-red'}`}>
                    {result.annual_return >= 0 ? '+' : ''}{result.annual_return}%
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">最大回撤</div>
                  <div className="metric-value text-red">-{result.max_drawdown}%</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">夏普比率</div>
                  <div className={`metric-value ${result.sharpe_ratio >= 1 ? 'text-green' : result.sharpe_ratio >= 0 ? '' : 'text-red'}`}>
                    {result.sharpe_ratio}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">胜率</div>
                  <div className={`metric-value ${result.win_rate >= 50 ? 'text-green' : 'text-red'}`}>
                    {result.win_rate}%
                  </div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">盈亏比</div>
                  <div className="metric-value">{result.profit_factor === Infinity ? '∞' : result.profit_factor}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">总交易次数</div>
                  <div className="metric-value">{result.total_trades}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">最终资金</div>
                  <div className={`metric-value ${result.final_capital >= result.initial_capital ? 'text-green' : 'text-red'}`}>
                    ${result.final_capital.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>

            {/* 权益曲线 */}
            <div className="widget">
              <div className="widget-title">权益曲线</div>
              <div ref={chartContainerRef} style={{ width: '100%', height: 300 }} />
            </div>

            {/* 交易明细 */}
            {result.trade_log.length > 0 && (
              <div className="widget">
                <div className="widget-title">交易明细 ({result.trade_log.length}笔)</div>
                <div className="table-container">
                  <table className="data-table">
                    <thead>
                      <tr><th>时间</th><th>操作</th><th>价格</th><th>数量</th><th>盈亏</th><th>余额</th><th>信号原因</th></tr>
                    </thead>
                    <tbody>
                      {result.trade_log.map((t, i) => (
                        <tr key={i}>
                          <td>{t.time}</td>
                          <td className={t.action === 'BUY' ? 'text-green' : 'text-red'}>{t.action === 'BUY' ? '买入' : '卖出'}</td>
                          <td>${t.price}</td>
                          <td>{t.quantity}</td>
                          <td className={(t.pnl || 0) >= 0 ? 'text-green' : 'text-red'}>{t.pnl != null ? `$${t.pnl}` : '—'}</td>
                          <td>${t.capital_after?.toLocaleString()}</td>
                          <td style={{ fontSize: 12, maxWidth: 300 }}>{t.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
