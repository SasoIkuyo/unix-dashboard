"""Validated, shared and persistent dashboard preferences."""
import json
import math
from pathlib import Path
import threading

FILE=Path(__file__).with_name('appearance.json')
LOCK=threading.RLock()
THEMES=['Lavanda','Océano','Bosque','Rosa','Ámbar','Nord','Dracula','Catppuccin','Gruvbox','Tokio','Solarizado','Carbón','Rubí','Menta','Cobre','Obsidiana','Caelestia']
DEFAULTS=dict(theme='Lavanda', lightningEnabled=True, lightningMin=5, lightningMax=9, lightningDuration=1.8, refreshInterval=1000, weatherInterval=10, backgroundOpacity=0.38, cardOpacity=0.66, fanMode='Automático', fanBoost=False, fanChannels=[], fanGPU=False, fanProfiles={'Silencioso':[35,45,70,100],'Equilibrado':[40,60,85,100],'Rendimiento':[55,75,95,100]})
BOUNDS=dict(lightningMin=(1,300),lightningMax=(1,300),lightningDuration=(0.5,4),refreshInterval=(500,5000),weatherInterval=(5,60),backgroundOpacity=(0,1),cardOpacity=(0,1))

def validate(values):
    if not isinstance(values,dict) or set(values)-set(DEFAULTS): raise ValueError('Ajustes no válidos')
    result=dict(DEFAULTS);result.update(values)
    if result['theme']=='Negro y rojo':result['theme']='Obsidiana'
    if result['theme'] not in THEMES:raise ValueError('Tema no válido')
    if not isinstance(result['lightningEnabled'],bool):raise ValueError('Estado de rayos no válido')
    for key,(low,high) in BOUNDS.items():
        value=result[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Valor no válido: '+key)
    if result['fanMode'] not in ['Automático','Silencioso','Equilibrado','Rendimiento']:raise ValueError('Modo de ventilación no válido')
    if not isinstance(result['fanBoost'],bool):raise ValueError('Máximo no válido')
    if not isinstance(result['fanGPU'],bool):raise ValueError('Objetivo GPU no válido')
    channels=result['fanChannels']
    if not isinstance(channels,list) or len(channels)!=len(set(channels)) or any(type(i) is not int or not 1<=i<=7 for i in channels):raise ValueError('Canales no válidos')
    profiles=result['fanProfiles']
    if not isinstance(profiles,dict) or set(profiles)!={'Silencioso','Equilibrado','Rendimiento'}:raise ValueError('Perfiles no válidos')
    for curve in profiles.values():
        if not isinstance(curve,list) or len(curve)!=4 or any(type(v) is not int or not 30<=v<=100 for v in curve) or curve!=sorted(curve) or curve[-1]!=100:raise ValueError('Las curvas deben subir entre 30 y 100%, terminando en 100%')
    if (result['fanMode']!='Automático' or result['fanBoost']) and not (channels or result['fanGPU']):raise ValueError('Selecciona un ventilador para aplicar el modo')
    if result['lightningMax']<result['lightningMin']:raise ValueError('El intervalo máximo debe ser mayor o igual al mínimo')
    return result

def load():
    with LOCK:
        try:return validate(json.loads(FILE.read_text()))
        except (OSError,ValueError,TypeError):return dict(DEFAULTS)

def save(changes):
    with LOCK:
        values=load();values.update(changes);values=validate(values)
        temporary=FILE.with_suffix('.tmp');temporary.write_text(json.dumps(values,ensure_ascii=False,indent=2)+'\n');temporary.replace(FILE)
        return values
