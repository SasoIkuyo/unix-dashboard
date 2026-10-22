#!/usr/bin/env python3
"""Pause Aura wallpapers for games or fully covered monitors."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
paused = set()


def command(path, *args):
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(1)
        client.connect(str(path))
        client.sendall((json.dumps({"command": args, "request_id": 42}) + "\n").encode())
        with client.makefile() as stream:
            for line in stream:
                reply = json.loads(line)
                if reply.get("request_id") == 42:
                    if reply.get("error") != "success":
                        raise RuntimeError(reply)
                    return reply.get("data")


def fully_covered(monitor, windows):
    """Pause this output whenever an ordinary app is visible on it."""
    if not monitor.get('dpmsStatus', True):
        return True
    workspaces={monitor['activeWorkspace']['id']}
    special=monitor.get('specialWorkspace',{}).get('id',0)
    if special: workspaces.add(special)
    width,height=monitor['width'],monitor['height']
    if monitor.get('transform',0)%2: width,height=height,width
    scale=monitor.get('scale',1)
    left,top=monitor['x'],monitor['y']
    right,bottom=left+width/scale,top+height/scale
    for window in windows:
        if (not window.get('mapped') or window.get('hidden')
                or window.get('visible') is False
                or window.get('class')=='unixporn-board'
                or (window.get('workspace',{}).get('id') not in workspaces
                    and not window.get('pinned'))):
            continue
        x,y=window.get('at',[0,0]); w,h=window.get('size',[0,0])
        if min(right,x+w)>max(left,x) and min(bottom,y+h)>max(top,y):
            return True
    return False


def resume():
    for path in list(paused):
        try:
            command(path, "set_property", "pause", False)
            paused.discard(path)
        except (OSError, ValueError, RuntimeError):
            if not path.exists():
                paused.discard(path)


def stop(*_):
    raise SystemExit


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    while True:
        try:
            result = subprocess.run(
                ["hyprctl", "clients", "-j"], capture_output=True, text=True,
                check=True, timeout=3,
            )
            windows = json.loads(result.stdout)
            gaming = any(
                w.get("mapped") and (
                    any(t.rstrip("*") == "game" for t in w.get("tags", []))
                    or w.get("class", "").startswith("steam_app_")
                ) for w in windows
            )
            result = subprocess.run(
                ["hyprctl", "monitors", "-j"], capture_output=True, text=True,
                check=True, timeout=3,
            )
            monitors = json.loads(result.stdout)
            covered = {m["name"] for m in monitors if fully_covered(m, windows)}
            for path in (runtime / "aura").glob("mpv_*.sock"):
                output = path.name[len("mpv_"):-len(".sock")]
                try:
                    should_pause = gaming or output in covered
                    if should_pause:
                        if not command(path, "get_property", "pause"):
                            command(path, "set_property", "pause", True)
                            paused.add(path)
                    elif path in paused:
                        command(path, "set_property", "pause", False)
                        paused.discard(path)
                except (OSError, ValueError, RuntimeError):
                    if not path.exists():
                        paused.discard(path)
        except (subprocess.SubprocessError, ValueError):
            resume()
        time.sleep(1)
finally:
    resume()
