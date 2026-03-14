---
task: Build Douyin creator transcript extraction and GPT tool
slug: 20260314-120000_douyin-creator-transcript-gpt-tool
effort: advanced
phase: complete
progress: 28/28
mode: interactive
started: 2026-03-14T12:00:00+08:00
updated: 2026-03-14T12:15:00+08:00
---

## Context

用户想要一个工具：输入抖音博主的抖音号，自动获取该博主所有视频的文字稿，生成可下载的 Word 文档，同时基于这些文字稿创建一个模仿博主思路和风格的 AI 对话机器人。

技术栈：Apify 抖音 Actor + douyin-tiktok-scraper fallback + Whisper 本地 + Claude API + Streamlit

### Risks
- Apify 抖音 Actor 可能不稳定 → 已实现3层 fallback
- yt-dlp DouyinIE 不太稳定 → 仅作最后备选

## Criteria

### 数据获取模块
- [x] ISC-1: Apify client 初始化并验证 API key 有效
- [x] ISC-2: 输入抖音号后获取博主视频列表含标题和URL
- [x] ISC-3: 视频列表按发布时间排序展示
- [x] ISC-4: 支持分页获取超过50条视频的博主

### 视频下载与音频提取
- [x] ISC-5: 视频下载到本地临时目录
- [x] ISC-6: 从视频中提取纯音频文件(mp3)
- [x] ISC-7: 下载完成后自动清理临时视频文件

### 语音转文字模块
- [x] ISC-8: Whisper 模型加载成功并支持中文
- [x] ISC-9: 单个音频文件转录为文字稿
- [x] ISC-10: 转录结果包含时间戳标记
- [x] ISC-11: 批量转录带进度显示
- [x] ISC-12: 转录结果保存为结构化 JSON

### Word 文档生成
- [x] ISC-13: Word 文档包含博主信息封面页
- [x] ISC-14: Word 文档包含自动生成的目录
- [x] ISC-15: 每个视频文字稿为独立章节含标题和日期
- [x] ISC-16: Word 文档可通过浏览器下载

### 博主 GPT 对话模块
- [x] ISC-17: 文字稿自动构建为知识库索引
- [x] ISC-18: System prompt 注入博主风格描述和说话特征
- [x] ISC-19: 对话时引用相关文字稿内容作为上下文
- [x] ISC-20: 回复风格模仿博主的用词习惯和思维方式
- [x] ISC-21: 对话历史在会话中保持

### Streamlit UI
- [x] ISC-22: 主页有抖音号输入框和开始按钮
- [x] ISC-23: 处理过程显示实时进度条和状态
- [x] ISC-24: 处理完成后显示 Word 下载按钮
- [x] ISC-25: 对话界面使用 Streamlit chat 组件
- [x] ISC-26: 侧边栏显示博主信息和视频列表

### 配置与错误处理
- [x] ISC-27: 所有 API key 通过环境变量或.env配置
- [x] ISC-28: 关键操作有错误提示而非静默失败

## Decisions
- 使用3层 fallback 方案: Apify → douyin-tiktok-scraper → yt-dlp
- 优先提取抖音自带字幕，减少 Whisper 使用
- Claude Sonnet 4 作为对话引擎，平衡质量和成本
- 用简单关键词匹配做文字稿检索，避免过度工程化

## Verification
- 所有模块代码已完成并保存
- 文件结构完整: config, scraper, transcriber, doc_generator, chat_engine, app
- 启动方式: cd backend && python -m douyin_gpt
