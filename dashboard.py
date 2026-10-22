#!/usr/bin/env python3
"""Dashboard TUI para la pantalla secundaria.

Paneles:
  · reloj grande + semana (número, días y progreso)
  · anillos de CPU, RAM, GPU y frecuencia media
  · térmicas con mínimo/máximo de la sesión
  · calendario de presencia del mes
  · aplicaciones usadas hoy, con iconos y tiempo

Sin dependencias externas: solo stdlib + ANSI truecolor.
"""

from __future__ import annotations

import argparse
import calendar as pycalendar
import datetime as dt
import json
import math
import os
import pathlib
import re
import select
import shutil
import signal
import sqlite3
import subprocess
import sys
import termios
import time
import tty

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import icons  # noqa: E402
import theme  # noqa: E402

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_CORTOS = ["LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM"]
DIAS_MIN = ["L", "M", "X", "J", "V", "S", "D"]
MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
SPARK = "▁▂▃▄▅▆▇█"
# Cuadrantes 2x2 por celda: bit 0 = arriba-izq, 1 = arriba-der, 2 = abajo-izq, 3 = abajo-der.
QUADRANTS = [
    " ",
    "▘",
    "▝",
    "▀",
    "▖",
    "▌",
    "▞",
    "▛",
    "▗",
    "▚",
    "▐",
    "▜",
    "▄",
    "▙",
    "▟",
    "█",
]
DB_PATH = pathlib.Path.home() / ".local/share/unix-dashboard/usage.db"

DIGITS = {
    "0": ["╭───╮", "│   │", "│   │", "│   │", "│   │", "│   │", "╰───╯"],
    "1": ["  ╷  ", "  │  ", "  │  ", "  │  ", "  │  ", "  │  ", "  ╵  "],
    "2": ["╭───╮", "    │", "    │", "╰───╮", "│    ", "│    ", "╰───╯"],
    "3": ["╭───╮", "    │", "    │", " ───┤", "    │", "    │", "╰───╯"],
    "4": ["╷   ╷", "│   │", "│   │", "╰───┤", "    │", "    │", "    ╵"],
    "5": ["╭────", "│    ", "│    ", "╰───╮", "    │", "    │", "╰───╯"],
    "6": ["╭───╮", "│    ", "│    ", "├───╮", "│   │", "│   │", "╰───╯"],
    "7": ["────╮", "    │", "   ╱ ", "  ╱  ", " ╱   ", "╱    ", "╵    "],
    "8": ["╭───╮", "│   │", "│   │", "├───┤", "│   │", "│   │", "╰───╯"],
    "9": ["╭───╮", "│   │", "│   │", "╰───┤", "    │", "    │", "╰───╯"],
    ":": ["     ", "  █  ", "     ", "     ", "  █  ", "     ", "     "],
}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def fmt_dur(seconds: float, pad: bool = False) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        text = f"{days}d {hours:02d}h {minutes:02d}m"
    elif hours:
        text = f"{hours}h {minutes:02d}m"
    elif minutes:
        text = f"{minutes}m {secs:02d}s"
    else:
        text = f"{secs}s"
    if pad:
        text = text.rjust(9)
    return text


def fmt_gib(kib: float) -> str:
    return f"{kib / 1048576:.1f}"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def fit(text: str, width: int) -> str:
    return icons.truncate(text, max(0, width))


def bar_text(pct: float, width: int, filled: str = "█", empty: str = "░") -> str:
    pct = clamp(pct, 0, 100)
    if width <= 0:
        return ""
    used = round(width * pct / 100)
    return filled * used + empty * (width - used)


def read_text(path: str | pathlib.Path) -> str:
    try:
        return pathlib.Path(path).read_text().strip()
    except OSError:
        return ""


def run(cmd: list[str], timeout: float = 2.0) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------------------
# Canvas de celdas
# ---------------------------------------------------------------------------


class Canvas:
    def __init__(self, width: int, height: int, background: str):
        self.w = width
        self.h = height
        self.ch = [[" "] * width for _ in range(height)]
        self.fg: list[list[str | None]] = [[None] * width for _ in range(height)]
        self.bg: list[list[str | None]] = [[background] * width for _ in range(height)]
        self.bold = [[False] * width for _ in range(height)]

    def put(
        self,
        x: int,
        y: int,
        text: str,
        fg: str | None = None,
        bg: str | None = None,
        bold: bool = False,
    ) -> None:
        if y < 0 or y >= self.h:
            return
        row_ch = self.ch[y]
        row_fg = self.fg[y]
        row_bg = self.bg[y]
        row_bold = self.bold[y]
        for index, char in enumerate(text):
            xx = x + index
            if 0 <= xx < self.w:
                row_ch[xx] = char
                row_fg[xx] = fg
                if bg is not None:
                    row_bg[xx] = bg
                row_bold[xx] = bold

    def fill(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        fg: str | None,
        bg: str | None,
        char: str = " ",
    ) -> None:
        for yy in range(y, y + height):
            if 0 <= yy < self.h:
                self.put(x, yy, char * max(0, width), fg, bg)

    def hline(
        self, x: int, y: int, width: int, fg: str | None, bg: str | None, char: str = "─"
    ) -> None:
        self.put(x, y, char * max(0, width), fg, bg)

    def box(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str,
        th: dict[str, str],
        note: str = "",
        accent: str | None = None,
    ) -> None:
        if width < 4 or height < 2:
            return
        bg = th["panel"]
        border = th["track"]
        accent = accent or th["accent"]
        self.fill(x, y, width, height, th["fg"], bg)
        self.put(x, y, "╭" + "─" * (width - 2) + "╮", border, bg)
        self.put(x, y + height - 1, "╰" + "─" * (width - 2) + "╯", border, bg)
        for yy in range(y + 1, y + height - 1):
            self.put(x, yy, "│", border, bg)
            self.put(x + width - 1, yy, "│", border, bg)
        label = f" {title} "
        self.put(x + 2, y, label, accent, bg, True)
        if note:
            note = f" {note} "
            nx = x + width - 2 - len(note)
            if nx > x + 2 + len(label):
                self.put(nx, y, note, th["dim"], bg)

    def render(self, plain: bool = False) -> str:
        lines: list[str] = []
        for y in range(self.h):
            if plain:
                lines.append("".join(self.ch[y]).rstrip())
                continue
            parts = [f"\x1b[{y + 1};1H"]
            cur_fg: str | None = None
            cur_bg: str | None = None
            cur_bold: bool | None = None
            for x in range(self.w):
                fg = self.fg[y][x]
                bg = self.bg[y][x]
                bold = self.bold[y][x]
                if fg != cur_fg:
                    parts.append(theme.ansi_fg(fg))
                    cur_fg = fg
                if bg != cur_bg:
                    parts.append(theme.ansi_bg(bg))
                    cur_bg = bg
                if bold != cur_bold:
                    parts.append("\x1b[1m" if bold else "\x1b[22m")
                    cur_bold = bold
                parts.append(self.ch[y][x])
            parts.append("\x1b[0m")
            lines.append("".join(parts))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sensores y sistema
# ---------------------------------------------------------------------------


