"""Full reel/video analysis: ffmpeg metadata, cuts, audio, vision AI."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import subprocess
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp

from bot.config import settings
from bot.services.analysis_progress import ai_error_key

logger = logging.getLogger(__name__)

TMP = Path("/tmp/reeldrive/analysis")
FRAMES_DIR = TMP / "frames"
MAX_VIDEO_BYTES = 20 * 1024 * 1024  # Telegram bot download limit


def ffmpeg_ready() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _parse_fps(raw: str | None) -> float:
    if not raw:
        return 30.0
    if "/" in raw:
        num, den = raw.split("/", 1)
        try:
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return 30.0
    try:
        return float(raw)
    except ValueError:
        return 30.0


def get_video_info(filepath: str) -> dict[str, Any]:
    """Duration, resolution, fps."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        raise ValueError("ffprobe failed")
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams") or []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise ValueError("No video stream found")
    duration = float(
        video_stream.get("duration")
        or (data.get("format") or {}).get("duration")
        or 0
    )
    return {
        "duration": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": _parse_fps(video_stream.get("r_frame_rate")),
    }


def detect_cuts(filepath: str, threshold: float = 0.15) -> list[float]:
    """Scene-cut timestamps in seconds."""
    cmd = [
        "ffmpeg",
        "-i",
        filepath,
        "-filter:v",
        f"select='gt(scene,{threshold})',showinfo",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    timestamps: list[float] = []
    for line in (result.stdout or "").split("\n"):
        if "pts_time:" in line:
            ts = line.split("pts_time:")[1].split()[0]
            try:
                timestamps.append(float(ts))
            except ValueError:
                pass
    return timestamps


def summarize_cut_phases(cuts: list[float], duration: float) -> str:
    """Summarize cut rhythm for the report."""
    if len(cuts) < 2:
        return "بدون کات قابل توجه — تک شات"

    gaps = [cuts[i + 1] - cuts[i] for i in range(len(cuts) - 1)]
    avg_gap = sum(gaps) / len(gaps)
    fast_cuts = sum(1 for g in gaps if g < 0.5)

    if fast_cuts > len(gaps) * 0.3:
        return (
            f"ترکیبی از شات‌های معمولی و rapid-fire — "
            f"میانگین {avg_gap:.1f} ثانیه بین کات‌ها"
        )
    return f"ریتم یکنواخت — میانگین {avg_gap:.1f} ثانیه بین کات‌ها"


def analyze_audio(filepath: str) -> dict[str, Any]:
    """BPM, speech vs music, energy peaks via librosa."""
    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        raise ValueError("ai_deps_missing") from exc

    audio_path = str(Path(filepath).with_suffix("")) + "_audio.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            filepath,
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "22050",
            "-ac",
            "1",
            audio_path,
            "-y",
        ],
        capture_output=True,
        timeout=60,
        check=False,
    )

    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True)

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo.flat[0]) if isinstance(tempo, np.ndarray) else float(tempo)

        zcr = float(librosa.feature.zero_crossing_rate(y)[0].mean())
        audio_type = "speech" if zcr > 0.08 else "music"

        rms = librosa.feature.rms(y=y)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        threshold = float(rms.mean() + rms.std())
        peak_indices = np.where(rms > threshold)[0]
        energy_peaks: list[float] = []
        prev = -99.0
        for i in peak_indices:
            t = float(times[i])
            if t - prev > 0.5:
                energy_peaks.append(round(t, 2))
            prev = t

        return {
            "bpm": round(bpm, 1),
            "audio_type": audio_type,
            "energy_peaks": energy_peaks[:10],
        }
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


def extract_keyframes(filepath: str, duration: float, count: int = 8) -> list[str]:
    """Extract evenly spaced frames as base64 JPEG strings."""
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for old in FRAMES_DIR.glob("frame_*.jpg"):
        old.unlink(missing_ok=True)

    if duration <= 0:
        duration = 10.0
    interval = duration / count
    timestamps = [round(i * interval, 2) for i in range(count)]

    base64_frames: list[str] = []
    for i, ts in enumerate(timestamps):
        frame_path = FRAMES_DIR / f"frame_{i:02d}.jpg"
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ts:.2f}",
                "-i",
                filepath,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(frame_path),
            ],
            capture_output=True,
            timeout=25,
            check=False,
        )
        if proc.returncode == 0 and frame_path.is_file() and frame_path.stat().st_size > 256:
            with open(frame_path, "rb") as fp:
                base64_frames.append(base64.b64encode(fp.read()).decode())
        frame_path.unlink(missing_ok=True)

    return base64_frames


