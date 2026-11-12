"""Best-effort intrinsic image dimensions for static editorial media.

This module is deliberately offline and side-effect free: it reads local assets or
uses dimensions that are part of the source metadata / a well-known YouTube
thumbnail variant. Unknown remote dimensions stay unknown rather than being
guessed, so the importer and article content are never rewritten.
"""
from pathlib import Path
from urllib.parse import urlparse
import re
import struct


def _positive_pair(width, height):
    try:
        width, height = int(width), int(height)
    except (TypeError, ValueError, OverflowError):
        return None
    if 0 < width <= 30000 and 0 < height <= 30000:
        return width, height
    return None


def _metadata_pair(metadata):
    if not isinstance(metadata, dict):
        return None
    for width_key, height_key in (
        ("image_width", "image_height"),
        ("cover_width", "cover_height"),
        ("width", "height"),
    ):
        pair = _positive_pair(metadata.get(width_key), metadata.get(height_key))
        if pair:
            return pair
    dimensions = metadata.get("image_dimensions")
    if isinstance(dimensions, (list, tuple)) and len(dimensions) >= 2:
        return _positive_pair(dimensions[0], dimensions[1])
    return None


def _jpeg(data):
    if not data.startswith(b"\xff\xd8"):
        return None
    i = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            continue
        if i + 2 > len(data):
            break
        segment_length = int.from_bytes(data[i:i + 2], "big")
        if segment_length < 2 or i + segment_length > len(data):
            break
        if marker in sof and segment_length >= 7:
            height = int.from_bytes(data[i + 3:i + 5], "big")
            width = int.from_bytes(data[i + 5:i + 7], "big")
            return _positive_pair(width, height)
        i += segment_length
    return None


def _svg(data):
    try:
        text = data[:65536].decode("utf-8", "ignore")
    except (AttributeError, UnicodeError):
        return None
    if "<svg" not in text[:2048].lower():
        return None
    tag = re.search(r"<svg\b([^>]*)>", text, re.I | re.S)
    if not tag:
        return None
    attrs = tag.group(1)
    values = {}
    for name in ("width", "height"):
        match = re.search(r"\b" + name + r"\s*=\s*['\"]\s*([0-9.]+)(?:px)?\s*['\"]", attrs, re.I)
        if match:
            values[name] = match.group(1)
    if "width" in values and "height" in values:
        return _positive_pair(values["width"], values["height"])
    view = re.search(r"\bviewBox\s*=\s*['\"]\s*[-0-9.]+[ ,]+[-0-9.]+[ ,]+([0-9.]+)[ ,]+([0-9.]+)", attrs, re.I)
    if view:
        return _positive_pair(view.group(1), view.group(2))
    return None


def parse_image_dimensions(data):
    """Return (width, height) for PNG, JPEG, GIF, WebP or SVG bytes."""
    if not isinstance(data, (bytes, bytearray)):
        return None
    data = bytes(data)
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return _positive_pair(*struct.unpack(">II", data[16:24]))
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        return _positive_pair(*struct.unpack("<HH", data[6:10]))
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP" and len(data) >= 30:
        kind = data[12:16]
        if kind == b"VP8X":
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return _positive_pair(width, height)
        if kind == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
            width = int.from_bytes(data[26:28], "little") & 0x3FFF
            height = int.from_bytes(data[28:30], "little") & 0x3FFF
            return _positive_pair(width, height)
        if kind == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            return _positive_pair((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    jpeg = _jpeg(data)
    if jpeg:
        return jpeg
    return _svg(data)


def image_dimensions(source, root=None, metadata=None):
    """Read dimensions when grounded; return None rather than guessing."""
    pair = _metadata_pair(metadata)
    if pair:
        return pair
    value = str(source or "")
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https"):
        host = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        if host == "i.ytimg.com":
            if path.endswith("/hqdefault.jpg"):
                return 480, 360
            if path.endswith("/maxresdefault.jpg"):
                return 1280, 720
            if path.endswith("/sddefault.jpg"):
                return 640, 480
            if path.endswith("/mqdefault.jpg"):
                return 320, 180
        return None
    if not value.startswith("/") or value.startswith("//") or ".." in value.split("/"):
        return None
    base = Path(root) if root else Path(__file__).resolve().parents[1]
    target = (base / value.lstrip("/")).resolve()
    try:
        target.relative_to(base.resolve())
        if not target.is_file() or target.stat().st_size > 8 * 1024 * 1024:
            return None
        return parse_image_dimensions(target.read_bytes())
    except (OSError, ValueError):
        return None


def dimension_attributes(source, root=None, metadata=None):
    pair = image_dimensions(source, root=root, metadata=metadata)
    if not pair:
        return ""
    return ' width="' + str(pair[0]) + '" height="' + str(pair[1]) + '"'