class Sampler:
    def __init__(self) -> None:
        self.cpu_prev = self._cpu_times()
        self.cpu_prev_at = time.monotonic()
        self.cpu_pct = 0.0
        self.cpu_temp_hist: list[float] = []
        self.gpu_temp_hist: list[float] = []
        self.ram_total_kib = 0.0
        self.ram_avail_kib = 0.0
        self.ram_pct = 0.0
        self.freq_avg = 0.0
        self.freq_max = 0.0
        self.load = (0.0, 0.0, 0.0)
        self.uptime = 0.0
        self.host = read_text("/proc/sys/kernel/hostname") or "archlinux"
        self.kernel = os.uname().release
        self.cpu_name = "CPU"
        self.gpu_name = "GPU"
        self.gpu_pct = 0.0
        self.gpu_mem_used = 0.0
        self.gpu_mem_total = 0.0
        self.gpu_temp: float | None = None
        self.therms: list[dict] = []
        self.therm_minmax: dict[str, tuple[float, float]] = {}
        self.therm_defs = self._discover_therms()
        self.gpu_at = 0.0
        self.gpu_ok = True
        self.active_class = ""
        self.active_at = 0.0
        self._read_static()

    # -- cpu / memoria ------------------------------------------------------
    def _cpu_times(self) -> tuple[int, int]:
        try:
            line = pathlib.Path("/proc/stat").read_text().splitlines()[0]
            values = [int(x) for x in line.split()[1:]]
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            return sum(values), idle
        except (OSError, ValueError, IndexError):
            return 0, 0

    def _read_static(self) -> None:
        try:
            for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    self.cpu_name = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
        self.freq_max = self._max_freq()

    def _max_freq(self) -> float:
        values: list[float] = []
        try:
            for path in pathlib.Path("/sys/devices/system/cpu").glob(
                "cpu[0-9]*/cpufreq/cpuinfo_max_freq"
            ):
                try:
                    values.append(float(path.read_text().strip()) / 1_000_000)
                except (OSError, ValueError):
                    pass
        except OSError:
            pass
        return max(values) if values else 0.0

    def _mem(self) -> None:
        info: dict[str, float] = {}
        try:
            for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
                key, _, rest = line.partition(":")
                try:
                    info[key] = float(rest.split()[0])
                except (ValueError, IndexError):
                    pass
        except OSError:
            return
        self.ram_total_kib = info.get("MemTotal", 0)
        self.ram_avail_kib = info.get("MemAvailable", 0)
        if self.ram_total_kib:
            used = self.ram_total_kib - self.ram_avail_kib
            target = used / self.ram_total_kib * 100
            self.ram_pct = self.ram_pct * 0.5 + target * 0.5

    def _freq(self) -> None:
        values: list[float] = []
        try:
            for path in pathlib.Path("/sys/devices/system/cpu").glob(
                "cpu[0-9]*/cpufreq/scaling_cur_freq"
            ):
                try:
                    values.append(float(path.read_text().strip()) / 1_000_000)
                except (OSError, ValueError):
                    pass
        except OSError:
            pass
        if values:
            self.freq_avg = sum(values) / len(values)
        else:
            mhz: list[float] = []
            try:
                for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
                    if line.startswith("cpu MHz"):
                        mhz.append(float(line.split(":", 1)[1]))
            except (OSError, ValueError):
                pass
            self.freq_avg = (sum(mhz) / len(mhz) / 1000) if mhz else 0.0

    # -- térmicas -----------------------------------------------------------
    def _discover_therms(self) -> list[dict]:
        cpu: list[dict] = []
        nvme: list[dict] = []
        igpu: dict | None = None
        try:
            hwmons = sorted(
                pathlib.Path("/sys/class/hwmon").glob("hwmon*"),
                key=lambda p: p.name,
            )
        except OSError:
            return []
        for hw in hwmons:
            name = read_text(hw / "name")
            if name in ("k10temp", "coretemp"):
                for temp in sorted(hw.glob("temp*_input")):
                    label = read_text(temp.with_name(temp.name.replace("_input", "_label")))
                    if name == "k10temp" and label not in ("Tctl", "Tccd1"):
                        continue
                    if name == "coretemp" and not label.startswith(("Package", "Core 0")):
                        continue
                    try:
                        value = float(temp.read_text().strip()) / 1000
                    except (OSError, ValueError):
                        continue
                    if 1 < value < 120:
                        key = "cpu" if label in ("Tctl", "Package id 0") else "ccd"
                        if any(item["key"] == key for item in cpu):
                            continue
                        cpu.append(
                            {
                                "key": key,
                                "group": "CPU",
                                "label": label or name,
                                "path": temp,
                            }
                        )
            elif name == "nvme" and len(nvme) < 2:
                temp = hw / "temp1_input"
                try:
                    value = float(temp.read_text().strip()) / 1000
                except (OSError, ValueError):
                    value = 0
                if value > 0:
                    nvme.append(
                        {
                            "key": f"nvme{len(nvme)}",
                            "group": "DISCO",
                            "label": f"NVMe {len(nvme) + 1}",
                            "path": temp,
                        }
                    )
            elif name == "amdgpu" and igpu is None:
                for temp in sorted(hw.glob("temp*_input")):
                    label = read_text(temp.with_name(temp.name.replace("_input", "_label")))
                    if label in ("edge", "junction") or not label:
                        igpu = {
                            "key": "igpu",
                            "group": "GPU",
                            "label": "iGPU",
                            "path": temp,
                        }
                        break
        definitions = cpu + nvme
        if igpu:
            definitions.append(igpu)
        return definitions

    def _read_therms(self) -> None:
        readings: list[dict] = []
        for definition in self.therm_defs:
            try:
                value = float(pathlib.Path(definition["path"]).read_text().strip()) / 1000
            except (OSError, ValueError):
                continue
            if not (1 < value < 120):
                continue
            key = definition["key"]
            low, high = self.therm_minmax.get(key, (value, value))
            self.therm_minmax[key] = (min(low, value), max(high, value))
            readings.append({**definition, "temp": value})
        if self.gpu_temp:
            key = "gpu"
            low, high = self.therm_minmax.get(key, (self.gpu_temp, self.gpu_temp))
            self.therm_minmax[key] = (min(low, self.gpu_temp), max(high, self.gpu_temp))
            readings.insert(
                0 if not readings else len(readings),
                {
                    "key": "gpu",
                    "group": "GPU",
                    "label": self.gpu_name.replace("NVIDIA GeForce ", ""),
                    "temp": self.gpu_temp,
                },
            )
        self.therms = readings
        cpu_main = next((r["temp"] for r in readings if r["key"] == "cpu"), None)
        if cpu_main is not None:
            self.cpu_temp_hist.append(cpu_main)
            if len(self.cpu_temp_hist) > 240:
                self.cpu_temp_hist.pop(0)
        if self.gpu_temp is not None:
            self.gpu_temp_hist.append(self.gpu_temp)
            if len(self.gpu_temp_hist) > 240:
                self.gpu_temp_hist.pop(0)

    # -- gpu ----------------------------------------------------------------
    def _read_gpu(self) -> None:
        if not self.gpu_ok:
            return
        out = run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            1.5,
        )
        if out:
            try:
                name, util, used, total, temp = [part.strip() for part in out.split(",")]
                self.gpu_name = name
                self.gpu_pct = self.gpu_pct * 0.45 + float(util) * 0.55
                self.gpu_mem_used = float(used)
                self.gpu_mem_total = float(total)
                self.gpu_temp = float(temp)
                self.gpu_ok = True
                return
            except (ValueError, IndexError):
                pass
        # Fallback para iGPU AMD.
        for card in sorted(pathlib.Path("/sys/class/drm").glob("card[0-9]*/device")):
            busy = read_text(card / "gpu_busy_percent")
            if not busy:
                continue
            try:
                self.gpu_pct = self.gpu_pct * 0.45 + float(busy) * 0.55
                self.gpu_mem_used = float(read_text(card / "mem_info_vram_used") or 0)
                self.gpu_mem_total = float(read_text(card / "mem_info_vram_total") or 0)
            except ValueError:
                pass
            self.gpu_name = "AMD iGPU"
            break
        self.gpu_ok = bool(out)

    # -- ventana activa -----------------------------------------------------
    def _read_active(self) -> None:
        out = run(["hyprctl", "-j", "activewindow"], 1.0)
        if not out:
            return
        try:
            window = json.loads(out)
        except ValueError:
            return
        self.active_class = str(window.get("class") or window.get("initialClass") or "")

    # -- ciclo --------------------------------------------------------------
    def update(self) -> None:
        now = time.monotonic()
        total, idle = self._cpu_times()
        dtotal = total - self.cpu_prev[0]
        didle = idle - self.cpu_prev[1]
        if dtotal > 0:
            target = clamp((dtotal - didle) / dtotal * 100, 0, 100)
            self.cpu_pct = self.cpu_pct * 0.45 + target * 0.55
        self.cpu_prev = (total, idle)
        self.cpu_prev_at = now

        self._mem()
        self._freq()
        try:
            self.load = os.getloadavg()
        except OSError:
            pass
        try:
            self.uptime = float(read_text("/proc/uptime").split()[0])
        except (ValueError, IndexError):
            pass

        if now - self.gpu_at >= 2.0:
            self._read_gpu()
            self.gpu_at = now
        self._read_therms()
        if now - self.active_at >= 2.0:
            self._read_active()
            self.active_at = now