async def analyze_visual_content(
    frames_base64: list[str],
    technical_data: dict[str, Any],
) -> dict[str, Any]:
    """GPT Vision analysis returning structured JSON."""
    if not settings.openai_api_key.strip():
        raise ValueError("AI not configured")

    prompt_text = f"""تو یک متخصص تحلیل محتوای اینستاگرام و ویدیوگرافی هستی.

من {len(frames_base64)} فریم کلیدی از یک ریل اینستاگرام رو به ترتیب زمانی برات می‌فرستم
(فریم اول = ابتدای ویدیو، فریم آخر = انتهای ویدیو). این فریم‌ها رو مثل اینکه کل ویدیو رو دیدی تحلیل کن.

اطلاعات فنی ویدیو:
- مدت: {technical_data.get('duration', 0)} ثانیه
- تعداد کات: {technical_data.get('cuts_count', 0)}
- BPM موزیک: {technical_data.get('bpm', 'نامشخص')}
- نوع صدا: {technical_data.get('audio_type', 'نامشخص')}

پاسخ رو فقط به فرمت JSON معتبر بده (بدون مارک‌داون، بدون backtick)، دقیقاً با این ساختار و به زبان فارسی:

{{
  "content_type": "نوع محتوا (مثلا Talking Head, Product Showcase, ...)",
  "summary": "خلاصه ۲-۳ جمله‌ای از محتوا",
  "location": "توضیح لوکیشن",
  "visual_style": "استایل بصری، رنگ‌بندی، نور",
  "camera_work": "حرکت دوربین و زوایا",
  "text_overlays": "متن‌های روی ویدیو در صورت وجود",
  "hook_analysis": "تحلیل ۳ ثانیه اول",
  "narrative_structure": "ساختار روایی محتوا",
  "music_content_match": "آیا موزیک با محتوا تطابق داره یا نه و چرا",
  "strengths": ["نقطه قوت ۱", "نقطه قوت ۲", "نقطه قوت ۳"],
  "weaknesses": ["نقطه ضعف ۱", "نقطه ضعف ۲"],
  "next_reel_ideas": ["ایده ۱", "ایده ۲", "ایده ۳"],
  "score": 7,
  "label": "قوی یا متوسط یا ضعیف",
  "score_reason": "دلیل نمره در یک جمله"
}}"""

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text}]
    for b64 in frames_base64:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64}",
                    "detail": "low",
                },
            }
        )

    payload = {
        "model": settings.ai_model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 2000,
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=settings.ai_timeout_seconds)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            settings.ai_chat_completions_url,
            headers=headers,
            json=payload,
        ) as resp:
            body = await resp.json()
            if resp.status != 200:
                err = body.get("error", {})
                msg = err.get("message") if isinstance(err, dict) else str(body)
                logger.error("Vision API HTTP %s: %s", resp.status, msg)
                raise ValueError(ai_error_key(resp.status))
            choices = body.get("choices") or []
            if not choices:
                raise ValueError("Empty AI response")
            text = (choices[0].get("message") or {}).get("content") or ""
            text = text.strip()
            text = re.sub(r"^```json\s*", "", text)
            text = re.sub(r"^```\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            return json.loads(text)


def format_telegram_report(
    technical: dict[str, Any],
    audio: dict[str, Any],
    visual: dict[str, Any],
) -> str:
    """HTML report for Telegram (bot default parse mode)."""
    cuts_per_phase = technical.get("cuts_summary", "")
    strengths = visual.get("strengths") or []
    weaknesses = visual.get("weaknesses") or []
    ideas = visual.get("next_reel_ideas") or []

    audio_type_fa = "گفتار" if audio.get("audio_type") == "speech" else "موزیک"

    report = f"""📊 <b>تحلیل جامع ریل</b>

🎬 <b>مشخصات فنی:</b>
مدت: {technical.get('duration', 0):.0f} ثانیه | {technical.get('cuts_count', 0)} کات
رزولوشن: {technical.get('width')}×{technical.get('height')}

🎵 <b>تحلیل موزیک:</b>
BPM: {audio.get('bpm', '—')} | نوع صدا: {audio_type_fa}
تطابق با محتوا: {visual.get('music_content_match', '—')}

✂️ <b>تحلیل کات‌ها:</b>
{cuts_per_phase}

🎥 <b>تحلیل بصری:</b>
نوع محتوا: {visual.get('content_type', '—')}
خلاصه: {visual.get('summary', '—')}
لوکیشن: {visual.get('location', '—')}
استایل: {visual.get('visual_style', '—')}
دوربین: {visual.get('camera_work', '—')}
هوک ۳ ثانیه اول: {visual.get('hook_analysis', '—')}
ساختار روایی: {visual.get('narrative_structure', '—')}
متن روی ویدیو: {visual.get('text_overlays', '—')}

✅ <b>نقاط قوت:</b>
{chr(10).join('• ' + s for s in strengths) or '—'}

⚠️ <b>نقاط بهبود:</b>
{chr(10).join('• ' + w for w in weaknesses) or '—'}

💡 <b>ایده ریل بعدی:</b>
{chr(10).join(f'{i + 1}. {idea}' for i, idea in enumerate(ideas)) or '—'}

🏆 <b>نمره نهایی: {visual.get('score', '—')}/10 — {visual.get('label', '—')}</b>
{visual.get('score_reason', '')}"""

    return report[:3900]


def _check_file_size(filepath: str) -> None:
    size = os.path.getsize(filepath)
    limit = min(MAX_VIDEO_BYTES, settings.ai_video_max_mb * 1024 * 1024)
    if size > limit:
        raise ValueError("ai_video_too_large")


async def run_full_analysis(
    filepath: str,
    on_status: Callable[[str], Awaitable[None]] | None = None,
) -> str:
    """Run complete pipeline on a local video file; returns HTML report."""
    if not ffmpeg_ready():
        raise ValueError("ffmpeg not available")

    async def _status(stage: str) -> None:
        if on_status:
            await on_status(stage)

    await asyncio.to_thread(_check_file_size, filepath)

    await _status("technical")
    technical = await asyncio.to_thread(get_video_info, filepath)
    cuts = await asyncio.to_thread(detect_cuts, filepath)
    technical["cuts_count"] = len(cuts)
    technical["cuts_summary"] = summarize_cut_phases(cuts, technical["duration"])

    await _status("audio")
    audio = await asyncio.to_thread(analyze_audio, filepath)

    await _status("frames")
    frames = await asyncio.to_thread(
        extract_keyframes,
        filepath,
        technical["duration"],
        settings.ai_video_frame_count or 8,
    )
    if not frames:
        raise ValueError("frame extraction failed")

    await _status("visual")
    merged = {**technical, **audio}
    visual = await analyze_visual_content(frames, merged)

    return format_telegram_report(technical, audio, visual)
