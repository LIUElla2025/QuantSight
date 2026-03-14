---
task: 全面检查新闻抓取系统排除所有bug
slug: 20260314-163000_comprehensive-bug-review
effort: extended
phase: observe
progress: 0/16
mode: autonomous
started: 2026-03-14T16:30:00+08:00
updated: 2026-03-14T16:32:00+08:00
---

## Context

用户要求从头检查新闻抓取系统的所有代码，排除所有bug。涉及文件：news_fetcher.py, news_strategy.py, sentiment.py, main.py中的新闻API端点。

### Risks
- 去重逻辑对中文标题不够有效
- 路由已修复但可能有其他路由冲突
- 线程安全问题可能隐藏在边界条件中
- LLM返回内容过滤可能不够完善

## Criteria

- [ ] ISC-1: news_fetcher.py 语法正确无错误
- [ ] ISC-2: news_strategy.py 语法正确无错误
- [ ] ISC-3: sentiment.py 语法正确无错误
- [ ] ISC-4: main.py 新闻端点语法正确无错误
- [ ] ISC-5: 路由顺序正确，固定路径在通配路由之前
- [ ] ISC-6: NewsItem.to_dict() 字段完整且无异常
- [ ] ISC-7: 缓存读写和TTL过期逻辑正确
- [ ] ISC-8: LRU淘汰在超限时正常工作
- [ ] ISC-9: 去重逻辑对中英文新闻标题均有效
- [ ] ISC-10: 线程安全 — 并发读写缓存无竞态
- [ ] ISC-11: start/stop auto_fetch 生命周期正确
- [ ] ISC-12: OpenAI Responses API调用参数正确
- [ ] ISC-13: DeepSeek LLM源调用参数和解析正确
- [ ] ISC-14: API端点返回格式一致（success/error/data）
- [ ] ISC-15: startup初始化新闻聚合器错误处理正确
- [ ] ISC-16: LLM情绪策略从缓存读取新闻逻辑正确

## Decisions

## Verification
