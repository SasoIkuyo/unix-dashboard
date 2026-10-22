import datetime
import json
import pathlib
import shutil
import time

DIGITS = {
    '0': ['╭──╮', '│  │', '│  │', '│  │', '╰──╯'],
    '1': [' ╷  ', ' │  ', ' │  ', ' │  ', ' ╵  '],
    '2': ['╭──╮', '   │', '╭──╯', '│   ', '╰───'],
    '3': ['╭──╮', '   │', ' ──┤', '   │', '╰──╯'],
    '4': ['╷  ╷', '│  │', '╰──┤', '   │', '   ╵'],
    '5': ['╭───', '│   ', '╰──╮', '   │', '╰──╯'],
    '6': ['╭──╮', '│   ', '├──╮', '│  │', '╰──╯'],
    '7': ['───╮', '   │', '  ╱ ', ' ╱  ', '╵   '],
    '8': ['╭──╮', '│  │', '├──┤', '│  │', '╰──╯'],
    '9': ['╭──╮', '│  │', '╰──┤', '   │', '╰──╯'],
    ':': ['    ', ' ▪  ', '    ', ' ▪  ', '    '],
}
ARCH = ['       /\\       ', '      /  \\      ', '     / /\\ \\     ', '    / /  \\ \\    ', '   / /    \\ \\   ', '  /_/  /\\  \\_\\  ', ' /___ /  \\ ___\\ ', '       ARCH      ']
state = pathlib.Path.home() / '.local/state/caelestia/scheme.json'
previous_size = None
print('\033[?25l', end='')
try:
    while True:
        now = datetime.datetime.now()
        size = shutil.get_terminal_size()
        if size != previous_size:
            print('\033[2J', end='')
            previous_size = size
        try:
            color = json.loads(state.read_text())['colours']['primary']
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        except (OSError, KeyError, ValueError):
            rgb = (155, 208, 204)
        accent = '\033[38;2;%d;%d;%dm' % rgb
        digits = now.strftime('%H:%M:%S')
        clock = [' '.join(DIGITS[c][row] for c in digits) for row in range(5)]
        right = ['C A E L E S T I A  //  A R C H', '', *clock, '', now.strftime('%A · %d %B %Y'), 'WORKSTATION ONLINE  /  WAYLAND']
        rows = []
        for i, text in enumerate(right):
            logo = ARCH[i-1] if 1 <= i <= len(ARCH) else ' ' * 17
            rows.append(logo.ljust(20) + '    ' + text)
        output = [''] * max(0, (size.lines - len(rows)) // 2)
        for row in rows:
            output.append(' ' * max(0, (size.columns - 65) // 2) + row)
        output += [''] * max(0, size.lines - len(output))
        print('\033[?2026h\033[H' + accent + '\r\n'.join(line[:size.columns].ljust(size.columns) for line in output[:max(1, size.lines-1)]) + '\033[0m\033[?2026l', end='', flush=True)
        time.sleep(1)
except KeyboardInterrupt:
    print('\033[?25h\033[0m', end='')
