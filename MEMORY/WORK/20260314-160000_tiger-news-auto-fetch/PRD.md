---
task: 接入老虎证券新闻API实现自动抓取分析
slug: 20260314-160000_tiger-news-auto-fetch
effort: standard
phase: complete
progress: 10/10
mode: autonomous
started: 2026-03-14T16:00:00+08:00
updated: 2026-03-14T16:20:00+08:00
---

## Context

用户要求实现自动新闻抓取和分析，不仅用Tiger API，还用多个LLM实时搜索获取最新新闻。全自动执行，不需要用户参与。

Tiger API没有专门的新闻标题API，用corporate_earnings_calendar、corporate_dividend、corporate_split等公司事件接口替代。DeepSeek和Perplexity用于实时新闻搜索。

### Risks
- Tiger API的公司事件数据有限，不是真正的新闻
- LLM搜索依赖API可用性和联网能力
- 已通过缓存+非阻塞设计缓解

## Criteria

- [x] ISC-1: news_fetcher.py模块创建，包含NewsFetcher类
- [x] ISC-2: Tiger API数据源实现（earnings_calendar + dividend + split）
- [x] ISC-3: DeepSeek联网搜索新闻源实现
- [x] ISC-4: Perplexity搜索新闻源实现（可选，按API key配置）
- [x] ISC-5: 多源新闻聚合和去重逻辑
- [x] ISC-6: 缓存机制防止重复抓取（TTL过期+LRU淘汰）
- [x] ISC-7: 自动定时抓取（后台daemon线程，线程安全）
- [x] ISC-8: main.py添加6个新闻API端点
- [x] ISC-9: 策略引擎startup自动初始化新闻聚合器
- [x] ISC-10: news_strategy.py用缓存读取自动获取新闻（不阻塞交易）

## Decisions

- DeepSeek/Perplexity统一为LLMNewsSource基类，消除70+行重复代码
- news_strategy使用get_cached_headlines()而非get_headlines()，避免热路径阻塞
- get_all_news()仅读缓存，不触发网络请求
- 缓存上限200个symbol，LRU淘汰
- 所有_shutdown/_watch_symbols操作都加锁

## Verification

- 11个Python文件语法验证全部通过
- 8项功能验证全部通过（数据结构、初始化、缓存读取、淘汰、线程安全、单例、基类）
- news_strategy在venv中导入和初始化成功
- /simplify代码审查完成，修复6个问题
