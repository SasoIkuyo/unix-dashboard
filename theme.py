"""Paleta del dashboard, sincronizada con el esquema de Caelestia."""

from __future__ import annotations

import json
import pathlib
import time

SCHEME = pathlib.Path.home() / ".local/state/caelestia/scheme.json"

FALLBACK = {
    "background": "212225",
    "onSurface": "CECDD0",
    "onSurfaceVariant": "7C7F86",
    "outline": "7C7F86",
    "outlineVariant": "ABAEB5",
    "surfaceContainerLowest": "191A1C",
    "surfaceContainerLow": "262729",
    "surfaceContainer": "2C2D2F",
    "surfaceContainerHigh": "333436",
    "primary": "B1C8EC",
    "primaryDim": "A3BADE",
    "primaryContainer": "3E5473",
    "onPrimary": "2B415F",
    "secondary": "BFC7D7",
    "tertiary": "FED79B",
    "tertiaryDim": "EECA8E",
    "error": "D18C84",
    "success": "B5CCBA",
    "term2": "00B8CE",
    "term3": "4CD8BA",
}

_cache: dict[str, str] = {}
_cache_mtime: float = -1.0


def _value(colours: dict, key: str) -> str:
    value = colours.get(key) or FALLBACK.get(key) or "CECDD0"
    return "#" + str(value).lstrip("#")


def load() -> dict[str, str]:
    """Devuelve la paleta actual. Se recarga si cambia el esquema en disco."""
    global _cache, _cache_mtime
    try:
        mtime = SCHEME.stat().st_mtime
    except OSError:
        mtime = -1.0

    if _cache and mtime == _cache_mtime:
        return _cache

    try:
        colours = json.loads(SCHEME.read_text())["colours"]
    except (OSError, ValueError, KeyError, TypeError):
        colours = FALLBACK

    p = {key: _value(colours, key) for key in FALLBACK}
    # Aliases cómodos para el resto del código.
    p.update(
        {
            "bg": p["background"],
            "fg": p["onSurface"],
            "dim": p["onSurfaceVariant"],
            "faint": p["outline"],
            "border": p["outline"],
            "panel": p["surfaceContainerLow"],
            "panel_alt": p["surfaceContainerLowest"],
            "track": p["surfaceContainerHigh"],
            "accent": p["primary"],
            "cpu": p["primary"],
            "ram": p["term2"],
            "gpu": p["tertiary"],
            "freq": p["term3"],
            "ok": p["success"],
            "warn": p["tertiary"],
            "bad": p["error"],
        }
    )
    _cache, _cache_mtime = p, mtime
    return p


def rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def mix(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    ra, ga, ba = rgb(a)
    rb, gb, bb = rgb(b)
    return "#%02x%02x%02x" % (
        round(ra + (rb - ra) * t),
        round(ga + (gb - ga) * t),
        round(ba + (bb - ba) * t),
    )


def luma(color: str) -> float:
    r, g, b = rgb(color)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def readable(bg: str, light: str, dark: str) -> str:
    return dark if luma(bg) > 0.55 else light


def ansi_fg(color: str | None) -> str:
    if not color:
        return "\x1b[39m"
    r, g, b = rgb(color)
    return f"\x1b[38;2;{r};{g};{b}m"


def ansi_bg(color: str | None) -> str:
    if not color:
        return "\x1b[49m"
    r, g, b = rgb(color)
    return f"\x1b[48;2;{r};{g};{b}m"


def heat(theme: dict[str, str], minutes: float) -> tuple[str, str]:
    """Color de fondo y de texto para un día del calendario."""
    if minutes <= 0:
        return theme["surfaceContainerHigh"], theme["faint"]
    if minutes < 60:
        bg = theme["surfaceContainerHigh"]
    elif minutes < 180:
        bg = mix(theme["primaryContainer"], theme["primary"], 0.30)
    elif minutes < 360:
        bg = mix(theme["primaryContainer"], theme["primary"], 0.62)
    elif minutes < 540:
        bg = theme["primary"]
    else:
        bg = theme["tertiary"]
    return bg, readable(bg, theme["onSurface"], theme["onPrimary"])


def temp_color(theme: dict[str, str], celsius: float) -> str:
    if celsius < 45:
        return theme["term3"]
    if celsius < 60:
        return theme["primary"]
    if celsius < 72:
        return theme["tertiary"]
    return theme["error"]
