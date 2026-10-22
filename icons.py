"""Nombres e iconos Nerd Font para las aplicaciones del tracker."""

from __future__ import annotations

import os
import pathlib

# Nombres "bonitos" para las clases de ventana más habituales.
NAMES = {
    "firefox": "Firefox",
    "brave-browser": "Brave",
    "brave": "Brave",
    "chromium": "Chromium",
    "google-chrome": "Chrome",
    "google-chrome-stable": "Chrome",
    "microsoft-edge": "Edge",
    "vivaldi-stable": "Vivaldi",
    "opera": "Opera",
    "code": "Visual Studio Code",
    "code-oss": "Code OSS",
    "codium": "VSCodium",
    "zed": "Zed",
    "kitty": "Kitty",
    "foot": "Foot",
    "alacritty": "Alacritty",
    "wezterm": "WezTerm",
    "org.wezfurlong.wezterm": "WezTerm",
    "ghostty": "Ghostty",
    "konsole": "Konsole",
    "steam": "Steam",
    "discord": "Discord",
    "vesktop": "Vesktop",
    "equibop": "Equibop",
    "legcord": "Legcord",
    "equicord": "Equicord",
    "spotify": "Spotify",
    "org.telegram.desktop": "Telegram",
    "telegram": "Telegram",
    "signal": "Signal",
    "slack": "Slack",
    "obsidian": "Obsidian",
    "logseq": "Logseq",
    "qbittorrent": "qBittorrent",
    "org.qbittorrent.qbittorrent": "qBittorrent",
    "thunar": "Thunar",
    "dolphin": "Dolphin",
    "org.gnome.nautilus": "Archivos",
    "nautilus": "Archivos",
    "nemo": "Nemo",
    "pcmanfm": "PCManFM",
    "mpv": "mpv",
    "vlc": "VLC",
    "celluloid": "Celluloid",
    "org.gnome.showtime": "Showtime",
    "com.obsproject.studio": "OBS Studio",
    "obs": "OBS Studio",
    "krita": "Krita",
    "gimp": "GIMP",
    "inkscape": "Inkscape",
    "blender": "Blender",
    "virt-manager": "Virt Manager",
    "org.virt-manager.virt-manager": "Virt Manager",
    "minecraft": "Minecraft",
    "prismlauncher": "Prism Launcher",
    "org.prismlauncher.prismlauncher": "Prism Launcher",
    "lutris": "Lutris",
    "heroic": "Heroic",
    "com.heroicgameslauncher.hgl": "Heroic",
    "com.usebottles.bottles": "Bottles",
    "org.gnome.calculator": "Calculadora",
    "kcalc": "Calculadora",
    "org.kde.spectacle": "Spectacle",
    "swappy": "Swappy",
    "local.flameshot": "Flameshot",
    "org.pulseaudio.pavucontrol": "Audio",
    "pavucontrol": "Audio",
    "blueman-manager": "Bluetooth",
    "nm-connection-editor": "Redes",
    "hyprland": "Hyprland",
}

# Iconos Nerd Font (Font Awesome / Material). Todos de un solo ancho.
ICONS = {
    "terminal": "\uf120",
    "browser": "\uf0ac",
    "firefox": "\uf269",
    "chrome": "\uf268",
    "code": "\uf121",
    "music": "\uf001",
    "video": "\uf03d",
    "game": "\uf11b",
    "chat": "\uf086",
    "folder": "\uf07b",
    "file": "\uf15b",
    "image": "\uf03e",
    "settings": "\uf013",
    "download": "\uf019",
    "cloud": "\uf0ed",
    "steam": "\uf1b6",
    "spotify": "\uf1bc",
    "discord": "\uf392",
    "telegram": "\uf2c6",
    "signal": "\uf47f",
    "slack": "\uf198",
    "obsidian": "\uf0f6",
    "brave": "\uf268",
    "edge": "\uf282",
    "opera": "\uf26a",
    "note": "\uf044",
    "calc": "\uf1ec",
    "camera": "\uf030",
    "paint": "\uf1fc",
    "cube": "\uf1b2",
    "network": "\uf1eb",
    "bluetooth": "\uf293",
    "audio": "\uf028",
    "generic": "\uf2d0",
}


def pretty(cls: str) -> str:
    """Nombre legible a partir de la clase de ventana."""
    key = cls.lower()
    if key in NAMES:
        return NAMES[key]
    # Coincidencias parciales habituales (org.gnome.Foo, com.foo.Bar...).
    for token, name in NAMES.items():
        if len(token) > 3 and token in key:
            return name
    if key.startswith("org.") or key.startswith("com."):
        last = cls.split(".")[-1]
        return last.replace("-", " ").replace("_", " ").title()
    return cls.replace("-", " ").replace("_", " ").title() or "Desconocida"


