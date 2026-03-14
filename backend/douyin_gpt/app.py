"""抖音博主文字稿提取 & GPT 对话工具 — Streamlit 主应用"""

import streamlit as st
from pathlib import Path

from .config import APIFY_API_TOKEN, ANTHROPIC_API_KEY, TRANSCRIPTS_DIR
from .scraper import get_creator_videos, download_all_audios, save_video_list, apify_get_transcripts
from .transcriber import transcribe_all, save_transcripts, load_transcripts
from .doc_generator import generate_word_doc
from .chat_engine import CreatorChat


def _check_dependencies():
    """启动时检查关键依赖"""
    missing = []
    try:
        import apify_client  # noqa: F401
    except ImportError:
        missing.append("apify-client")
    try:
        import docx  # noqa: F401
    except ImportError:
        missing.append("python-docx")
    try:
        import anthropic  # noqa: F401
    except ImportError:
        missing.append("anthropic (对话功能需要)")
    # whisper 不在这里检查，因为它是可选的（有抖音字幕就不需要）
    return missing


def main():
    st.set_page_config(
        page_title="抖音博主 GPT",
        page_icon="🎬",
        layout="wide",
    )

    st.title("🎬 抖音博主文字稿 & GPT 对话")

    # 启动时检查依赖
    missing = _check_dependencies()
    if missing:
        st.error(
            f"缺少依赖包: {', '.join(missing)}\n\n"
            "请运行: `pip install -r douyin_gpt/requirements.txt`"
        )
        return
    st.caption("输入抖音号 → 自动提取所有视频文字稿 → 生成 Word + 博主 GPT 对话")

    # ─── 侧边栏：配置检查 ───
    with st.sidebar:
        st.header("⚙️ 配置状态")

        if APIFY_API_TOKEN:
            st.success("✅ Apify API Token 已配置")
        else:
            st.warning("⚠️ Apify Token 未设置")
            apify_input = st.text_input("Apify API Token", type="password", key="apify_token_input")
            if apify_input:
                st.info("请将 Token 写入 backend/.env 文件后重启")

        if ANTHROPIC_API_KEY:
            st.success("✅ Anthropic API Key 已配置")
        else:
            st.warning("⚠️ Anthropic Key 未设置（对话功能需要）")

        st.divider()

        # 显示已处理的博主
        st.header("📁 已处理的博主")
        existing = list(TRANSCRIPTS_DIR.glob("*_transcripts.json"))
        if existing:
            for f in existing:
                creator_id = f.stem.replace("_transcripts", "")
                if st.button(f"📂 {creator_id}", key=f"load_{creator_id}"):
                    st.session_state["loaded_creator_id"] = creator_id
                    st.rerun()
        else:
            st.caption("还没有处理过的博主")

    # ─── 主界面 ───
    tab1, tab2 = st.tabs(["📥 提取文字稿", "💬 博主 GPT 对话"])

    with tab1:
        _render_extraction_tab()

    with tab2:
        _render_chat_tab()


def _render_extraction_tab():
    """文字稿提取界面"""

    col1, col2 = st.columns([3, 1])
    with col1:
        douyin_id = st.text_input(
            "抖音号",
            placeholder="输入博主的抖音号（如：douyin_creator_123）",
            help="在抖音 App 中查看博主主页，复制抖音号即可",
        )
    with col2:
        creator_name = st.text_input(
            "博主名称（可选）",
            placeholder="用于 Word 封面",
            value="",
        )

    max_videos = st.slider("最大视频数量", 10, 500, 100, step=10)

    if st.button("🚀 开始提取", type="primary", disabled=not douyin_id):
        if not creator_name:
            creator_name = douyin_id

        _run_extraction(douyin_id, creator_name, max_videos)

    # 检查是否有从侧边栏加载的博主
    if "loaded_creator_id" in st.session_state:
        loaded_id = st.session_state.pop("loaded_creator_id")
        transcripts = load_transcripts(loaded_id)
        if transcripts:
            st.success(f"已加载 {loaded_id} 的 {len(transcripts)} 条文字稿")
            st.session_state["current_transcripts"] = transcripts
            st.session_state["current_creator_id"] = loaded_id
            st.session_state["current_creator_name"] = loaded_id

    # 显示结果
    if "current_transcripts" in st.session_state:
        _show_results()


