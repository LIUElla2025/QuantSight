"""抖音博主视频数据获取模块

方案优先级:
1. Apify 抖音专用 Actor（最稳定）
2. douyin-tiktok-scraper PyPI 包（免费 fallback）
3. yt-dlp DouyinIE（最后备选，不太稳定）
"""

import json
import subprocess
import re
import threading
from pathlib import Path
from .config import APIFY_API_TOKEN, TEMP_DIR, AUDIO_DIR, TRANSCRIPTS_DIR


# ─── 方案1: Apify 抖音 Actor ───


def apify_get_creator_videos(douyin_id: str, max_videos: int = 200) -> list[dict]:
    """通过 Apify 抖音专用 Actor 获取博主视频列表"""
    if not APIFY_API_TOKEN:
        raise ValueError("请设置 APIFY_API_TOKEN 环境变量")

    from apify_client import ApifyClient
    client = ApifyClient(APIFY_API_TOKEN)

    actors = [
        {
            "id": "apibox/douyin-user-post-scraper",
            "input": {"userId": douyin_id, "maxItems": max_videos},
        },
        {
            "id": "natanielsantos/douyin-scraper",
            "input": {"profiles": [douyin_id], "resultsPerPage": max_videos},
        },
        {
            "id": "easyapi/douyin-video-downloader",
            "input": {"userId": douyin_id, "maxItems": max_videos},
        },
    ]

    for actor in actors:
        try:
            run = client.actor(actor["id"]).call(run_input=actor["input"])
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            if items:
                return _normalize_video_list(items)
        except Exception as e:
            print(f"  Apify Actor {actor['id']} 失败: {e}")
            continue

    return []


