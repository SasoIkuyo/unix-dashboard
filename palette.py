import json
import pathlib
import re

root = pathlib.Path(__file__).parent
scheme = json.loads((pathlib.Path.home()/'.local/state/caelestia/scheme.json').read_text())['colours']
get = lambda key: '#' + scheme[key].lstrip('#')
colors = {'background': get('background'), 'foreground': get('onSurface'), 'cursor': get('primary'), 'active_border_color': get('primary'), 'inactive_border_color': get('outlineVariant')}
for i in range(16):
    colors['color'+str(i)] = get('term'+str(i)) if 'term'+str(i) in scheme else get('primary' if i%2 else 'onSurface')
(root/'colors.conf').write_text('\n'.join(f'{k} {v}' for k,v in colors.items())+'\n')
template = pathlib.Path('/usr/share/btop/themes/tokyo-night.theme').read_text()
mapping = {'#1a1b26':get('background'), '#cfc9c2':get('onSurface'), '#7dcfff':get('primary'), '#414868':get('surfaceContainerHigh'), '#565f89':get('outline'), '#9ece6a':get('primaryContainer'), '#e0af68':get('primary'), '#f7768e':get('tertiary')}
template = re.sub(r'#[0-9a-fA-F]{6}', lambda m: mapping.get(m[0],m[0]), template)
(root/'caelestia.theme').write_text(template)
(root/'cava.conf').write_text(f'''[general]
framerate = 30
bars = 12
bar_width = 2
bar_spacing = 1
autosens = 1
[input]
method = pipewire
source = auto
[color]
background = 'default'
foreground = '{get("primary")}'
gradient = 1
gradient_count = 3
gradient_color_1 = '{get("primaryContainer")}'
gradient_color_2 = '{get("primary")}'
gradient_color_3 = '{get("tertiary")}'
''')