def icon(cls: str) -> str:
    key = cls.lower()

    def has(*words: str) -> bool:
        return any(word in key for word in words)

    if has("kitty", "foot", "alacritty", "wezterm", "ghostty", "konsole", "terminal"):
        return ICONS["terminal"]
    if has("firefox"):
        return ICONS["firefox"]
    if has("brave"):
        return ICONS["brave"]
    if has("chrome", "chromium"):
        return ICONS["chrome"]
    if has("edge"):
        return ICONS["edge"]
    if has("opera"):
        return ICONS["opera"]
    if has("firefox", "zen"):
        return ICONS["browser"]
    if has("browser", "vivaldi"):
        return ICONS["browser"]
    if has("code", "codium", "zed", "idea", "studio"):
        return ICONS["code"]
    if has("discord", "vesktop", "equibop", "equicord", "legcord"):
        return ICONS["discord"]
    if has("telegram"):
        return ICONS["telegram"]
    if has("signal"):
        return ICONS["signal"]
    if has("slack"):
        return ICONS["slack"]
    if has("steam"):
        return ICONS["steam"]
    if has("spotify"):
        return ICONS["spotify"]
    if has("obsidian", "logseq", "typora", "notion"):
        return ICONS["obsidian"]
    if has("qbittorrent", "transmission", "deluge"):
        return ICONS["download"]
    if has("thunar", "dolphin", "nautilus", "nemo", "pcmanfm", "files"):
        return ICONS["folder"]
    if has("mpv", "vlc", "celluloid", "showtime", "player"):
        return ICONS["video"]
    if has("krita", "gimp", "inkscape", "blender", "figma"):
        return ICONS["paint"]
    if has("obs", "record"):
        return ICONS["camera"]
    if has("pavucontrol", "audio", "wireplumber", "easyeffects"):
        return ICONS["audio"]
    if has("bluetooth", "blueman"):
        return ICONS["bluetooth"]
    if has("network", "nm-connection", "warp", "tailscale"):
        return ICONS["network"]
    if has("calculator", "kcalc"):
        return ICONS["calc"]
    if has("virt-manager", "virtualbox", "vmware", "qemu"):
        return ICONS["cube"]
    if has("minecraft", "prism", "lutris", "heroic", "bottles", "game"):
        return ICONS["game"]
    if has("spectacle", "flameshot", "swappy", "grim"):
        return ICONS["camera"]
    return ICONS["generic"]


def desktop_name(cls: str) -> str | None:
    """Busca el Name de un .desktop cuyo WMClass coincida. Cacheado por proceso."""
    if not _desktop_index:
        _build_desktop_index()
    return _desktop_index.get(cls.lower())


_desktop_index: dict[str, str] = {}
_desktop_built = False


def _build_desktop_index() -> None:
    global _desktop_built
    if _desktop_built:
        return
    _desktop_built = True
    roots = [
        pathlib.Path.home() / ".local/share/applications",
        pathlib.Path("/usr/share/applications"),
        pathlib.Path("/var/lib/flatpak/exports/share/applications"),
        pathlib.Path.home() / ".local/share/flatpak/exports/share/applications",
    ]
    for root in roots:
        try:
            entries = list(root.glob("*.desktop"))
        except OSError:
            continue
        for path in entries:
            try:
                text = path.read_text(errors="replace")
            except OSError:
                continue
            name = None
            wmclass = None
            exec_line = None
            for line in text.splitlines():
                if line.startswith("Name=") and name is None:
                    name = line[5:].strip()
                elif line.startswith("StartupWMClass=") and wmclass is None:
                    wmclass = line[15:].strip()
                elif line.startswith("Exec=") and exec_line is None:
                    exec_line = line[5:].strip()
            if not name:
                continue
            keys = {path.stem.lower()}
            if wmclass:
                keys.add(wmclass.lower())
            if exec_line:
                exe = exec_line.split()[0].rsplit("/", 1)[-1]
                exe = exe.replace("%U", "").replace("%u", "").strip()
                if exe:
                    keys.add(exe.lower())
            for key in keys:
                _desktop_index.setdefault(key, name)


def display_name(cls: str) -> str:
    if not cls:
        return "Escritorio"
    return NAMES.get(cls.lower()) or desktop_name(cls) or pretty(cls)


# Iconos que no dependen de la clase sino del nombre del juego/app.
def icon_for(cls: str) -> str:
    return icon(cls)


def truncate(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return "…"[:width]
    return text[: width - 1] + "…"

# Native desktop icons are used by the graphical dashboard instead of private
# font glyphs, which differ between Nerd Font versions.
_native_icons = None

def native_icon(cls: str) -> str:
    global _native_icons
    if _native_icons is None:
        import configparser
        import shlex
        _native_icons = {}
        roots = [pathlib.Path.home()/'.local/share/applications', pathlib.Path.home()/'.local/share/flatpak/exports/share/applications', pathlib.Path('/var/lib/flatpak/exports/share/applications'), pathlib.Path('/usr/local/share/applications'), pathlib.Path('/usr/share/applications')]
        for root in roots:
            for path in sorted(root.glob('*.desktop')):
                try:
                    conf = configparser.ConfigParser(interpolation=None, strict=False)
                    conf.read(path, encoding='utf-8')
                    entry = conf['Desktop Entry']; icon_name = entry.get('Icon','')
                    if not icon_name: continue
                    keys = [path.stem, entry.get('StartupWMClass',''), entry.get('Name','')]
                    try:
                        executable = shlex.split(entry.get('Exec',''))
                        if executable: keys.append(pathlib.Path(executable[0]).name)
                    except ValueError: pass
                    for key in keys:
                        if key: _native_icons.setdefault(key.lower(),icon_name)
                except (OSError, ValueError, KeyError, configparser.Error):
                    continue
    key = cls.lower()
    if key in _native_icons: return _native_icons[key]
    for token in ('firefox','discord','steam','spotify','chatgpt','foot','kitty','code'):
        if token in key: return _native_icons.get(token,token)
    return 'application-x-executable'
