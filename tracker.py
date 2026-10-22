#!/usr/bin/env python3
"""Registra presencia y uso de aplicaciones para el dashboard.

Se ejecuta en segundo plano (una sola instancia, protegida por flock desde
tracker.sh). Guarda datos agregados por día en SQLite:

  presence(day, seconds)     tiempo con la sesión desbloqueada
  apps(day, cls, seconds)    tiempo con cada ventana activa
  meta(key, value)           estado interno (seed, sesión, boot id)

La primera vez rellena el historial disponible en wtmp para que el calendario
del mes no empiece vacío.
"""

from __future__ import annotations

import datetime as dt
import getpass
import os
import pathlib
import re
import signal
import sqlite3
import subprocess
import sys
import time

TICK = 5
STATE = pathlib.Path.home() / ".local/share/unix-dashboard"
DB_PATH = STATE / "usage.db"
IGNORED = {"", "unixporn-board", "hyprland", "desktop", "xdg-desktop-portal-gtk"}
_running = True


def _terminate(_signum, _frame):
    global _running
    _running = False


def run(cmd: list[str], timeout: float = 2.0, env: dict | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def day_key(moment: dt.datetime | None = None) -> str:
    return (moment or dt.datetime.now()).strftime("%Y-%m-%d")


def boot_id() -> str:
    try:
        return pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return ""


def session_locked() -> bool:
    sid = os.environ.get("XDG_SESSION_ID")
    if not sid:
        return False
    value = run(["loginctl", "show-session", sid, "-p", "LockedHint", "--value"], 1.0)
    return value.lower() == "yes"


def active_class() -> str:
    out = run(["hyprctl", "-j", "activewindow"], 1.0)
    if not out:
        return ""
    try:
        import json

        window = json.loads(out)
    except ValueError:
        return ""
    if window.get("title") == "ARCH // WORKSTATION":
        return "unixporn-board"
    cls = window.get("class") or window.get("initialClass") or ""
    return str(cls)


def connect() -> sqlite3.Connection:
    STATE.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS presence (
            day TEXT PRIMARY KEY,
            seconds INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS apps (
            day TEXT NOT NULL,
            cls TEXT NOT NULL,
            seconds INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (day, cls)
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    return conn


def meta_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


DATE_RE = re.compile(
    r"([A-Z][a-z]{2} [A-Z][a-z]{2} +\d+ \d{2}:\d{2}:\d{2} \d{4})"
)


def _parse_last_date(text: str) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(" ".join(text.split()), "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None


def seed_from_wtmp(conn: sqlite3.Connection) -> None:
    """Rellena días pasados a partir de las sesiones de `last`."""
    if meta_get(conn, "seeded") == "1":
        return

    env = dict(os.environ, LC_ALL="C", LANG="C")
    output = run(["last", "-F", "-w"], 5.0, env=env)
    now = dt.datetime.now()
    intervals: list[tuple[dt.datetime, dt.datetime]] = []

    username = getpass.getuser()
    for line in output.splitlines():
        fields = line.split(maxsplit=1)
        if not fields or fields[0] != username:
            continue
        dates = DATE_RE.findall(line)
        if not dates:
            continue
        start = _parse_last_date(dates[0])
        if not start:
            continue
        end: dt.datetime | None = None
        if "still logged in" in line:
            end = now
        elif len(dates) >= 2:
            end = _parse_last_date(dates[1])
        elif " - down" in line or line.rstrip().endswith("down"):
            match = re.search(r"\((\d+):(\d+)\)", line)
            if match:
                end = start + dt.timedelta(
                    hours=int(match.group(1)), minutes=int(match.group(2))
                )
        if end and end > start:
            intervals.append((start, min(end, now)))

    # Fusiona sesiones solapadas (varias terminales) para no contar de más.
    intervals.sort()
    merged: list[list[dt.datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    for start, end in merged:
        cursor = start
        while cursor < end:
            next_midnight = (cursor + dt.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            slice_end = min(end, next_midnight)
            seconds = int((slice_end - cursor).total_seconds())
            if seconds > 0:
                conn.execute(
                    "INSERT INTO presence(day, seconds) VALUES(?, ?) "
                    "ON CONFLICT(day) DO UPDATE SET seconds=seconds+excluded.seconds",
                    (day_key(cursor), seconds),
                )
            cursor = slice_end

    meta_set(conn, "seeded", "1")
    conn.commit()


def session_start_time() -> dt.datetime | None:
    """Hora de inicio de la sesión gráfica según logind."""
    sid = os.environ.get("XDG_SESSION_ID")
    if sid:
        env = dict(os.environ, LC_ALL="C", LANG="C")
        text = run(
            ["loginctl", "show-session", sid, "-p", "Timestamp", "--value"],
            1.5,
            env,
        )
        try:
            parsed = dt.datetime.strptime(text, "%a %Y-%m-%d %H:%M:%S %z")
            return dt.datetime.fromtimestamp(parsed.timestamp())
        except ValueError:
            pass
    # Fallback: arranque del sistema.
    try:
        uptime = float(pathlib.Path("/proc/uptime").read_text().split()[0])
        return dt.datetime.now() - dt.timedelta(seconds=uptime)
    except (OSError, ValueError, IndexError):
        return None


def main() -> None:
    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)

    conn = connect()
    seed_from_wtmp(conn)

    boot = boot_id()
    start = session_start_time()
    if meta_get(conn, "boot_id") != boot or start is not None:
        meta_set(conn, "boot_id", boot)
        if start is not None:
            meta_set(conn, "session_start", start.isoformat(timespec="seconds"))
        else:
            meta_set(conn, "session_start", dt.datetime.now().isoformat(timespec="seconds"))
    meta_set(conn, "tracker_last", dt.datetime.now().isoformat(timespec="seconds"))
    conn.commit()

    while _running:
        started = time.monotonic()
        now = dt.datetime.now()
        day = day_key(now)
        locked = session_locked()
        cls = active_class() if not locked else ""

        if not locked:
            conn.execute(
                "INSERT INTO presence(day, seconds) VALUES(?, ?) "
                "ON CONFLICT(day) DO UPDATE SET seconds=seconds+excluded.seconds",
                (day, TICK),
            )
            if cls not in IGNORED:
                conn.execute(
                    "INSERT INTO apps(day, cls, seconds) VALUES(?, ?, ?) "
                    "ON CONFLICT(day, cls) DO UPDATE SET seconds=seconds+excluded.seconds",
                    (day, cls, TICK),
                )
            meta_set(conn, "active_class", cls)
            meta_set(conn, "last_seen", now.isoformat(timespec="seconds"))
        else:
            meta_set(conn, "active_class", "")

        meta_set(conn, "tracker_last", now.isoformat(timespec="seconds"))
        conn.commit()

        elapsed = time.monotonic() - started
        deadline = started + TICK
        while _running and time.monotonic() < deadline:
            time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
        if elapsed > TICK:
            time.sleep(0)  # el retraso se descuenta en el siguiente ciclo

    conn.close()


if __name__ == "__main__":
    sys.exit(main())
