"""博主 GPT 对话引擎 - 使用 Claude API"""

import re
from .config import ANTHROPIC_API_KEY

_anthropic = None


def _get_anthropic():
    """延迟 import anthropic，避免未安装时 app 启动崩溃"""
    global _anthropic
    if _anthropic is None:
        try:
            import anthropic
            _anthropic = anthropic
        except ImportError:
            raise ImportError(
                "anthropic 未安装。请运行: pip install anthropic"
            )
    return _anthropic

# Claude 上下文预算：system prompt 中放博主 profile 最多用 ~80K 字符
_MAX_PROFILE_CHARS = 80000
_MAX_CONTEXT_CHARS = 15000


def build_creator_profile(videos: list[dict]) -> str:
    """从文字稿中构建博主内容样本，控制总长度"""
    all_texts = []
    for v in videos:
        t = v.get("transcript")
        if t:
            text = t.get("text", "") if isinstance(t, dict) else str(t)
            if text:
                title = v.get("title", "")
                all_texts.append(f"【{title}】\n{text}")

    if not all_texts:
        return "该博主暂无可用的文字稿内容。"

    # 拼接文字稿，控制总长度不超过预算
    parts = []
    total_len = 0
    for text in all_texts:
        if total_len + len(text) > _MAX_PROFILE_CHARS:
            remaining = _MAX_PROFILE_CHARS - total_len
            if remaining > 200:
                parts.append(text[:remaining] + "...")
            break
        parts.append(text)
        total_len += len(text)

    return "\n\n---\n\n".join(parts)


def build_system_prompt(creator_name: str, creator_profile: str, context_texts: str) -> str:
    """构建模仿博主风格的 system prompt"""
    return f"""你是抖音博主「{creator_name}」的 AI 分身。你的任务是完全模仿这位博主的思维方式、说话风格、用词习惯和知识领域来回答问题。

## 你的身份
- 你就是「{creator_name}」，用第一人称说话
- 模仿这位博主的语气、口头禅、表达方式
- 回答问题时基于博主在视频中表达过的观点和知识
- 如果被问到博主没有涉及过的话题，用博主的风格说"这个我还真没怎么聊过"之类的话

## 博主的视频内容样本（用于学习风格和知识）
{creator_profile}

## 当前对话相关的参考内容
{context_texts}

## 行为规则
1. 始终保持博主的说话风格和语气
2. 优先使用博主在视频中表达过的观点来回答
3. 不要说"根据视频内容"或"在某个视频中"这样的元叙述，直接用博主的口吻说
4. 回答要自然、口语化，像博主在和粉丝聊天
5. 如果不确定博主的观点，可以用博主的风格表达自己的推测，但要坦诚"""


def _tokenize_chinese(text: str) -> list[str]:
    """简单的中文分词：按标点拆句，再提取2-4字的词组"""
    # 去除标点后按2-3字滑窗提取词组，同时保留完整短句
    words = set()
    # 按标点符号拆分成短句
    phrases = re.split(r'[，。？！、；：\s,.\?!;:\n]+', text)
    for phrase in phrases:
        phrase = phrase.strip()
        if not phrase:
            continue
        # 短句本身作为关键词
        if 2 <= len(phrase) <= 6:
            words.add(phrase)
        # 2-gram 和 3-gram
        for n in (2, 3):
            for i in range(len(phrase) - n + 1):
                words.add(phrase[i:i+n])
    return list(words)


def search_relevant_transcripts(query: str, videos: list[dict], top_k: int = 5) -> str:
    """基于词组匹配搜索相关文字稿"""
    query_words = _tokenize_chinese(query)
    if not query_words:
        return "（没有找到特别相关的视频内容）"

    scored = []
    for v in videos:
        t = v.get("transcript")
        if not t:
            continue
        text = t.get("text", "") if isinstance(t, dict) else str(t)
        if not text:
            continue

        # 按词组匹配计分
        score = sum(1 for w in query_words if w in text)
        if score > 0:
            scored.append((score, v.get("title", ""), text))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    if not top:
        return "（没有找到特别相关的视频内容）"

    parts = []
    total_len = 0
    for score, title, text in top:
        snippet = text[:800]
        if total_len + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        parts.append(f"【{title}】\n{snippet}")
        total_len += len(snippet)

    return "\n\n---\n\n".join(parts)


class CreatorChat:
    """博主 GPT 对话管理器"""

    def __init__(self, creator_name: str, videos: list[dict]):
        if not ANTHROPIC_API_KEY:
            raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量")

        anthropic = _get_anthropic()
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.creator_name = creator_name
        self.videos = videos
        self.creator_profile = build_creator_profile(videos)
        self.history: list[dict] = []

    def chat(self, user_message: str) -> str:
        """与博主 GPT 对话"""
        # 搜索相关文字稿作为上下文
        context = search_relevant_transcripts(user_message, self.videos)

        # 构建 system prompt
        system = build_system_prompt(
            self.creator_name,
            self.creator_profile,
            context,
        )

        # 添加用户消息到历史
        self.history.append({"role": "user", "content": user_message})

        # 保持历史在合理长度（最近20轮）
        recent_history = self.history[-40:]

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system,
                messages=recent_history,
            )

            assistant_message = response.content[0].text
            self.history.append({"role": "assistant", "content": assistant_message})
            return assistant_message

        except Exception as e:
            # 错误消息不加入历史，避免污染后续对话
            # 移除刚加入的用户消息，让用户可以重试
            self.history.pop()
            return f"对话出错: {str(e)}"

    def reset(self):
        """清空对话历史"""
        self.history = []
