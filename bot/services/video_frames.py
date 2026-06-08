"""Extract key frames from reel/video for AI vision analysis."""

import asyncio
import base64
import logging
import shutil
import subprocess
from pathlib import Path

import aiohttp

from bot.config import settings
from bot.media_variants import MediaVariant, pick_best_download
from bot.services.cdn_download import IG_CDN_HEADERS

logger = logging.getLogger(__name__)

TMP = Path("/tmp/reeldrive/ai_frames")


def ffmpeg_ready() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _video_variant(variants: list[MediaVariant]) -> MediaVariant | None:
    videos = [v for v in variants if v.kind == "video"]
    if videos:
        return pick_best_download(videos) or videos[0]
    for v in variants:
        url = v.url.lower().split("?")[0]
        if url.endswith(".mp4") or url.endswith(".mov"):
            return v
    return None


def _is_video_item(item: dict, variants: list[MediaVariant]) -> bool:
    kind = str(item.get("type") or item.get("productType") or "").lower()
    if "video" in kind or kind == "reels":
        return True
    return _video_variant(variants) is not None


def _probe_duration(path: Path) -> float | None:
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if out.returncode != 0:
            return None
        return float(out.stdout.strip())
    except Exception:
        return None


def _frame_timestamps(duration: float | None) -> list[tuple[str, float]]:
    """Hook-heavy sampling for short-form reels."""
    if duration and duration > 1:
        d = min(duration, float(settings.ai_video_max_duration))
        return [
            ("شروع / Hook (0s)", 0.0),
            ("ثانیه ۱", min(1.0, d * 0.95)),
            ("ثانیه ۲.۵", min(2.5, d * 0.95)),
            ("میانه", d * 0.5),
            ("پایان", max(d * 0.85, 0.0)),
        ]
    return [
        ("شروع / Hook (0s)", 0.0),
        ("ثانیه ۱", 1.0),
        ("ثانیه ۳", 3.0),
    ]


def _extract_frames_sync(video_path: Path, stamps: list[tuple[str, float]]) -> list[tuple[str, Path]]:
    TMP.mkdir(parents=True, exist_ok=True)
    out: list[tuple[str, Path]] = []
    for i, (label, ts) in enumerate(stamps):
        frame_path = TMP / f"{video_path.stem}_f{i}.jpg"
        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{ts:.2f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "3",
                    str(frame_path),
                ],
                capture_output=True,
                timeout=25,
                check=False,
            )
            if proc.returncode == 0 and frame_path.is_file() and frame_path.stat().st_size > 512:
                out.append((label, frame_path))
        except Exception:
            logger.debug("Frame extract failed at %ss", ts)
    return out


def _encode_frame(path: Path) -> tuple[str, str] | None:
    try:
        data = path.read_bytes()
        if len(data) > 750_000:
            return None
        return base64.b64encode(data).decode("ascii"), "image/jpeg"
    except OSError:
        return None


async def _download_video(url: str, dest: Path) -> bool:
    max_bytes = settings.ai_video_max_mb * 1024 * 1024
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=IG_CDN_HEADERS) as resp:
                if not (200 <= resp.status < 300):
                    return False
                data = await resp.read()
                if not data or len(data) > max_bytes:
                    return False
                dest.write_bytes(data)
                return True
    except Exception:
        logger.exception("Video download for AI failed")
        return False


async def extract_vision_frames(
    item: dict,
    variants: list[MediaVariant],
) -> list[tuple[str, str, str]]:
    """
    Return [(label, base64, mime), ...] from reel/video frames.
    Empty if not a video or extraction fails.
    """
    if not settings.ai_video_frames_enabled or not ffmpeg_ready():
        return []

    var = _video_variant(variants)
    if not var and not _is_video_item(item, variants):
        return []

    if not var:
        return []

    TMP.mkdir(parents=True, exist_ok=True)
    video_path = TMP / f"reel_{abs(hash(var.url)) % 10_000_000}.mp4"
    try:
        if not await _download_video(var.url, video_path):
            return []

        duration = await asyncio.to_thread(_probe_duration, video_path)
        stamps = _frame_timestamps(duration)
        labeled = await asyncio.to_thread(_extract_frames_sync, video_path, stamps)

        frames: list[tuple[str, str, str]] = []
        for label, path in labeled:
            encoded = _encode_frame(path)
            if encoded:
                b64, mime = encoded
                frames.append((label, b64, mime))
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        return frames[: settings.ai_video_frame_count]
    finally:
        try:
            video_path.unlink(missing_ok=True)
        except OSError:
            pass
