"""Word 文档生成模块（docx 延迟加载，未安装时 app 仍能启动）"""

from datetime import datetime
from pathlib import Path
from .config import OUTPUT_DIR


def _set_chinese_font(style):
    """安全地设置中文字体（跨平台兼容）"""
    try:
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        rpr = style.element.get_or_add_rPr()
        fonts = rpr.find(qn('w:rFonts'))
        if fonts is None:
            fonts = OxmlElement('w:rFonts')
            rpr.append(fonts)
        fonts.set(qn('w:eastAsia'), '苹方-简')
    except Exception:
        pass


def generate_word_doc(
    videos: list[dict],
    creator_name: str,
    douyin_id: str,
) -> Path:
    """生成包含所有文字稿的 Word 文档"""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise ImportError("python-docx 未安装。请运行: pip install python-docx")

    doc = Document()

    # 设置默认字体
    style = doc.styles["Normal"]
    style.font.size = Pt(11)
    _set_chinese_font(style)

    # --- 封面页 ---
    doc.add_paragraph()
    doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(creator_name)
    run.font.size = Pt(36)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
    run.bold = True

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("抖音视频文字稿合集")
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run(f"\n抖音号: {douyin_id}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    total_videos = len(videos)
    transcribed = sum(1 for v in videos if v.get("transcript"))
    info2 = doc.add_paragraph()
    info2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info2.add_run(f"共 {total_videos} 个视频 | 已转录 {transcribed} 个")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    date_info = doc.add_paragraph()
    date_info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_info.add_run(f"生成日期: {datetime.now().strftime('%Y年%m月%d日')}")
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)

    doc.add_page_break()

    # --- 目录页 ---
    doc.add_heading("目录", level=1)
    chapter_num = 0
    for video in videos:
        if video.get("transcript"):
            chapter_num += 1
            title_text = video.get("title", f"视频 {chapter_num}")[:60]
            time_str = _format_time(video.get("create_time", ""))
            toc_entry = doc.add_paragraph()
            toc_entry.paragraph_format.space_after = Pt(2)
            run = toc_entry.add_run(f"{chapter_num}. {title_text}")
            run.font.size = Pt(10)
            if time_str:
                run2 = toc_entry.add_run(f"  ({time_str})")
                run2.font.size = Pt(9)
                run2.font.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)

    doc.add_page_break()

    # --- 文字稿正文 ---
    chapter_num = 0
    for video in videos:
        transcript = video.get("transcript")
        if not transcript:
            continue

        chapter_num += 1
        title_text = video.get("title", f"视频 {chapter_num}")

        doc.add_heading(f"{chapter_num}. {title_text}", level=2)

        # 元信息
        meta_parts = []
        time_str = _format_time(video.get("create_time", ""))
        if time_str:
            meta_parts.append(f"发布时间: {time_str}")
        if video.get("duration"):
            duration = video["duration"]
            if isinstance(duration, (int, float)) and duration > 0:
                minutes, seconds = divmod(int(duration), 60)
                meta_parts.append(f"时长: {minutes}:{seconds:02d}")

        if meta_parts:
            meta = doc.add_paragraph()
            run = meta.add_run("  |  ".join(meta_parts))
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

        # 文字稿内容
        text = transcript.get("text", "") if isinstance(transcript, dict) else str(transcript)
        if text:
            doc.add_paragraph(text)

        # 分隔线
        sep = doc.add_paragraph()
        sep.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = sep.add_run("─" * 40)
        run.font.color.rgb = RGBColor(0xDD, 0xDD, 0xDD)

    # 保存
    filename = f"{douyin_id}_文字稿合集_{datetime.now().strftime('%Y%m%d')}.docx"
    output_path = OUTPUT_DIR / filename
    doc.save(str(output_path))
    return output_path


def _format_time(time_val) -> str:
    """格式化时间显示"""
    if not time_val:
        return ""
    if isinstance(time_val, (int, float)):
        try:
            return datetime.fromtimestamp(time_val).strftime("%Y-%m-%d")
        except (OSError, ValueError, OverflowError):
            return ""
    if isinstance(time_val, str):
        return time_val[:10]
    return ""