# ---------------------------------------------------------------------------
# Base de datos de uso
# ---------------------------------------------------------------------------


class Usage:
    def __init__(self) -> None:
        self.days: dict[str, int] = {}
        self.apps: list[tuple[str, int]] = []
        self.apps_week: list[tuple[str, int]] = []
        self.session_start: dt.datetime | None = None
        self.tracker_last: dt.datetime | None = None
        self.today = ""
        self.last_refresh = 0.0
        self.available = DB_PATH.exists()

    def refresh(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_refresh < 4.0:
            return
        self.last_refresh = now
        self.today = dt.date.today().isoformat()
        if not DB_PATH.exists():
            self.available = False
            return
        self.available = True
        try:
            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=1.5)
        except sqlite3.Error:
            return
        try:
            cutoff = (dt.date.today() - dt.timedelta(days=40)).isoformat()
            for day, seconds in conn.execute(
                "SELECT day, seconds FROM presence WHERE day>=?", (cutoff,)
            ):
                self.days[day] = int(seconds)
            self.apps = [
                (str(cls), int(seconds))
                for cls, seconds in conn.execute(
                    "SELECT cls, seconds FROM apps WHERE day=? ORDER BY seconds DESC LIMIT 40",
                    (self.today,),
                )
                if seconds > 2
            ]
            week_start = (dt.date.today() - dt.timedelta(days=6)).isoformat()
            self.apps_week = [
                (str(cls), int(seconds))
                for cls, seconds in conn.execute(
                    "SELECT cls, SUM(seconds) AS total FROM apps WHERE day>=? "
                    "GROUP BY cls ORDER BY total DESC LIMIT 8",
                    (week_start,),
                )
                if seconds > 2
            ]
            row = conn.execute(
                "SELECT value FROM meta WHERE key='session_start'"
            ).fetchone()
            if row:
                try:
                    self.session_start = dt.datetime.fromisoformat(row[0])
                except ValueError:
                    self.session_start = None
            row = conn.execute(
                "SELECT value FROM meta WHERE key='tracker_last'"
            ).fetchone()
            if row:
                try:
                    self.tracker_last = dt.datetime.fromisoformat(row[0])
                except ValueError:
                    self.tracker_last = None
        except sqlite3.Error:
            pass
        finally:
            conn.close()

    def seconds_for(self, day: dt.date) -> int:
        return self.days.get(day.isoformat(), 0)

    def month_rows(self, first: dt.date, last: dt.date) -> list[tuple[dt.date, int]]:
        rows = []
        cursor = first
        while cursor <= last:
            rows.append((cursor, self.seconds_for(cursor)))
            cursor += dt.timedelta(days=1)
        return rows

    def month_total(self, now: dt.datetime) -> int:
        first = now.date().replace(day=1)
        last = now.date().replace(
            day=pycalendar.monthrange(now.year, now.month)[1]
        )
        return sum(seconds for _, seconds in self.month_rows(first, last))

    def month_active_days(self, now: dt.datetime) -> int:
        first = now.date().replace(day=1)
        last = now.date().replace(
            day=pycalendar.monthrange(now.year, now.month)[1]
        )
        return sum(1 for _, seconds in self.month_rows(first, last) if seconds >= 300)

    def best_day(self, now: dt.datetime) -> tuple[dt.date | None, int]:
        first = now.date().replace(day=1)
        last = now.date().replace(
            day=pycalendar.monthrange(now.year, now.month)[1]
        )
        rows = self.month_rows(first, last)
        if not rows:
            return None, 0
        return max(rows, key=lambda item: item[1])

    def streak(self, now: dt.datetime) -> int:
        count = 0
        cursor = now.date()
        if self.seconds_for(cursor) < 300:
            cursor -= dt.timedelta(days=1)
        while self.seconds_for(cursor) >= 300:
            count += 1
            cursor -= dt.timedelta(days=1)
        return count

    def last_days(self, now: dt.datetime, count: int) -> list[tuple[dt.date, int]]:
        days = [
            now.date() - dt.timedelta(days=offset)
            for offset in range(count - 1, -1, -1)
        ]
        return [(day, self.seconds_for(day)) for day in days]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class Dashboard:
    def __init__(self, width: int, height: int) -> None:
        self.w = width
        self.h = height
        self.sampler = Sampler()
        self.usage = Usage()
        self.sampler.update()
        time.sleep(0.18)
        self.sampler.update()
        self.usage.refresh(force=True)
        self.live = True

    # -- helpers de dibujo --------------------------------------------------
    def panel(self, c: Canvas, x: int, y: int, w: int, h: int, title: str, th, note=""):
        c.box(x, y, w, h, title, th, note)

    def kv(
        self,
        c: Canvas,
        x: int,
        y: int,
        width: int,
        label: str,
        value: str,
        th: dict[str, str],
        color: str | None = None,
    ) -> None:
        c.put(x, y, fit(label, width - len(value) - 2), th["dim"], th["panel"])
        vx = x + width - len(value)
        c.put(vx, y, value, color or th["fg"], th["panel"], True)

    def bar(
        self,
        c: Canvas,
        x: int,
        y: int,
        width: int,
        pct: float,
        th: dict[str, str],
        color: str,
        bg: str | None = None,
        empty_color: str | None = None,
    ) -> None:
        bg = bg or th["panel"]
        used = int(round(width * clamp(pct, 0, 100) / 100))
        c.put(x, y, "█" * used, color, bg)
        c.put(x + used, y, "░" * (width - used), empty_color or th["track"], bg)

    # -- cabecera / pie -----------------------------------------------------
    def header(self, c: Canvas, th, now: dt.datetime) -> None:
        brand = "\uf303  ARCH // WORKSTATION"
        c.put(1, 0, brand, th["accent"], None, True)
        middle = f"{self.sampler.host}  ·  kernel {self.sampler.kernel}"
        mx = max(len(brand) + 4, (self.w - len(middle)) // 2)
        c.put(mx, 0, middle, th["dim"], None)
        state = "● LIVE" if self.live else "○ OFFLINE"
        right = f"{state}   {now:%H:%M:%S}"
        c.put(max(0, self.w - len(right) - 1), 0, right, th["ok"], None, True)
        c.put(0, 1, "─" * self.w, th["track"], None)
        c.put(1, 1, "─" * (len(brand) + 2), th["accent"], None)

    def footer(self, c: Canvas, th, now: dt.datetime) -> None:
        y = self.h - 1
        c.put(1, y, " q salir   r refrescar ", th["dim"], None)
        beat = self.usage.tracker_last
        alive = bool(beat and (now - beat).total_seconds() < 20)
        tracker = "● tracker activo" if alive else "○ tracker parado"
        c.put(
            max(0, self.w // 2 - len(tracker) // 2),
            y,
            tracker,
            th["ok"] if alive else th["warn"],
            None,
        )
        right = f"actualizado {now:%H:%M:%S} "
        c.put(max(0, self.w - len(right) - 1), y, right, th["faint"], None)

    # -- reloj --------------------------------------------------------------
    def clock(self, c: Canvas, x: int, y: int, w: int, h: int, th, now: dt.datetime):
        self.panel(c, x, y, w, h, "RELOJ", th, now.strftime("%Z"))
        text = now.strftime("%H:%M")
        glyphs = [DIGITS[ch] for ch in text]
        widths = [len(g[0]) for g in glyphs]
        total_w = sum(widths) + (len(glyphs) - 1)
        cx = x + max(2, (w - total_w) // 2)
        top = y + max(1, (h - 9) // 2)
        for row in range(7):
            gx = cx
            for index, glyph in enumerate(glyphs):
                char = text[index]
                color = th["accent"] if char == ":" else th["fg"]
                c.put(gx, top + row, glyph[row], color, th["panel"], True)
                gx += widths[index] + 1
        date_text = f"{DIAS[now.weekday()].upper()} · {now.day} {MESES[now.month - 1].upper()} {now.year}"
        c.put(
            x + max(2, (w - len(date_text)) // 2),
            top + 8,
            date_text,
            th["dim"],
            th["panel"],
        )
        sec = f":{now.second:02d}"
        if w > total_w + 12:
            c.put(cx + total_w + 3, top + 5, sec, th["accent"], th["panel"], True)

    # -- semana -------------------------------------------------------------
    def week(self, c: Canvas, x: int, y: int, w: int, h: int, th, now: dt.datetime):
        iso = now.isocalendar()
        self.panel(c, x, y, w, h, "SEMANA", th, "ISO")
        monday = now.date() - dt.timedelta(days=now.weekday())
        week_start = dt.datetime.combine(monday, dt.time.min)
        week_pct = (now - week_start).total_seconds() / (7 * 86400) * 100
        year_pct = (
            (now - dt.datetime(now.year, 1, 1)).total_seconds()
            / (dt.datetime(now.year + 1, 1, 1) - dt.datetime(now.year, 1, 1)).total_seconds()
            * 100
        )
        content_y = y + 1
        c.put(x + 2, content_y, f"SEMANA {iso.week} / 52", th["accent"], th["panel"], True)
        pct_text = f"{week_pct:4.1f}%"
        c.put(x + w - 2 - len(pct_text), content_y, pct_text, th["dim"], th["panel"])

        slot = max(7, (w - 4) // 7)
        names_y = content_y + 2
        nums_y = content_y + 3
        start_x = x + 2 + max(0, (w - 4 - slot * 7) // 2)
        today = now.date()
        for index in range(7):
            day = monday + dt.timedelta(days=index)
            sx = start_x + index * slot
            is_today = day == today
            future = day > today
            name = DIAS_CORTOS[index]
            c.put(
                sx + max(0, (slot - len(name)) // 2),
                names_y,
                name,
                th["accent"] if is_today else th["faint"],
                th["panel"],
                is_today,
            )
            size = min(6, slot - 1)
            num = f"{day.day:2d}"
            minutes = self.usage.seconds_for(day) / 60
            if is_today:
                bg, fg = th["accent"], th["onPrimary"]
            elif future:
                bg, fg = th["panel"], th["faint"]
            else:
                bg, fg = theme.heat(th, minutes)
            cell = num.center(size)
            c.put(sx + max(0, (slot - size) // 2), nums_y, cell, fg, bg, is_today)

        bar_y = nums_y + 2
        bar_w = max(10, w - 6)
        self.bar(c, x + 2, bar_y, bar_w, week_pct, th, th["accent"])
        line = f"día {now.weekday() + 1} de 7 · quedan {6 - now.weekday()} días"
        c.put(x + 2, bar_y + 1, line, th["dim"], th["panel"])
        c.put(
            x + 2,
            bar_y + 2,
            f"{year_pct:.1f}% del año transcurrido",
            th["faint"],
            th["panel"],
        )

    # -- uptime / presencia -------------------------------------------------
    def uptime(self, c: Canvas, x: int, y: int, w: int, h: int, th, now: dt.datetime):
        self.panel(c, x, y, w, h, "UPTIME · PRESENCIA", th)
        cy = y + 1
        day = now.date()
        month_first = day.replace(day=1)
        month_days = pycalendar.monthrange(now.year, now.month)[1]
        month_last = day.replace(day=month_days)
        month_total = self.usage.month_total(now)
        active_days = self.usage.month_active_days(now)
        avg = month_total / active_days if active_days else 0
        streak = self.usage.streak(now)
        today_seconds = self.usage.seconds_for(day)
        session_seconds = 0
        if self.usage.session_start:
            session_seconds = (now - self.usage.session_start).total_seconds()

        self.kv(c, x + 2, cy, w - 4, "sistema encendido", fmt_dur(self.sampler.uptime), th)
        self.kv(c, x + 2, cy + 1, w - 4, "sesión actual", fmt_dur(session_seconds), th)
        self.kv(c, x + 2, cy + 3, w - 4, "hoy", fmt_dur(today_seconds), th, th["accent"])
        self.kv(
            c,
            x + 2,
            cy + 4,
            w - 4,
            f"este mes ({active_days} días)",
            fmt_dur(month_total),
            th,
            th["tertiary"],
        )
        self.kv(c, x + 2, cy + 5, w - 4, "media por día", fmt_dur(avg), th)
        self.kv(c, x + 2, cy + 6, w - 4, "racha", f"{streak} días", th, th["ok"])

        divider_y = cy + 8
        c.put(x + 2, divider_y, "╌" * (w - 4), th["track"], th["panel"])
        c.put(x + 2, divider_y + 1, "ÚLTIMOS 7 DÍAS", th["accent"], th["panel"], True)
        rows = self.usage.last_days(now, 7)
        max_seconds = max((seconds for _, seconds in rows), default=1) or 1
        row_y = divider_y + 2
        bar_x = x + 12
        bar_w = max(8, w - bar_x + x - 12)
        for index, (d, seconds) in enumerate(rows):
            label = DIAS_CORTOS[d.weekday()]
            color = th["accent"] if d == day else th["dim"]
            c.put(x + 2, row_y + index, f"{label} {d.day:02d}", color, th["panel"])
            self.bar(
                c,
                bar_x,
                row_y + index,
                bar_w,
                seconds / max_seconds * 100,
                th,
                th["ram"] if d != day else th["accent"],
            )
            duration = fmt_dur(seconds)
            c.put(
                x + w - 2 - len(duration),
                row_y + index,
                duration,
                th["fg"] if d == day else th["dim"],
                th["panel"],
                d == day,
            )

        spark_y = row_y + 7 + 1
        if spark_y + 2 < y + h:
            c.put(x + 2, spark_y, "30 DÍAS", th["faint"], th["panel"])
            values = [seconds for _, seconds in self.usage.last_days(now, 30)]
            peak = max(values) or 1
            spark = "".join(
                SPARK[min(len(SPARK) - 1, int(math.sqrt(value / peak) * (len(SPARK) - 1)))]
                for value in values
            )
            c.put(x + 11, spark_y, spark, th["ram"], th["panel"])
            c.put(
                x + 2,
                spark_y + 1,
                f"máx {fmt_dur(peak)} · media {fmt_dur(sum(values) / max(1, len(values)))}",
                th["faint"],
                th["panel"],
            )

        info_y = y + h - 3
        if info_y > spark_y + 2:
            c.put(x + 2, info_y, f"{self.sampler.host} · wayland", th["faint"], th["panel"])
            c.put(
                x + 2,
                info_y + 1,
                f"{self.sampler.cpu_name} · {self.sampler.ram_total_kib / 1048576:.0f} GiB",
                th["faint"],
                th["panel"],
            )

    # -- anillos ------------------------------------------------------------
    def ring(
        self,
        c: Canvas,
        x: int,
        y: int,
        w: int,
        h: int,
        pct: float,
        color: str,
        th,
        value: str,
        sub: str,
    ) -> None:
        """Anillo con subpíxeles 2x2 (cuadrantes) para un círculo suave."""
        pct = clamp(pct, 0, 100) / 100
        aspect = 2.16
        radius = min(w, h * aspect) - 0.8
        thickness = max(2.0, radius * 0.16)
        for gy in range(h):
            for gx in range(w):
                fill_bits = 0
                track_bits = 0
                for bit, (ox, oy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
                    px = (gx * 2 + ox + 0.5) - w
                    py = ((gy * 2 + oy + 0.5) - h) * aspect
                    distance = math.hypot(px, py)
                    if radius - thickness <= distance <= radius:
                        angle = math.degrees(math.atan2(py, px))
                        delta = (angle + 90) % 360
                        if delta <= pct * 360:
                            fill_bits |= 1 << bit
                        else:
                            track_bits |= 1 << bit
                if not fill_bits and not track_bits:
                    continue
                if fill_bits:
                    char = QUADRANTS[fill_bits | track_bits]
                    fg = color
                else:
                    char = QUADRANTS[track_bits]
                    fg = th["track"]
                c.put(x + gx, y + gy, char, fg, th["panel"])

        center_y = y + h // 2
        if value:
            c.put(
                x + max(0, (w - len(value)) // 2),
                center_y - 1,
                value,
                th["fg"],
                th["panel"],
                True,
            )
        if sub:
            c.put(
                x + max(0, (w - len(sub)) // 2),
                center_y + 1,
                sub,
                th["dim"],
                th["panel"],
            )

    def gauges(self, c: Canvas, x: int, y: int, w: int, h: int, th):
        self.panel(c, x, y, w, h, "RECURSOS", th, "live")
        content_x = x + 2
        content_y = y + 1
        content_w = w - 4
        content_h = h - 2
        tile_w = content_w // 2
        tile_h = content_h // 2
        ram_used = self.sampler.ram_total_kib - self.sampler.ram_avail_kib
        gpu_mem = (
            f"{self.sampler.gpu_mem_used / 1024:.1f}/{self.sampler.gpu_mem_total / 1024:.1f}G"
            if self.sampler.gpu_mem_total
            else "VRAM n/d"
        )
        freq_pct = (
            self.sampler.freq_avg / self.sampler.freq_max * 100
            if self.sampler.freq_max
            else 0
        )
        gauges = [
            {
                "label": "CPU",
                "value": f"{self.sampler.cpu_pct:.0f}%",
                "sub": f"{os.cpu_count()} hilos",
                "pct": self.sampler.cpu_pct,
                "color": th["cpu"],
                "note": f"{self.sampler.cpu_name.split(' ')[0]} · {self.sampler.load[0]:.1f} load",
            },
            {
                "label": "MEMORIA",
                "value": f"{self.sampler.ram_pct:.0f}%",
                "sub": f"{ram_used / 1048576:.1f}/{self.sampler.ram_total_kib / 1048576:.0f}G",
                "pct": self.sampler.ram_pct,
                "color": th["ram"],
                "note": f"{ram_used / 1048576:.1f} GiB en uso",
            },
            {
                "label": "GPU",
                "value": f"{self.sampler.gpu_pct:.0f}%",
                "sub": gpu_mem,
                "pct": self.sampler.gpu_pct,
                "color": th["gpu"],
                "note": self.sampler.gpu_name.replace("NVIDIA GeForce ", ""),
            },
            {
                "label": "FREC. MEDIA",
                "value": f"{self.sampler.freq_avg:.2f}",
                "sub": "GHz",
                "pct": freq_pct,
                "color": th["freq"],
                "note": f"AVG · máx {self.sampler.freq_max:.2f} GHz",
            },
        ]
        for index, gauge in enumerate(gauges):
            col = index % 2
            row = index // 2
            tx = content_x + col * tile_w
            ty = content_y + row * tile_h
            diameter = min(tile_w - 6, (tile_h - 4) * 2)
            diameter = max(8, diameter - diameter % 2)
            ring_h = diameter // 2
            ring_x = tx + (tile_w - diameter) // 2
            ring_y = ty + 1
            self.ring(
                c,
                ring_x,
                ring_y,
                diameter,
                ring_h,
                gauge["pct"],
                gauge["color"],
                th,
                gauge["value"],
                gauge["sub"],
            )
            label = gauge["label"]
            c.put(
                tx + max(0, (tile_w - len(label)) // 2),
                ring_y + ring_h + 1,
                label,
                gauge["color"],
                th["panel"],
                True,
            )
            note = fit(gauge["note"], tile_w - 2)
            c.put(
                tx + max(0, (tile_w - len(note)) // 2),
                ring_y + ring_h + 2,
                note,
                th["faint"],
                th["panel"],
            )

    # -- térmicas -----------------------------------------------------------
    def thermals(self, c: Canvas, x: int, y: int, w: int, h: int, th):
        self.panel(c, x, y, w, h, "TÉRMICAS", th, "mín / máx de la sesión")
        cy = y + 1
        header_fg = th["faint"]
        c.put(x + 2, cy, "ZONA", header_fg, th["panel"])
        c.put(x + 8, cy, "SENSOR", header_fg, th["panel"])
        c.put(x + 19, cy, "ACT", header_fg, th["panel"])
        c.put(x + w - 14, cy, "MÍN", header_fg, th["panel"])
        c.put(x + w - 7, cy, "MÁX", header_fg, th["panel"])
        cy += 1

        def sort_key(item):
            order = {"CPU": 0, "GPU": 1, "DISCO": 2}
            return (order.get(item["group"], 3), item["key"])

        for row in sorted(self.sampler.therms, key=sort_key)[:7]:
            key = row["key"]
            low, high = self.sampler.therm_minmax.get(key, (row["temp"], row["temp"]))
            color = theme.temp_color(th, row["temp"])
            c.put(x + 2, cy, fit(row["group"], 5), th["dim"], th["panel"])
            c.put(x + 8, cy, fit(row["label"], 10), th["fg"], th["panel"])
            temp = f"{row['temp']:.1f}°"
            c.put(x + 19, cy, temp, color, th["panel"], True)
            bar_x = x + 25
            bar_w = max(6, x + w - 14 - 2 - bar_x)
            pct = clamp((row["temp"] - 20) / (95 - 20) * 100, 0, 100)
            self.bar(c, bar_x, cy, bar_w, pct, th, color)
            low_text = f"{low:.1f}°"
            high_text = f"{high:.1f}°"
            c.put(x + w - 14, cy, low_text, th["faint"], th["panel"])
            c.put(x + w - 7, cy, high_text, th["faint"], th["panel"])
            cy += 1

        if not self.sampler.therms:
            c.put(x + 2, cy, "sin sensores disponibles", th["faint"], th["panel"])
            cy += 1

        all_low = min((pair[0] for pair in self.sampler.therm_minmax.values()), default=0)
        all_high = max((pair[1] for pair in self.sampler.therm_minmax.values()), default=0)
        summary_y = min(cy + 1, y + h - 4)
        c.put(x + 2, summary_y, "SESIÓN", th["faint"], th["panel"])
        c.put(
            x + 10,
            summary_y,
            f"mín {all_low:.1f}°C",
            th["term3"] if "term3" in th else th["ok"],
            th["panel"],
            True,
        )
        c.put(x + 24, summary_y, f"máx {all_high:.1f}°C", th["tertiary"], th["panel"], True)

        # En pantallas verticales hay espacio para un gráfico de área real.
        if h >= 32 and w >= 42 and self.sampler.cpu_temp_hist:
            chart_x = x + 11
            chart_w = max(10, w - 14)
            cpu_y = summary_y + 2
            cpu_h = 14 if h >= 40 else 10
            gpu_h = 8 if h >= 40 else 6
            cpu_hist = self.sampler.cpu_temp_hist[-180:]
            cpu_low, cpu_high = self.chart_bounds(cpu_hist)
            c.put(x + 2, cpu_y, "CPU 3m", th["faint"], th["panel"])
            c.put(
                x + w - 2 - len(f"{self.sampler.cpu_temp_hist[-1]:.0f}°"),
                cpu_y,
                f"{self.sampler.cpu_temp_hist[-1]:.0f}°",
                th["cpu"],
                th["panel"],
                True,
            )
            self.area_chart(
                c,
                chart_x,
                cpu_y + 1,
                chart_w,
                cpu_h,
                cpu_hist,
                th["cpu"],
                th,
                low=cpu_low,
                high=cpu_high,
            )
            c.put(x + 2, cpu_y + 1, f"{cpu_high:.0f}°", th["faint"], th["panel"])
            c.put(x + 2, cpu_y + cpu_h, f"{cpu_low:.0f}°", th["faint"], th["panel"])
            gpu_y = cpu_y + cpu_h + 3
            if gpu_y + gpu_h + 1 < y + h:
                if self.sampler.gpu_temp is not None:
                    gpu_hist = self.sampler.gpu_temp_hist[-180:]
                    gpu_low, gpu_high = self.chart_bounds(gpu_hist)
                    c.put(x + 2, gpu_y, "GPU 3m", th["faint"], th["panel"])
                    c.put(
                        x + w - 2 - len(f"{self.sampler.gpu_temp:.0f}°"),
                        gpu_y,
                        f"{self.sampler.gpu_temp:.0f}°",
                        th["gpu"],
                        th["panel"],
                        True,
                    )
                    self.area_chart(
                        c,
                        chart_x,
                        gpu_y + 1,
                        chart_w,
                        gpu_h,
                        gpu_hist,
                        th["gpu"],
                        th,
                        low=gpu_low,
                        high=gpu_high,
                    )
                    c.put(x + 2, gpu_y + 1, f"{gpu_high:.0f}°", th["faint"], th["panel"])
                    c.put(x + 2, gpu_y + gpu_h, f"{gpu_low:.0f}°", th["faint"], th["panel"])
        elif h >= 12 and self.sampler.cpu_temp_hist:
            spark_y = summary_y + 2
            if spark_y < y + h - 1:
                c.put(x + 2, spark_y, "Tctl 3m", th["faint"], th["panel"])
                values = self.sampler.cpu_temp_hist[-max(20, w - 16) :]
                spark = self.sparkline(values, 30, 90, len(values))
                c.put(x + 11, spark_y, spark, th["cpu"], th["panel"])

    def chart_bounds(
        self, values: list[float], pad: float = 1.0, min_span: float = 6.0
    ) -> tuple[float, float]:
        """Ventana vertical centrada en los datos, sin amplificar el ruido."""
        if not values:
            return 30.0, 90.0
        low, high = min(values), max(values)
        span = max(min_span, high - low + pad * 2)
        middle = (low + high) / 2
        return middle - span / 2, middle + span / 2

    def area_chart(
        self,
        c: Canvas,
        x: int,
        y: int,
        w: int,
        h: int,
        values: list[float],
        color: str,
        th,
        low: float = 30,
        high: float = 90,
    ) -> None:
        if not values or w <= 0 or h <= 0:
            return
        # Relleno atenuado en degradado + borde superior brillante.
        shades = [
            theme.mix(color, th["panel"], 0.62 + 0.26 * (index / max(1, h - 1)))
            for index in range(h)
        ]
        # Marco tenue + rejilla para que el área se lea como gráfico.
        for row in range(y, y + h):
            c.put(x - 1, row, "│", th["track"], th["panel"])
        c.put(x - 1, y + h, "╰" + "─" * w, th["track"], th["panel"])
        for fraction in (0.25, 0.5, 0.75):
            grid_y = y + h - 1 - int((h - 1) * fraction)
            c.put(x, grid_y, "╌" * w, th["track"], th["panel"])

        count = len(values)
        levels = h * 8
        for col in range(w):
            index = min(count - 1, int(col * count / w))
            value = clamp((values[index] - low) / (high - low), 0, 1)
            level = int(value * levels)
            full, part = divmod(level, 8)
            base = y + h - 1
            for row in range(min(full, h)):
                shade = shades[min(h - 1, h - 1 - row)]
                c.put(x + col, base - row, "█", shade, th["panel"])
            if part and full < h:
                c.put(x + col, base - full, SPARK[part - 1], color, th["panel"])
            elif full:
                c.put(x + col, base - full + 1, "▔", color, th["panel"], True)

    def sparkline(self, values: list[float], low: float, high: float, width: int) -> str:
        if not values:
            return ""
        count = len(values)
        chars = []
        for index in range(width):
            value = values[min(count - 1, int(index * count / width))]
            level = int(clamp((value - low) / (high - low), 0, 1) * (len(SPARK) - 1))
            chars.append(SPARK[level])
        return "".join(chars)

    # -- calendario ---------------------------------------------------------
    def calendar(self, c: Canvas, x: int, y: int, w: int, h: int, th, now: dt.datetime):
        month_name = f"{MESES[now.month - 1].upper()} {now.year}"
        self.panel(c, x, y, w, h, "ACTIVIDAD", th, "MES ACTUAL")
        cy = y + 1
        c.put(x + 2, cy, f"{MESES[now.month - 1].capitalize()} {now.year}", th["accent"], th["panel"], True)
        month_total = self.usage.month_total(now)
        total_text = fmt_dur(month_total)
        c.put(x + w - 2 - len(total_text), cy, total_text, th["fg"], th["panel"], True)

        cell_w = 6
        gap = 2
        grid_w = 7 * cell_w + 6 * gap
        grid_x = x + 2
        grid_y = cy + 2
        first = now.date().replace(day=1)
        days_in_month = pycalendar.monthrange(now.year, now.month)[1]
        offset = first.weekday()

        for index in range(7):
            c.put(
                grid_x + index * (cell_w + gap) + (cell_w - 1) // 2,
                grid_y,
                DIAS_MIN[index],
                th["faint"],
                th["panel"],
                True,
            )

        for day_num in range(1, days_in_month + 1):
            cell_index = offset + day_num - 1
            row, col = divmod(cell_index, 7)
            cell_x = grid_x + col * (cell_w + gap)
            cell_y = grid_y + 1 + row * 3
            date = first.replace(day=day_num)
            seconds = self.usage.seconds_for(date)
            is_today = date == now.date()
            future = date > now.date()
            if is_today:
                bg, fg = th["accent"], th["onPrimary"]
            elif future or seconds <= 0:
                # Sin datos: no se pinta cuadro, solo el número atenuado.
                bg, fg = None, th["faint"]
            else:
                bg, fg = theme.heat(th, seconds / 60)
            if bg:
                c.fill(cell_x, cell_y, cell_w, 2, fg, bg)
            c.put(
                cell_x + max(0, (cell_w - 2) // 2),
                cell_y + 1,
                f"{day_num:2d}",
                fg,
                bg,
                is_today,
            )

        # Panel lateral de estadísticas.
        side_x = grid_x + grid_w + 3
        side_w = x + w - 2 - side_x
        if side_w >= 22:
            sy = cy + 2
            c.put(side_x, sy, "ESTE MES", th["faint"], th["panel"], True)
            c.put(side_x, sy + 1, fmt_dur(month_total), th["accent"], th["panel"], True)
            active = self.usage.month_active_days(now)
            avg = month_total / active if active else 0
            best_day, best_seconds = self.usage.best_day(now)
            self.kv(c, side_x, sy + 3, side_w, "días activos", str(active), th)
            self.kv(c, side_x, sy + 4, side_w, "media/día", fmt_dur(avg), th)
            self.kv(c, side_x, sy + 5, side_w, "racha", f"{self.usage.streak(now)}d", th, th["ok"])
            if best_day:
                self.kv(
                    c,
                    side_x,
                    sy + 6,
                    side_w,
                    f"mejor ({best_day.day})",
                    fmt_dur(best_seconds),
                    th,
                    th["tertiary"],
                )
            self.kv(
                c,
                side_x,
                sy + 8,
                side_w,
                "hoy",
                fmt_dur(self.usage.seconds_for(now.date())),
                th,
                th["accent"],
            )
            # Progreso del mes.
            month_pct = now.day / days_in_month * 100
            self.bar(c, side_x, sy + 10, side_w, month_pct, th, th["dim"], empty_color=th["track"])
            c.put(side_x, sy + 11, f"día {now.day} de {days_in_month}", th["faint"], th["panel"])
            # Leyenda.
            legend_y = sy + 13
            c.put(side_x, legend_y, "menos", th["faint"], th["panel"])
            levels = [th["track"], theme.mix(th["primaryContainer"], th["primary"], 0.4), th["primary"], th["tertiary"]]
            for idx, color in enumerate(levels):
                c.put(side_x + 7 + idx * 2, legend_y, "■", color, th["panel"])
            c.put(side_x + 15, legend_y, "más", th["faint"], th["panel"])
            c.put(side_x, legend_y + 1, "hoy = acento", th["faint"], th["panel"])
        else:
            week_rows = (offset + days_in_month + 6) // 7
            legend_y = grid_y + 1 + week_rows * 3 + 1
            c.put(
                grid_x,
                legend_y,
                fit("menos ░▒▓█ más · hoy = acento · vacío = sin datos", grid_w),
                th["faint"],
                th["panel"],
            )
            active = self.usage.month_active_days(now)
            avg = month_total / active if active else 0
            best_day, best_seconds = self.usage.best_day(now)
            best_text = (
                f"mejor {best_day.day} ({fmt_dur(best_seconds)})" if best_day else "mejor —"
            )
            stats_y = legend_y + 1
            c.put(
                grid_x,
                stats_y,
                fit(f"{fmt_dur(month_total)} este mes · {active} días activos", grid_w),
                th["fg"],
                th["panel"],
            )
            c.put(
                grid_x,
                stats_y + 1,
                fit(f"media {fmt_dur(avg)} · racha {self.usage.streak(now)} días", grid_w),
                th["dim"],
                th["panel"],
            )
            c.put(
                grid_x,
                stats_y + 2,
                fit(f"hoy {fmt_dur(self.usage.seconds_for(now.date()))} · {best_text}", grid_w),
                th["dim"],
                th["panel"],
            )
            if stats_y + 4 < y + h:
                month_pct = now.day / days_in_month * 100
                self.bar(c, grid_x, stats_y + 4, grid_w, month_pct, th, th["dim"])
                c.put(
                    grid_x,
                    stats_y + 5,
                    f"día {now.day} de {days_in_month}",
                    th["faint"],
                    th["panel"],
                )

    # -- aplicaciones -------------------------------------------------------
    def apps(self, c: Canvas, x: int, y: int, w: int, h: int, th, now: dt.datetime):
        registered = sum(seconds for _, seconds in self.usage.apps)
        self.panel(c, x, y, w, h, "APLICACIONES · HOY", th, fmt_dur(registered))
        cy = y + 1
        session = "sin sesión"
        if self.usage.session_start:
            session = fmt_dur((now - self.usage.session_start).total_seconds())
        subtitle = f"tiempo de uso por ventana · sesión {session}"
        c.put(x + 2, cy, fit(subtitle, w - 4), th["faint"], th["panel"])
        cy += 1

        if not self.usage.available or not self.usage.apps:
            c.put(x + 2, cy + 1, "Aún no hay datos de uso.", th["dim"], th["panel"])
            c.put(x + 2, cy + 2, "El tracker empieza a medir al iniciar sesión.", th["faint"], th["panel"])
            return

        rows = h - 3
        # Lista de hoy a la izquierda; historial y resumen a la derecha.
        right_w = 0
        list_w = w - 4
        if w >= 96 and self.usage.apps_week:
            right_w = min(52, max(38, round(w * 0.36)))
            list_w = w - 4 - right_w - 3

        max_seconds = max(seconds for _, seconds in self.usage.apps) or 1
        columns = 1 if len(self.usage.apps) <= rows else (2 if list_w >= 62 else 1)
        capacity = rows * columns
        if len(self.usage.apps) > capacity:
            rows -= 1
            capacity = rows * columns
        shown = self.usage.apps[: max(0, capacity)]
        col_w = ((list_w - 2) // 2) if columns == 2 else list_w
        for index, (cls, seconds) in enumerate(shown):
            col, row = divmod(index, max(1, rows))
            base_x = x + 2 + col * (col_w + 2)
            row_y = cy + row
            active = cls == self.sampler.active_class
            color = th["accent"] if active else th["secondary"]
            name = icons.display_name(cls)
            icon = icons.icon_for(cls)
            c.put(base_x, row_y, icon, color, th["panel"], active)
            name_w = 16 if col_w >= 46 else (14 if col_w >= 36 else 11)
            c.put(
                base_x + 3,
                row_y,
                fit(name, name_w),
                th["accent"] if active else th["fg"],
                th["panel"],
                active,
            )
            duration = fmt_dur(seconds)
            time_x = base_x + col_w - len(duration)
            bar_x = base_x + 3 + name_w + 1
            bar_w = max(4, time_x - 2 - bar_x)
            self.bar(
                c,
                bar_x,
                row_y,
                bar_w,
                seconds / max_seconds * 100,
                th,
                color,
                empty_color=th["track"],
            )
            c.put(
                time_x,
                row_y,
                duration,
                th["accent"] if active else th["dim"],
                th["panel"],
                active,
            )

        hidden = len(self.usage.apps) - len(shown)
        if hidden > 0:
            c.put(
                x + 2,
                y + h - 2,
                f"+{hidden} apps más",
                th["faint"],
                th["panel"],
            )

        if right_w:
            self.apps_side(c, x + w - 2 - right_w, cy, right_w, rows, th, now)

    def apps_side(
        self,
        c: Canvas,
        x: int,
        y: int,
        w: int,
        h: int,
        th,
        now: dt.datetime,
    ) -> None:
        """Historial de la semana y resumen del día."""
        week = self.usage.apps_week[:5]
        week_total = sum(seconds for _, seconds in self.usage.apps_week)
        c.put(x, y, "ÚLTIMOS 7 DÍAS", th["accent"], th["panel"], True)
        total_text = fmt_dur(week_total)
        c.put(x + w - len(total_text), y, total_text, th["dim"], th["panel"])
        max_week = max((seconds for _, seconds in week), default=1) or 1
        wy = y + 1
        name_w = min(18, max(10, w - 22))
        for cls, seconds in week:
            icon = icons.icon_for(cls)
            c.put(x, wy, icon, th["secondary"], th["panel"])
            c.put(
                x + 3,
                wy,
                fit(icons.display_name(cls), name_w),
                th["fg"],
                th["panel"],
            )
            duration = fmt_dur(seconds)
            time_x = x + w - len(duration)
            bar_x = x + 3 + name_w + 1
            bar_w = max(4, time_x - 2 - bar_x)
            self.bar(
                c,
                bar_x,
                wy,
                bar_w,
                seconds / max_week * 100,
                th,
                th["secondary"],
                empty_color=th["track"],
            )
            c.put(time_x, wy, duration, th["dim"], th["panel"])
            wy += 1

        registered = sum(seconds for _, seconds in self.usage.apps)
        presence = self.usage.seconds_for(now.date())
        idle = max(0, presence - registered)
        summary_y = wy + 1
        if summary_y + 6 < y + h:
            c.put(x, summary_y, "╌" * w, th["track"], th["panel"])
            c.put(x, summary_y + 1, "RESUMEN", th["faint"], th["panel"], True)
            self.kv(c, x, summary_y + 2, w, "presencia hoy", fmt_dur(presence), th)
            self.kv(c, x, summary_y + 3, w, "registrado", fmt_dur(registered), th, th["accent"])
            self.kv(c, x, summary_y + 4, w, "sin ventana", fmt_dur(idle), th, th["dim"])
            self.kv(c, x, summary_y + 5, w, "apps distintas", str(len(self.usage.apps)), th)

    # -- composición --------------------------------------------------------
    def draw(self, now: dt.datetime) -> Canvas:
        th = theme.load()
        c = Canvas(self.w, self.h, th["bg"])
        self.header(c, th, now)
        self.footer(c, th, now)

        top = 2
        bottom = self.h - 1
        ch = bottom - top
        gap = 1
        if ch < 30:
            c.put(2, top + 1, "Terminal demasiado pequeña", th["warn"], None, True)
            return c

        portrait = self.w < self.h * 2.0 and self.w >= 90 and ch >= 70
        if portrait:
            clock_h = 13
            cal_h = min(31, max(24, round(ch * 0.29)))
            apps_h = min(18, max(12, round(ch * 0.17)))
            gauges_h = ch - clock_h - cal_h - apps_h - 3 * gap
            if gauges_h < 30:
                cal_h = max(22, cal_h - (30 - gauges_h))
                gauges_h = ch - clock_h - cal_h - apps_h - 3 * gap
            if gauges_h < 24:
                apps_h = max(10, apps_h - (24 - gauges_h))
                gauges_h = ch - clock_h - cal_h - apps_h - 3 * gap
            clock_w = round(self.w * 0.44)
            week_w = self.w - clock_w - gap
            self.clock(c, 0, top, clock_w, clock_h, th, now)
            self.week(c, clock_w + gap, top, week_w, clock_h, th, now)

            gauges_y = top + clock_h + gap
            gauges_w = round(self.w * 0.56)
            thermo_w = self.w - gauges_w - gap
            self.gauges(c, 0, gauges_y, gauges_w, gauges_h, th)
            self.thermals(c, gauges_w + gap, gauges_y, thermo_w, gauges_h, th)

            cal_y = gauges_y + gauges_h + gap
            cal_w = round(self.w * 0.45)
            self.calendar(c, 0, cal_y, cal_w, cal_h, th, now)
            self.uptime(c, cal_w + gap, cal_y, self.w - cal_w - gap, cal_h, th, now)

            apps_y = cal_y + cal_h + gap
            self.apps(c, 0, apps_y, self.w, apps_h, th, now)
            return c

        wide = self.w >= 188 and ch >= 40
        if wide:
            left_w = max(58, round(self.w * 0.285))
            mid_w = max(60, round(self.w * 0.335))
            right_w = self.w - left_w - mid_w - 2 * gap
            if right_w < 56:
                mid_w -= 56 - right_w
                right_w = 56
            if mid_w < 56:
                left_w -= 56 - mid_w
                mid_w = 56
            if right_w < 50:
                wide = False

        if wide:
            clock_h = min(11, ch - 24)
            week_h = 10
            left_x = 0
            mid_x = left_w + gap
            right_x = mid_x + mid_w + gap
            self.clock(c, left_x, top, left_w, clock_h, th, now)
            self.week(c, left_x, top + clock_h + gap, left_w, week_h, th, now)
            up_y = top + clock_h + gap + week_h + gap
            up_h = bottom - up_y
            self.uptime(c, left_x, up_y, left_w, up_h, th, now)

            gauges_h = max(24, round(ch * 0.56))
            self.gauges(c, mid_x, top, mid_w, gauges_h, th)
            therm_y = top + gauges_h + gap
            self.thermals(c, mid_x, therm_y, mid_w, bottom - therm_y, th)

            cal_h = min(21, max(17, ch - 17))
            self.calendar(c, right_x, top, right_w, cal_h, th, now)
            apps_y = top + cal_h + gap
            self.apps(c, right_x, apps_y, right_w, bottom - apps_y, th, now)
        else:
            # Fallback en dos columnas para terminales más estrechas.
            if self.w < 112:
                c.put(
                    2,
                    top + 1,
                    "Terminal demasiado estrecha · usa al menos 112 columnas",
                    th["warn"],
                    None,
                    True,
                )
                return c
            left_w = max(46, round(self.w * 0.38))
            right_x = left_w + gap
            right_w = self.w - right_x
            clock_h = min(11, ch - 18)
            self.clock(c, 0, top, left_w, clock_h, th, now)
            self.week(c, 0, top + clock_h + gap, left_w, 10, th, now)
            up_y = top + clock_h + gap + 10 + gap
            self.uptime(c, 0, up_y, left_w, bottom - up_y, th, now)

            gauges_h = max(22, min(30, round(ch * 0.48)))
            self.gauges(c, right_x, top, right_w, gauges_h, th)
            cal_y = top + gauges_h + gap
            cal_h = 19
            self.calendar(c, right_x, cal_y, right_w, cal_h, th, now)
            apps_y = cal_y + cal_h + gap
            self.apps(c, right_x, apps_y, right_w, bottom - apps_y, th, now)
        return c


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dashboard TUI de presencia y sistema")
    parser.add_argument("--snapshot", action="store_true", help="imprime un frame y sale")
    parser.add_argument("--plain", action="store_true", help="sin colores (para depurar)")
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    args = parser.parse_args()

    if args.snapshot:
        size = shutil.get_terminal_size()
        width = args.width or size.columns
        height = args.height or size.lines
        app = Dashboard(max(80, width), max(24, height))
        app.usage.refresh(force=True)
        frame = app.draw(dt.datetime.now()).render(plain=args.plain)
        print(frame)
        return 0

    try:
        fd = sys.stdin.fileno()
        old_term = termios.tcgetattr(fd)
    except (termios.error, ValueError, OSError):
        old_term = None
        fd = -1

    stop = False

    def resize(_signum, _frame):
        nonlocal stop

    def terminate(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGWINCH, resize)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)

    if old_term is not None:
        tty.setcbreak(fd)
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    sys.stdout.flush()

    app: Dashboard | None = None
    try:
        while not stop:
            started = time.monotonic()
            size = shutil.get_terminal_size()
            width, height = size.columns, size.lines
            if app is None or app.w != width or app.h != height:
                app = Dashboard(max(80, width), max(24, height))
            else:
                app.sampler.update()
                app.usage.refresh()

            now = dt.datetime.now()
            frame = app.draw(now).render()
            sys.stdout.write("\x1b[?2026h" + frame + "\x1b[?2026l")
            sys.stdout.flush()

            if fd >= 0:
                ready, _, _ = select.select([sys.stdin], [], [], max(0.05, 1.0 - (time.monotonic() - started)))
                if ready:
                    key = os.read(fd, 16)
                    if key in (b"q", b"Q", b"\x03", b"\x1b"):
                        break
                    if key in (b"r", b"R"):
                        app.usage.refresh(force=True)
            else:
                time.sleep(max(0.05, 1.0 - (time.monotonic() - started)))
    finally:
        sys.stdout.write("\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        if old_term is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_term)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
