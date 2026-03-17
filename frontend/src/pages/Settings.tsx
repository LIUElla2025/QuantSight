import { useState } from 'react'

const API = 'http://localhost:8000'

export default function Settings() {
  const [apiStatus, setApiStatus] = useState<string>('未检测')
  const [checking, setChecking] = useState(false)

  // API Key 认证
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('quantsight_api_key') || '')
  const [keySaved, setKeySaved] = useState(false)

  const saveApiKey = () => {
    const trimmed = apiKey.trim()
    if (trimmed) {
      localStorage.setItem('quantsight_api_key', trimmed)
    } else {
      localStorage.removeItem('quantsight_api_key')
    }
    setKeySaved(true)
    setTimeout(() => setKeySaved(false), 2000)
  }

  // LLM 情绪分析测试
  const [sentimentSymbol, setSentimentSymbol] = useState('AAPL')
  const [sentimentText, setSentimentText] = useState('')
  const [sentimentResult, setSentimentResult] = useState<any>(null)
  const [sentimentLoading, setSentimentLoading] = useState(false)

  const checkConnection = () => {
    setChecking(true)
    setApiStatus('检测中...')
    fetch(`${API}/`)
      .then(r => r.json())
      .then(d => {
        if (d.status === 'ok') setApiStatus('后端连接正常')
        else setApiStatus('后端响应异常')
      })
      .catch(() => setApiStatus('无法连接后端'))
      .finally(() => setChecking(false))

    // 测试老虎证券连接
    fetch(`${API}/api/account`)
      .then(r => r.json())
      .then(d => {
        if (d.success) setApiStatus(prev => prev + ' · 老虎证券连接正常')
        else setApiStatus(prev => prev + ` · 老虎证券: ${d.error}`)
      })
      .catch(() => {})
  }

  const testSentiment = () => {
    if (!sentimentText.trim()) return
    setSentimentLoading(true)
    setSentimentResult(null)
    fetch(`${API}/api/sentiment/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol: sentimentSymbol, text: sentimentText }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.success) setSentimentResult(d.data)
        else setSentimentResult({ error: d.error })
      })
      .catch(e => setSentimentResult({ error: e.message }))
      .finally(() => setSentimentLoading(false))
  }

  return (
    <>
      <header className="topbar">
        <h1 className="page-title">系统设置</h1>
      </header>

      <div className="page-content">
        {/* 连接状态 */}
        <div className="widget">
          <div className="widget-title">连接检测</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <button className="btn btn-primary" onClick={checkConnection} disabled={checking}>
              {checking ? '检测中...' : '检测连接'}
            </button>
            <span style={{ color: apiStatus.includes('正常') ? 'var(--accent-green)' : 'var(--text-muted)' }}>
              {apiStatus}
            </span>
          </div>
        </div>

        {/* API Key 认证 */}
        <div className="widget" style={{ borderColor: 'rgba(255, 61, 0, 0.3)' }}>
          <div className="widget-title" style={{ color: 'var(--accent-red)' }}>交易接口认证</div>
          <div className="settings-info">
            <p>设置 API Key 后，所有交易操作（买卖、启停策略）需要携带此密钥。密钥需与后端 <code>.env</code> 中的 <code>API_SECRET_KEY</code> 一致。</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12 }}>
            <input
              className="trade-input"
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="输入 API Secret Key"
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={saveApiKey}>
              {keySaved ? '已保存' : '保存'}
            </button>
          </div>
          {apiKey && (
            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
              当前已配置密钥（{apiKey.length}位），所有交易请求将自动携带
            </div>
          )}
        </div>

        {/* API 配置说明 */}
        <div className="widget">
          <div className="widget-title">老虎证券 API 配置</div>
          <div className="settings-info">
            <p>在后端 <code>.env</code> 文件中配置以下变量：</p>
            <div className="code-block">
              <div>TIGER_ID=你的开发者ID</div>
              <div>TIGER_ACCOUNT=你的资金账户</div>
              <div>TIGER_PRIVATE_KEY=你的RSA私钥</div>
            </div>
            <p style={{ marginTop: 16 }}>获取方式：</p>
            <ol>
              <li>登录老虎证券开发者后台</li>
              <li>创建应用并获取 Tiger ID</li>
              <li>生成 RSA 密钥对，上传公钥到开发者后台</li>
              <li>将私钥内容填入 .env 文件</li>
            </ol>
          </div>
        </div>

        {/* DeepSeek LLM 配置 */}
        <div className="widget">
          <div className="widget-title">DeepSeek LLM 配置</div>
          <div className="settings-info">
            <p>在后端 <code>.env</code> 文件中配置以下变量：</p>
            <div className="code-block">
              <div>DEEPSEEK_API_KEY=你的DeepSeek API Key</div>
              <div>DEEPSEEK_BASE_URL=https://api.deepseek.com</div>
            </div>
            <p style={{ marginTop: 16 }}>功能说明：</p>
            <ul>
              <li>用 DeepSeek 大模型分析新闻/财报对股价的影响</li>
              <li>情绪评分范围：-1.0（极度看空）到 +1.0（极度看多）</li>
              <li>可与多因子策略结合使用（LLM情绪增强策略）</li>
              <li>DeepSeek API 价格约为 GPT-4 的 1/50，性价比极高</li>
            </ul>
          </div>
        </div>

        {/* LLM 情绪分析测试 */}
        <div className="widget" style={{ borderColor: 'rgba(41, 98, 255, 0.3)' }}>
          <div className="widget-title" style={{ color: 'var(--accent-blue)' }}>LLM 情绪分析测试</div>
          <div className="form-row">
            <div className="form-group">
              <label className="input-label">股票代码</label>
              <input className="trade-input" value={sentimentSymbol} onChange={e => setSentimentSymbol(e.target.value)} />
            </div>
          </div>
          <div className="form-row" style={{ marginTop: 8 }}>
            <div className="form-group" style={{ flex: 3 }}>
              <label className="input-label">新闻/财报文本</label>
              <textarea
                className="trade-input"
                value={sentimentText}
                onChange={e => setSentimentText(e.target.value)}
                placeholder="粘贴新闻或财报内容，DeepSeek 会分析对股价的影响..."
                style={{ minHeight: 80, resize: 'vertical', fontFamily: 'inherit' }}
              />
            </div>
          </div>
          <button className="btn btn-primary" onClick={testSentiment} disabled={sentimentLoading || !sentimentText.trim()} style={{ marginTop: 12 }}>
            {sentimentLoading ? 'DeepSeek 分析中...' : '分析情绪'}
          </button>

          {sentimentResult && !sentimentResult.error && (
            <div style={{ marginTop: 16, padding: 16, background: 'var(--bg-dark)', borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 12 }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>情绪评分</div>
                  <div style={{
                    fontSize: 28, fontWeight: 700,
                    color: sentimentResult.score > 0.2 ? 'var(--accent-green)' : sentimentResult.score < -0.2 ? 'var(--accent-red)' : 'var(--text-muted)'
                  }}>
                    {sentimentResult.score > 0 ? '+' : ''}{sentimentResult.score?.toFixed(2)}
                  </div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>置信度</div>
                  <div style={{ fontSize: 28, fontWeight: 700 }}>{(sentimentResult.confidence * 100)?.toFixed(0)}%</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>建议</div>
                  <div style={{
                    fontSize: 28, fontWeight: 700,
                    color: sentimentResult.recommendation === 'BUY' ? 'var(--accent-green)' : sentimentResult.recommendation === 'SELL' ? 'var(--accent-red)' : 'var(--text-muted)'
                  }}>
                    {sentimentResult.recommendation === 'BUY' ? '买入' : sentimentResult.recommendation === 'SELL' ? '卖出' : '观望'}
                  </div>
                </div>
              </div>
              <div style={{ color: 'var(--text-main)', marginBottom: 8 }}>{sentimentResult.summary}</div>
              {sentimentResult.key_factors?.length > 0 && (
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 4 }}>关键因素</div>
                  <ul style={{ paddingLeft: 20, color: 'var(--text-muted)' }}>
                    {sentimentResult.key_factors.map((f: string, i: number) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          {sentimentResult?.error && (
            <div style={{ color: 'var(--accent-red)', marginTop: 12 }}>{sentimentResult.error}</div>
          )}
        </div>

        {/* 策略参数说明 */}
        <div className="widget">
          <div className="widget-title">内置策略说明</div>
          <div className="settings-info">
            <div className="strategy-doc">
              <h3>1. MA交叉策略 (ma_cross)</h3>
              <p>双均线金叉买入、死叉卖出。参数：short_period(短期均线, 默认5), long_period(长期均线, 默认20), quantity(下单数量, 默认100)</p>
            </div>
            <div className="strategy-doc">
              <h3>2. RSI策略 (rsi)</h3>
              <p>RSI超卖买入、超买卖出。参数：period(RSI周期, 默认14), oversold(超卖线, 默认30), overbought(超买线, 默认70)</p>
            </div>
            <div className="strategy-doc">
              <h3>3. 布林带策略 (bollinger)</h3>
              <p>价格触及布林带上下轨反向交易。参数：period(均线周期, 默认20), std_dev(标准差倍数, 默认2.0)</p>
            </div>
            <div className="strategy-doc">
              <h3>4. MACD策略 (macd)</h3>
              <p>MACD金叉买入、死叉卖出。参数：fast(快线, 默认12), slow(慢线, 默认26), signal(信号线, 默认9)</p>
            </div>
            <div className="strategy-doc">
              <h3>5. 放量突破策略 (volume_breakout)</h3>
              <p>价格突破+成交量放大时入场。参数：lookback(回看天数, 默认20), volume_ratio(量比阈值, 默认1.5)</p>
            </div>
            <div className="strategy-doc" style={{ borderLeft: '3px solid var(--accent-blue)', paddingLeft: 16 }}>
              <h3>6. 多因子融合策略 (multi_factor) [研究驱动]</h3>
              <p>RSI+MACD+布林带+均线+量价五因子加权投票，多数确认才交易。灵感来源：Two Sigma / D.E. Shaw 多信号融合。参数：buy_threshold(买入需要几个因子确认, 默认3), sell_threshold(卖出需要几个因子确认, 默认3), stop_loss_pct(止损百分比, 默认0.07), take_profit_pct(止盈百分比, 默认0.20)</p>
            </div>
            <div className="strategy-doc" style={{ borderLeft: '3px solid var(--accent-blue)', paddingLeft: 16 }}>
              <h3>7. 趋势跟踪+动态对冲 (trend_tail_hedge) [研究驱动]</h3>
              <p>三重均线确认趋势+ATR动态止损+追踪止盈。灵感来源：CTA趋势跟踪 + Goldman Sachs尾部对冲研究。参数：fast_ma(快线, 默认10), mid_ma(中线, 默认20), slow_ma(慢线, 默认50), atr_stop_multiplier(ATR止损倍数, 默认2.5), atr_profit_multiplier(ATR止盈倍数, 默认4.0)</p>
            </div>
            <div className="strategy-doc" style={{ borderLeft: '3px solid var(--accent-blue)', paddingLeft: 16 }}>
              <h3>8. 短期反转策略 (mean_reversion) [研究驱动·港股特效]</h3>
              <p>捕捉散户过度反应造成的短期价格偏离。港股/A股散户占80%交易量，反转因子特别有效。参数：lookback(回看天数, 默认5), deviation_threshold(跌幅阈值, 默认-0.05), rsi_oversold(超卖RSI, 默认25), max_holding_days(最大持仓天数, 默认10)</p>
            </div>
            <div className="strategy-doc" style={{ borderLeft: '3px solid #e040fb', paddingLeft: 16 }}>
              <h3>9. LLM情绪增强策略 (llm_sentiment) [AI驱动·DeepSeek]</h3>
              <p>DeepSeek大模型分析新闻/财报情绪 + 多因子技术面双重确认。技术面看"图"，LLM看"新闻"，两者结合大幅降低假信号。参数：sentiment_weight(情绪权重, 默认0.4), sentiment_threshold(情绪阈值, 默认0.3), require_sentiment_confirm(是否要求情绪确认, 默认true), headlines(新闻标题列表)</p>
            </div>
          </div>
        </div>

        {/* 风险提示 */}
        <div className="widget" style={{ borderColor: 'rgba(255, 61, 0, 0.3)' }}>
          <div className="widget-title" style={{ color: 'var(--accent-red)' }}>风险提示</div>
          <div className="settings-info">
            <p>自动化交易涉及资金风险，请注意：</p>
            <ul>
              <li>所有策略都有止损机制，但不保证在极端行情下能完全执行</li>
              <li>建议先用小资金测试，确认策略有效后再加大仓位</li>
              <li>回测结果不代表未来表现，市场状况可能发生变化</li>
              <li>请确保账户有足够保证金，避免被强制平仓</li>
              <li>建议定期检查策略运行状态，及时处理异常情况</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  )
}
