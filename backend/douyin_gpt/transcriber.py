"""语音转文字模块 - 使用 OpenAI Whisper（延迟加载，不装 whisper 也不会崩）"""

import json
from pathlib import Path
from .config import WHISPER_MODEL, TRANSCRIPTS_DIR


_model = None
_whisper = None


def _ensure_whisper():
    """延迟 import whisper，避免未安装时整个 app 崩溃"""
    global _whisper
    if _whisper is None:
        try:
            import whisper
            _whisper = whisper
        except ImportError:
            raise ImportError(
                "Whisper 未安装。请运行:\n"
                "  pip install openai-whisper\n"
                "注意：Whisper 需要 PyTorch，首次安装可能需要下载 ~2GB。\n"
                "如果不需要本地转录（已从抖音字幕获取），可以跳过。"
            )
    return _whisper


def get_model():
    """延迟加载 Whisper 模型"""
    global _model
    if _model is None:
        whisper = _ensure_whisper()
        _model = whisper.load_model(WHISPER_MODEL)
    return _model


def transcribe_audio(audio_path: str | Path) -> dict:
    """转录单个音频文件"""
    model = get_model()
    result = model.transcribe(
        str(audio_path),
        language="zh",
        verbose=False,
    )

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "text": result["text"].strip(),
        "segments": segments,
        "language": result.get("language", "zh"),
    }


def transcribe_all(videos: list[dict], progress_callback=None) -> list[dict]:
    """批量转录所有视频音频"""
    has_audio = [v for v in videos if v.get("audio_path") and Path(v["audio_path"]).exists()]

    if not has_audio:
        return [{**v, "transcript": None} for v in videos]

    # 只在真正需要转录时才加载 Whisper
    try:
        _ensure_whisper()
    except ImportError as e:
        print(f"  {e}")
        return [{**v, "transcript": None} for v in videos]

    results = []
    total = len(has_audio)
    done = 0

    for video in videos:
        audio_path = video.get("audio_path")
        if not audio_path or not Path(audio_path).exists():
            results.append({**video, "transcript": None})
            continue

        if progress_callback:
            progress_callback(
                done / max(total, 1),
                f"转录中 ({done+1}/{total}): {video.get('title', '')[:30]}"
            )

        try:
            transcript = transcribe_audio(audio_path)
            results.append({**video, "transcript": transcript})
        except Exception as e:
            print(f"  转录失败: {video.get('title', '')[:30]} - {e}")
            results.append({**video, "transcript": None})

        done += 1

    return results


def save_transcripts(videos: list[dict], douyin_id: str) -> Path:
    """保存转录结果到 JSON"""
    output_path = TRANSCRIPTS_DIR / f"{douyin_id}_transcripts.json"

    save_data = []
    for v in videos:
        save_data.append({
            "id": v.get("id"),
            "title": v.get("title"),
            "create_time": v.get("create_time"),
            "duration": v.get("duration"),
            "transcript": v.get("transcript"),
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return output_path


def load_transcripts(douyin_id: str) -> list[dict] | None:
    """从文件加载已有的转录结果"""
    path = TRANSCRIPTS_DIR / f"{douyin_id}_transcripts.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