def apify_get_transcripts(douyin_id: str, video_urls: list[str] = None) -> list[dict]:
    """通过 Apify 高精度抖音文字稿 Actor 直接获取字幕"""
    if not APIFY_API_TOKEN:
        return []

    from apify_client import ApifyClient
    client = ApifyClient(APIFY_API_TOKEN)

    try:
        run_input = {"userId": douyin_id}
        if video_urls:
            run_input["urls"] = video_urls

        run = client.actor("apple_yang/high-accuracy-douyin-transcripts-scraper").call(
            run_input=run_input
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        return items
    except Exception as e:
        print(f"  Apify 文字稿 Actor 失败: {e}")
        return []


# ─── 方案2: douyin-tiktok-scraper (免费 fallback) ───


def pypi_get_creator_videos(douyin_id: str, max_videos: int = 200) -> list[dict]:
    """使用 douyin-tiktok-scraper PyPI 包获取博主视频"""
    try:
        import asyncio
        from douyin_tiktok_scraper.scraper import Scraper

        scraper = Scraper()

        async def _fetch():
            url = f"https://www.douyin.com/user/{douyin_id}"
            data = await scraper.hybrid_parsing(url)
            return data

        # 在独立线程中运行 asyncio，避免和 Streamlit 事件循环冲突
        result_holder = [None]
        error_holder = [None]

        def _run_in_thread():
            try:
                result_holder[0] = asyncio.run(_fetch())
            except Exception as e:
                error_holder[0] = e

        t = threading.Thread(target=_run_in_thread)
        t.start()
        t.join(timeout=60)

        if error_holder[0]:
            raise error_holder[0]

        result = result_holder[0]
        if isinstance(result, dict) and result.get("video_data"):
            return _normalize_video_list(result["video_data"][:max_videos])
        if isinstance(result, list):
            return _normalize_video_list(result[:max_videos])

    except ImportError:
        print("  douyin-tiktok-scraper 未安装，跳过此方案")
    except Exception as e:
        print(f"  douyin-tiktok-scraper 失败: {e}")

    return []


# ─── 方案3: yt-dlp (最后备选) ───


def ytdlp_get_creator_videos(douyin_url: str) -> list[dict]:
    """使用 yt-dlp 获取抖音博主视频列表（不太稳定）"""
    try:
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            "--no-download",
            douyin_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            # 加 cookies 重试
            cmd_with_cookies = cmd[:-1] + ["--cookies-from-browser", "chrome", douyin_url]
            result = subprocess.run(cmd_with_cookies, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            return []

        videos = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    videos.append(data)
                except json.JSONDecodeError:
                    continue
        return _normalize_video_list(videos)
    except FileNotFoundError:
        print("  yt-dlp 未安装，跳过此方案")
    except subprocess.TimeoutExpired:
        print("  yt-dlp 超时")
    except Exception as e:
        print(f"  yt-dlp 失败: {e}")
    return []


# ─── 统一入口 ───


def get_creator_videos(douyin_id: str, max_videos: int = 200, progress_callback=None) -> list[dict]:
    """获取博主视频列表 — 自动尝试多种方案"""

    # 先检查是否有缓存
    cache_path = TRANSCRIPTS_DIR / f"{douyin_id}_videos.json"
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached:
                if progress_callback:
                    progress_callback(1.0, f"从缓存加载了 {len(cached)} 个视频")
                return cached
        except (json.JSONDecodeError, OSError):
            pass

    errors = []

    # 方案1: Apify
    if APIFY_API_TOKEN:
        if progress_callback:
            progress_callback(0.1, "尝试 Apify 抖音 Actor...")
        try:
            videos = apify_get_creator_videos(douyin_id, max_videos)
            if videos:
                if progress_callback:
                    progress_callback(1.0, f"通过 Apify 获取到 {len(videos)} 个视频")
                return videos
        except Exception as e:
            errors.append(f"Apify: {e}")

    # 方案2: PyPI 包
    if progress_callback:
        progress_callback(0.4, "尝试 douyin-tiktok-scraper...")
    try:
        videos = pypi_get_creator_videos(douyin_id, max_videos)
        if videos:
            if progress_callback:
                progress_callback(1.0, f"通过 scraper 获取到 {len(videos)} 个视频")
            return videos
    except Exception as e:
        errors.append(f"scraper: {e}")

    # 方案3: yt-dlp
    if progress_callback:
        progress_callback(0.7, "尝试 yt-dlp...")
    douyin_url = f"https://www.douyin.com/user/{douyin_id}"
    try:
        videos = ytdlp_get_creator_videos(douyin_url)
        if videos:
            if progress_callback:
                progress_callback(1.0, f"通过 yt-dlp 获取到 {len(videos)} 个视频")
            return videos
    except Exception as e:
        errors.append(f"yt-dlp: {e}")

    error_detail = "\n".join(f"  - {e}" for e in errors) if errors else ""
    raise RuntimeError(
        f"所有方案均无法获取抖音号 '{douyin_id}' 的视频。\n"
        "请检查：\n"
        "1. 抖音号是否正确（注意不是昵称，是抖音号）\n"
        "2. APIFY_API_TOKEN 是否已设置\n"
        "3. 是否已安装 douyin-tiktok-scraper (pip install douyin-tiktok-scraper)\n"
        f"\n错误详情:\n{error_detail}"
    )


def download_video_audio(video: dict, index: int) -> Path | None:
    """下载视频并提取音频"""
    url = video.get("share_url") or video.get("url") or video.get("video_url")
    if not url:
        return None

    safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', video.get("title", f"video_{index}"))[:50]
    output_path = AUDIO_DIR / f"{index:04d}_{safe_title}.mp3"

    if output_path.exists():
        return output_path

    temp_pattern = f"{index:04d}_temp"

    try:
        # 先不带 cookies 尝试
        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "-o", str(TEMP_DIR / f"{temp_pattern}.%(ext)s"),
            "--no-playlist",
            "--socket-timeout", "30",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            # 带 cookies 重试
            cmd_retry = cmd[:-1] + ["--cookies-from-browser", "chrome", url]
            result = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            for f in TEMP_DIR.glob(f"{temp_pattern}*"):
                f.rename(output_path)
                return output_path

    except FileNotFoundError:
        print(f"  yt-dlp 未安装，无法下载 [{index}]")
    except subprocess.TimeoutExpired:
        print(f"  下载超时 [{index}]: {video.get('title', '')[:30]}")
        for f in TEMP_DIR.glob(f"{temp_pattern}*"):
            f.unlink(missing_ok=True)
    except Exception as e:
        print(f"  音频下载失败 [{index}]: {e}")

    return None


def download_all_audios(videos: list[dict], progress_callback=None) -> list[dict]:
    """批量下载所有视频的音频"""
    results = []
    total = len(videos)

    for i, video in enumerate(videos):
        if progress_callback:
            progress_callback(
                i / max(total, 1),
                f"下载音频 ({i+1}/{total}): {video.get('title', '')[:30]}",
            )

        audio_path = download_video_audio(video, i)
        results.append({
            **video,
            "audio_path": str(audio_path) if audio_path else None,
            "downloaded": audio_path is not None,
        })

    return results


# ─── 工具函数 ───


def _normalize_video_list(items: list) -> list[dict]:
    """将不同来源的视频数据标准化"""
    videos = []
    seen_ids = set()

    for item in items:
        vid = str(item.get("id", item.get("aweme_id", item.get("video_id", ""))))

        if vid and vid in seen_ids:
            continue
        if vid:
            seen_ids.add(vid)

        video = {
            "id": vid,
            "title": item.get("desc", item.get("title", item.get("description", "无标题"))),
            "url": item.get("video_url", item.get("videoUrl", item.get("url", ""))),
            "share_url": item.get("share_url", item.get("shareUrl", item.get("webpage_url", ""))),
            "create_time": item.get("create_time", item.get("createTime", item.get("timestamp", ""))),
            "duration": item.get("duration", 0),
            "digg_count": item.get("digg_count", item.get("diggCount", item.get("like_count", 0))),
            "author": item.get("author", item.get("nickname", item.get("author_name", ""))),
        }
        videos.append(video)

    videos.sort(key=lambda x: str(x.get("create_time", "")), reverse=True)
    return videos


def save_video_list(videos: list[dict], douyin_id: str) -> Path:
    """保存视频列表到 JSON"""
    output_path = TRANSCRIPTS_DIR / f"{douyin_id}_videos.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    return output_path
