"""Explicit, bounded OpenRGB commands; never changes lighting on startup."""
import colorsys
import math
import json
import re
import subprocess
import threading
import sys
import time
from pathlib import Path

PATH = Path(__file__).with_name('lighting.json')
LOCK = threading.Lock()
MODES = {'Fijo': ('Static','Direct'), 'Respiración': ('Breathing','Color Pulse'), 'Arcoíris': ('Rainbow','Rainbow Wave'), 'Apagado': ('Off','Direct')}

def snapshot():
    try:
        return json.loads(PATH.read_text())
    except (OSError, ValueError):
        return dict(mode='Fijo', color='00FF00', speed=50, target='Ambos', applied=False)

def apply(values):
    mode, target = values.get('mode'), values.get('target')
    color = values.get('color', '').lstrip('#').upper()
    speed = values.get('speed',50)
    if mode not in MODES or target not in ('Todo','Ambos','Placa','RAM','HyperX') or not re.fullmatch(r'[0-9A-F]{6}',color):
        raise ValueError('Modo, destino o color no válido')
    if isinstance(speed,bool) or not isinstance(speed,int) or not 0 <= speed <= 100:
        raise ValueError('Velocidad no válida')
    with LOCK:
        sys.path.insert(0,str(PATH.parent/'vendor'))
        from openrgb import OpenRGBClient
        from openrgb.utils import ModeFlags, ModeColors, RGBColor
        try:
            client=OpenRGBClient(port=6743,name='Unix Dashboard')
        except OSError:
            subprocess.run(['systemctl','--user','start','unix-dashboard-rgb.service'],check=True,timeout=5)
            for attempt in range(40):
                try:
                    client=OpenRGBClient(port=6743,name='Unix Dashboard')
                    break
                except OSError:
                    if attempt==39: raise
                    time.sleep(.25)
        try:
            devices=[]
            for device in client.devices:
                if device.name=='ASRock X870 Pro RS' and target in ('Todo','Ambos','Placa'):
                    devices.append((device,MODES[mode][0]))
                if device.name=='Corsair Vengeance RGB DDR5' and target in ('Todo','Ambos','RAM'):
                    devices.append((device,MODES[mode][1]))
                if device.name=='HyperX Quadcast S' and target in ('Todo','HyperX'):
                    devices.append((device,'Direct'))
            expected=4 if target=='Todo' else 3 if target=='Ambos' else 2 if target=='RAM' else 1
            if len(devices)!=expected: raise ValueError('No se detectaron todos los dispositivos seleccionados')
            native=[]
            for device,effect in devices:
                chosen=next(m for m in device.modes if m.name==effect)
                if ModeFlags.HAS_SPEED in chosen.flags:
                    chosen.speed=native_speed(chosen.speed_min,chosen.speed_max,speed)
                    native.append(dict(device=device.name,value=chosen.speed,minimum=chosen.speed_min,maximum=chosen.speed_max))
                device.set_mode(chosen,force=True)
                if chosen.color_mode!=ModeColors.NONE:
                    device.set_color(RGBColor.fromHEX('000000' if mode=='Apagado' else color))
            data=dict(mode=mode,target=target,color=color,speed=speed,applied=True,nativeSpeeds=native)
            previous=snapshot().get('hyperx')
            if target in ('Todo','HyperX'):
                data['hyperx']=dict(mode=mode,color=color,speed=speed)
            elif previous:
                data['hyperx']=previous
            temp=PATH.with_suffix('.tmp');temp.write_text(json.dumps(data));temp.replace(PATH)
            return data
        finally:
            client.disconnect()

def native_speed(minimum,maximum,percent):
    return round(minimum+(maximum-minimum)*percent/100)


def worker(stop):
    """QuadCast only exposes direct colors; animate its two LEDs at 10 Hz."""
    sys.path.insert(0,str(PATH.parent/'vendor'))
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
    client=None
    device=None
    config=None
    phase=0.0
    last=time.monotonic()
    try:
        while not stop.wait(.1):
            settings=snapshot().get('hyperx')
            now=time.monotonic()
            elapsed=min(1,now-last);last=now
            if not settings or settings['mode'] not in ('Respiración','Arcoíris'):
                continue
            try:
                with LOCK:
                    if client is None:
                        client=OpenRGBClient(port=6743,name='Dashboard HyperX effects')
                        device=next(d for d in client.devices if d.name=='HyperX Quadcast S')
                    if settings!=config:
                        config=dict(settings);phase=0
                    phase=(phase+elapsed*(.08+settings['speed']/100*.8))%1
                    if settings['mode']=='Arcoíris':
                        rgb=colorsys.hsv_to_rgb(phase,.85,1)
                    else:
                        brightness=.12+.88*(.5+.5*math.sin(phase*math.pi*2))
                        rgb=tuple(int(settings['color'][i:i+2],16)/255*brightness for i in (0,2,4))
                    device.set_color(RGBColor(*(round(c*255) for c in rgb)),fast=True)
            except Exception as exc:
                if client:
                    try: client.disconnect()
                    except OSError: pass
                client=None
                print(f'HyperX RGB: {exc}',flush=True)
                stop.wait(2)
    finally:
        if client: client.disconnect()