def _run_extraction(douyin_id: str, creator_name: str, max_videos: int):
    """执行完整的提取流程"""

    progress_bar = st.progress(0, text="准备中...")
    status = st.empty()

    try:
        # 步骤1: 获取视频列表
        status.info("📡 正在获取博主视频列表...")
        progress_bar.progress(0.05, text="获取视频列表...")

        videos = get_creator_videos(
            douyin_id,
            max_videos=max_videos,
            progress_callback=lambda p, t: progress_bar.progress(
                min(0.05 + p * 0.15, 0.19), text=t
            ),
        )

        status.success(f"✅ 获取到 {len(videos)} 个视频")
        save_video_list(videos, douyin_id)

        # 步骤2: 尝试直接获取抖音字幕（Apify 文字稿 Actor）
        status.info("📝 尝试直接提取抖音字幕...")
        progress_bar.progress(0.2, text="提取抖音字幕...")

        apify_transcripts = {}
        if APIFY_API_TOKEN:
            try:
                transcript_items = apify_get_transcripts(douyin_id)
                for item in transcript_items:
                    vid = item.get("id", item.get("aweme_id", ""))
                    if vid and item.get("transcript"):
                        apify_transcripts[str(vid)] = {
                            "text": item["transcript"],
                            "segments": [],
                            "language": "zh",
                            "source": "douyin_subtitle",
                        }
            except Exception as e:
                st.warning(f"字幕提取跳过: {e}")

        if apify_transcripts:
            status.success(f"✅ 从抖音字幕直接获取了 {len(apify_transcripts)} 条文字稿")

        # 将已获取的字幕合并到视频列表
        need_whisper = []
        for v in videos:
            vid = str(v.get("id", ""))
            if vid in apify_transcripts:
                v["transcript"] = apify_transcripts[vid]
            else:
                need_whisper.append(v)

        # 步骤3: 对没有字幕的视频，下载音频 + Whisper 转录
        if need_whisper:
            status.info(f"🔊 还有 {len(need_whisper)} 个视频需要下载音频并转录...")
            progress_bar.progress(0.35, text="下载音频...")

            need_whisper = download_all_audios(
                need_whisper,
                progress_callback=lambda p, t: progress_bar.progress(
                    min(0.35 + p * 0.25, 0.59), text=t
                ),
            )

            status.info("🤖 Whisper 转录中（这可能需要一些时间）...")
            progress_bar.progress(0.6, text="Whisper 转录中...")

            need_whisper = transcribe_all(
                need_whisper,
                progress_callback=lambda p, t: progress_bar.progress(
                    min(0.6 + p * 0.25, 0.84), text=t
                ),
            )

            # 合并回主列表
            whisper_map = {str(v.get("id", "")): v for v in need_whisper}
            for v in videos:
                vid = str(v.get("id", ""))
                if vid in whisper_map and whisper_map[vid].get("transcript"):
                    v["transcript"] = whisper_map[vid]["transcript"]

        # 步骤4: 保存转录结果
        save_transcripts(videos, douyin_id)

        # 步骤5: 生成 Word 文档
        status.info("📄 生成 Word 文档...")
        progress_bar.progress(0.9, text="生成 Word 文档...")

        doc_path = generate_word_doc(videos, creator_name, douyin_id)

        progress_bar.progress(1.0, text="✅ 完成！")

        transcribed_count = sum(1 for v in videos if v.get("transcript"))
        status.success(
            f"🎉 完成！共 {len(videos)} 个视频，成功转录 {transcribed_count} 个"
        )

        # 保存到 session state
        st.session_state["current_transcripts"] = videos
        st.session_state["current_creator_id"] = douyin_id
        st.session_state["current_creator_name"] = creator_name
        st.session_state["doc_path"] = str(doc_path)

    except Exception as e:
        progress_bar.empty()
        status.error(f"❌ 出错了: {str(e)}")
        st.exception(e)


def _show_results():
    """显示提取结果"""
    videos = st.session_state["current_transcripts"]
    transcribed = [v for v in videos if v.get("transcript")]

    st.divider()
    st.subheader(f"📊 结果：{len(transcribed)}/{len(videos)} 个视频已转录")

    # Word 下载按钮
    if "doc_path" in st.session_state:
        doc_path = Path(st.session_state["doc_path"])
        if doc_path.exists():
            with open(doc_path, "rb") as f:
                st.download_button(
                    label="📥 下载 Word 文档",
                    data=f.read(),
                    file_name=doc_path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                )

    # 文字稿预览
    with st.expander("📜 文字稿预览", expanded=False):
        for i, v in enumerate(transcribed[:20]):
            st.markdown(f"**{i+1}. {v.get('title', '无标题')[:60]}**")
            transcript = v.get("transcript", {})
            text = transcript.get("text", "") if isinstance(transcript, dict) else str(transcript)
            st.text(text[:300] + ("..." if len(text) > 300 else ""))
            st.divider()

        if len(transcribed) > 20:
            st.caption(f"...还有 {len(transcribed) - 20} 条文字稿，请下载 Word 查看完整内容")


def _render_chat_tab():
    """博主 GPT 对话界面"""

    if "current_transcripts" not in st.session_state:
        st.info("👈 请先在「提取文字稿」标签页中提取博主的视频文字稿")
        return

    if not ANTHROPIC_API_KEY:
        st.error("❌ 需要设置 ANTHROPIC_API_KEY 才能使用对话功能")
        return

    creator_id = st.session_state.get("current_creator_id", "")
    creator_name = st.session_state.get("current_creator_name", "博主")
    videos = st.session_state["current_transcripts"]

    st.subheader(f"💬 与「{creator_name}」对话")
    st.caption(f"基于 {sum(1 for v in videos if v.get('transcript'))} 个视频的文字稿，模仿博主的思路和风格回复")

    # 对话引擎和消息都按博主 ID 隔离
    engine_key = f"chat_engine_{creator_id}"
    messages_key = f"chat_messages_{creator_id}"

    if engine_key not in st.session_state:
        try:
            st.session_state[engine_key] = CreatorChat(creator_name, videos)
        except ValueError as e:
            st.error(str(e))
            return

    chat_engine: CreatorChat = st.session_state[engine_key]

    # 重置按钮
    if st.button("🔄 重新开始对话"):
        chat_engine.reset()
        st.session_state[messages_key] = []
        st.rerun()

    # 对话历史显示
    if messages_key not in st.session_state:
        st.session_state[messages_key] = []

    for msg in st.session_state[messages_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 用户输入
    if prompt := st.chat_input(f"问「{creator_name}」点什么..."):
        st.session_state[messages_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"「{creator_name}」正在思考..."):
                response = chat_engine.chat(prompt)
            st.markdown(response)

        st.session_state[messages_key].append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
