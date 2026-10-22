#!/usr/bin/env python3
"""Guarda y restaura la geometría del tablero flotante.

  layout.py save    guarda tamaño/posición de la ventana actual
  layout.py apply   aplica la geometría guardada al tablero

La posición se guarda relativa al monitor para que siga siendo válida aunque
cambie el origen global de las pantallas.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

CLASS = "unixporn-board"
CONF = pathlib.Path(__file__).with_name("layout.json")
DEFAULT_LEFT = 81
DEFAULT_MARGIN = 31


def hypr(*args: str) -> str:
    try:
        return subprocess.run(
            ["hyprctl", *args], capture_output=True, text=True, timeout=2.0
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def as_json(text: str, fallback):
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return fallback


def board() -> dict | None:
    for window in as_json(hypr("-j", "clients"), []):
        if (window.get("class") == CLASS or window.get("title") == "ARCH // WORKSTATION"):
            return window
    return None


def monitors() -> list[dict]:
    return as_json(hypr("-j", "monitors"), [])


def logical_size(monitor: dict) -> tuple[int, int]:
    width = int(monitor.get("width") or 0)
    height = int(monitor.get("height") or 0)
    if monitor.get("transform") in (1, 3, 5, 7):
        width, height = height, width
    scale = float(monitor.get("scale") or 1)
    if scale > 0:
        width = round(width / scale)
        height = round(height / scale)
    return width, height


def load_layout() -> dict:
    try:
        data = json.loads(CONF.read_text())
    except (OSError, ValueError):
        data = {}
    return data if isinstance(data, dict) else {}


def save() -> int:
    window = board()
    if not window:
        print("No hay ninguna ventana unixporn-board.", file=sys.stderr)
        return 1
    monitor = next(
        (m for m in monitors() if m.get("id") == window.get("monitor")), None
    )
    if not monitor:
        print("No encuentro el monitor del tablero.", file=sys.stderr)
        return 1
    at = window.get("at") or [0, 0]
    size = window.get("size") or [0, 0]
    data = {
        "monitor": monitor.get("name"),
        "x": int(at[0]) - int(monitor.get("x") or 0),
        "y": int(at[1]) - int(monitor.get("y") or 0),
        "width": int(size[0]),
        "height": int(size[1]),
        "floating": True,
    }
    CONF.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(
        f"Guardado: {data['width']}x{data['height']} en "
        f"{data['monitor']} (+{data['x']}+{data['y']})"
    )
    return 0


def target_monitor(name: str | None) -> dict | None:
    for monitor in monitors():
        if name and monitor.get("name") == name:
            return monitor
    return None


def apply(name: str | None) -> int:
    if not board():
        print("No hay ninguna ventana unixporn-board.", file=sys.stderr)
        return 1
    data = load_layout()
    monitor = target_monitor(name) or target_monitor(data.get("monitor"))
    if not monitor:
        mons = monitors()
        if not mons:
            print("Hyprland no informa de ningún monitor.", file=sys.stderr)
            return 1
        monitor = min(mons, key=lambda m: (m.get("x", 0), m.get("y", 0)))

    mon_w, mon_h = logical_size(monitor)
    width = int(data.get("width") or (mon_w - DEFAULT_LEFT - DEFAULT_MARGIN))
    height = int(data.get("height") or (mon_h - DEFAULT_MARGIN * 2))
    width = max(200, min(width, mon_w))
    height = max(150, min(height, mon_h))

    rel_x = int(data.get("x", DEFAULT_LEFT))
    rel_y = int(data.get("y", DEFAULT_MARGIN))
    rel_x = max(0, min(rel_x, mon_w - width))
    rel_y = max(0, min(rel_y, mon_h - height))
    x = int(monitor.get("x") or 0) + rel_x
    y = int(monitor.get("y") or 0) + rel_y

    previous = as_json(hypr("-j", "activewindow"), {})
    previous_address = str(previous.get("address") or "")
    previous_class = str(previous.get("class") or "")

    hypr("dispatch", 'hl.dsp.focus({ window = "title:^(ARCH // WORKSTATION)$" })')
    focused = as_json(hypr("-j", "activewindow"), {})
    if focused.get("class") != CLASS and focused.get("title") != "ARCH // WORKSTATION":
        print("No se pudo enfocar el tablero; no aplico la geometría.", file=sys.stderr)
        return 1
    hypr("dispatch", 'hl.dsp.window.float({ action = "on" })')

    def clear_fullscreen() -> None:
        """Kitty recuerda el estado maximizado entre ejecuciones."""
        current = board()
        state = int((current or {}).get("fullscreen") or 0)
        if state == 1:
            hypr("dispatch", 'hl.dsp.window.fullscreen({ mode = "maximized" })')
            time.sleep(0.12)
        elif state in (2, 3):
            hypr("dispatch", 'hl.dsp.window.fullscreen({ mode = "fullscreen" })')
            time.sleep(0.12)

    clear_fullscreen()

    window = None
    at = [0, 0]
    size = [0, 0]
    for attempt in range(4):
        if attempt:
            hypr("dispatch", 'hl.dsp.focus({ window = "title:^(ARCH // WORKSTATION)$" })')
            clear_fullscreen()
        hypr(
            "dispatch",
            "hl.dsp.window.resize({ x = %d, y = %d, relative = false })"
            % (width, height),
        )
        hypr(
            "dispatch",
            "hl.dsp.window.move({ x = %d, y = %d, relative = false })" % (x, y),
        )
        time.sleep(0.14)
        window = board()
        if not window:
            continue
        at = window.get("at") or [0, 0]
        size = window.get("size") or [0, 0]
        if (
            int(window.get("monitor", -1)) == int(monitor.get("id", -2))
            and abs(int(at[0]) - x) <= 2
            and abs(int(at[1]) - y) <= 2
            and abs(int(size[0]) - width) <= 2
            and abs(int(size[1]) - height) <= 2
            and bool(window.get("floating"))
        ):
            break

    if previous_address and previous_class != CLASS:
        hypr(
            "dispatch",
            'hl.dsp.focus({ window = "address:%s" })' % previous_address,
        )

    if window and (
        int(window.get("monitor", -1)) == int(monitor.get("id", -2))
        and abs(int(at[0]) - x) <= 2
        and abs(int(at[1]) - y) <= 2
        and abs(int(size[0]) - width) <= 2
        and abs(int(size[1]) - height) <= 2
        and bool(window.get("floating"))
    ):
        print(
            f"Tablero flotante: {size[0]}x{size[1]} en "
            f"{monitor.get('name')} ({x},{y})"
        )
        return 0
    print(
        "No se pudo aplicar la geometría: "
        f"size={size} at={at} floating={window.get('floating')}",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "apply"
    name = None
    if "--monitor" in sys.argv:
        index = sys.argv.index("--monitor")
        if index + 1 < len(sys.argv):
            name = sys.argv[index + 1]
    if mode == "save":
        return save()
    if mode == "apply":
        return apply(name)
    print("Uso: layout.py [save|apply] [--monitor DP-5]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
