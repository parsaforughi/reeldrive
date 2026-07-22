"""Extract labeled media URLs and qualities from Instagram media items."""

import re
from dataclasses import dataclass

_RESOLUTION_RE = re.compile(r"[/_]s(\d+)x(\d+)[/_]", re.I)


@dataclass
class MediaVariant:
    label: str
    url: str
    kind: str  # video | image


def _resolution_label(url: str, width: int | None, height: int | None) -> str:
    if width and height:
        return f"{width}×{height}"
    match = _RESOLUTION_RE.search(url)
    if match:
        return f"{match.group(1)}×{match.group(2)}"
    if ".mp4" in url.lower() or "/video/" in url.lower():
        return "ویدیو"
    return "تصویر"


def _is_video_url(url: str) -> bool:
    lower = url.lower().split("?")[0]
    return lower.endswith(".mp4") or lower.endswith(".mov") or "/video/" in lower


def extract_media_variants(item: dict) -> list[MediaVariant]:
    """Collect all distinct media URLs with human-readable labels."""
    found: list[tuple[str, str, str]] = []  # url, kind, label_suffix

    def walk(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            w = obj.get("dimensionsWidth") or obj.get("width")
            h = obj.get("dimensionsHeight") or obj.get("height")
            try:
                wi, hi = int(w) if w else None, int(h) if h else None
            except (TypeError, ValueError):
                wi, hi = None, None

            for key in (
                "videoUrl",
                "video_url",
                "displayUrl",
                "display_url",
                "url",
            ):
                val = obj.get(key)
                if isinstance(val, str) and val.startswith("http"):
                    kind = "video" if _is_video_url(val) or key.startswith("video") else "image"
                    if key.startswith("video"):
                        kind = "video"
                    elif kind == "video" and key == "displayUrl":
                        kind = "image"  # displayUrl on video posts is usually thumbnail
                    label = _resolution_label(val, wi, hi)
                    if key.startswith("video"):
                        label = f"ویدیو {label}" if "×" in label or label == "ویدیو" else f"ویدیو ({label})"
                    elif path == "" and obj.get("type", "").lower() == "video" and kind == "image":
                        label = f"کاور {label}"
                    found.append((val, kind, label))

            for key in ("displayResourceUrls", "images", "imageUrls"):
                val = obj.get(key)
                if isinstance(val, list):
                    for i, entry in enumerate(val):
                        if isinstance(entry, str) and entry.startswith("http"):
                            k = "video" if _is_video_url(entry) else "image"
                            found.append(
                                (entry, k, f"اسلاید {i + 1} — {_resolution_label(entry, None, None)}")
                            )
                        elif isinstance(entry, dict):
                            walk(entry, f"{path}.{key}[{i}]")

            for key in ("childPosts", "sidecarChildren", "carouselMedia"):
                children = obj.get(key)
                if isinstance(children, list):
                    for i, child in enumerate(children):
                        walk(child, f"{path}.{key}[{i}]")

            for k, v in obj.items():
                if k in (
                    "videoUrl",
                    "displayUrl",
                    "displayResourceUrls",
                    "childPosts",
                    "sidecarChildren",
                    "images",
                    "imageUrls",
                    "carouselMedia",
                    "latestPosts",
                    "topPosts",
                ):
                    continue
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}.{k}")

        elif isinstance(obj, list):
            for i, entry in enumerate(obj):
                walk(entry, f"{path}[{i}]")

    walk(item)

    # Deduplicate by URL, keep best label
    by_url: dict[str, MediaVariant] = {}
    for url, kind, label in found:
        if url not in by_url:
            by_url[url] = MediaVariant(label=label, url=url, kind=kind)

    variants = list(by_url.values())
    # Sort: videos first (larger resolution first), then images
    def sort_key(v: MediaVariant) -> tuple:
        is_vid = 0 if v.kind == "video" else 1
        m = _RESOLUTION_RE.search(v.url)
        pixels = int(m.group(1)) * int(m.group(2)) if m else 0
        return (is_vid, -pixels)

    variants.sort(key=sort_key)
    return variants


def pick_best_download(variants: list[MediaVariant]) -> MediaVariant | None:
    videos = [v for v in variants if v.kind == "video"]
    if videos:
        return videos[0]
    if variants:
        return variants[0]
    return None
