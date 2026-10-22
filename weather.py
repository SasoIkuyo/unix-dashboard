"""Open-Meteo weather, fetched separately from the UI and system sampler."""
import datetime as dt
import json
from pathlib import Path
import threading
import urllib.parse
import urllib.request
import preferences

CONFIG = Path(__file__).with_name('weather.json')
CACHE = Path.home()/'.cache/unix-dashboard/weather.json'
wake = threading.Event()
lock = threading.Lock()
current = {'ready': False, 'status': 'Elige tu ciudad', 'city': '', 'forecast': []}

def read_config():
    try:
        value = json.loads(CONFIG.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def set_city(city):
    if not isinstance(city, str) or not 2 <= len(city.strip()) <= 120:
        raise ValueError('Ciudad no válida')
    temp=CONFIG.with_suffix('.tmp')
    temp.write_text(json.dumps({'city': city.strip()},ensure_ascii=False)+'\n')
    temp.replace(CONFIG)
    with lock:
        current.clear(); current.update(ready=False,status='Buscando ciudad…',city=city.strip(),forecast=[])
    wake.set()

def snapshot():
    with lock: return dict(current)

def fetch(url, params):
    request=urllib.request.Request(url+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'unix-dashboard/1.0'})
    with urllib.request.urlopen(request,timeout=10) as response:
        return json.load(response)

def condition(code, day=True):
    if code == 0: return ('Despejado','☀' if day else '☾')
    if code in (1,2): return ('Parcialmente nublado','⛅')
    if code == 3: return ('Nublado','☁')
    if code in (45,48): return ('Niebla','≋')
    if code in (51,53,55,56,57): return ('Llovizna','☂')
    if code in (61,63,65,66,67,80,81,82): return ('Lluvia','☂')
    if code in (71,73,75,77,85,86): return ('Nieve','❄')
    if code in (95,96,99): return ('Tormenta','ϟ')
    return ('Sin información','·')

def load_weather(config):
    if 'latitude' not in config:
        places=fetch('https://geocoding-api.open-meteo.com/v1/search',{'name':config['city'],'count':1,'language':'es'}).get('results',[])
        if not places: raise ValueError('Ciudad no encontrada')
        place=places[0]
        config.update(latitude=place['latitude'],longitude=place['longitude'],label=place['name']+', '+place.get('country_code',''))
        # Do not overwrite a new location entered while this request was running.
        if read_config().get('city') == config['city']:
            temp=CONFIG.with_suffix('.geo.tmp');temp.write_text(json.dumps(config,ensure_ascii=False)+'\n');temp.replace(CONFIG)
    result=fetch('https://api.open-meteo.com/v1/forecast',{
        'latitude':config['latitude'],'longitude':config['longitude'],
        'current':'temperature_2m,apparent_temperature,relative_humidity_2m,is_day,weather_code,wind_speed_10m',
        'daily':'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
        'timezone':'auto','forecast_days':5})
    now=result['current'];daily=result['daily'];description,icon=condition(now['weather_code'],now['is_day'])
    forecast=[]
    for i,date in enumerate(daily['time']):
        label='Hoy' if i==0 else ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'][dt.date.fromisoformat(date).weekday()]
        desc,symbol=condition(daily['weather_code'][i])
        forecast.append(dict(day=label,icon=symbol,description=desc,high=round(daily['temperature_2m_max'][i]),low=round(daily['temperature_2m_min'][i]),rain=daily['precipitation_probability_max'][i] or 0))
    return dict(ready=True,city=config.get('label',config['city']),query=config['city'],status=description,icon=icon,temperature=round(now['temperature_2m']),feels=round(now['apparent_temperature']),humidity=now['relative_humidity_2m'],wind=round(now['wind_speed_10m']),forecast=forecast,updated=dt.datetime.now().strftime('%H:%M'),stale=False)

def worker(stop):
    try:
        cached=json.loads(CACHE.read_text())
        if cached.get('query')==read_config().get('city'):
            cached['stale']=True
            with lock: current.update(cached)
    except (OSError,ValueError): pass
    while not stop.is_set():
        wake.clear()
        config=read_config(); retry=preferences.load()["weatherInterval"]*60
        if config.get('city'):
            try:
                result=load_weather(config)
                if read_config().get('city')==config['city']:
                    with lock: current.clear();current.update(result)
                    CACHE.parent.mkdir(parents=True,exist_ok=True)
                    temp=CACHE.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False));temp.replace(CACHE)
            except Exception as exc:
                retry=120
                with lock:
                    if read_config().get('city')==config['city']:
                        current['stale']=True
                        current['status']=current.get('status','') if current.get('ready') else ('Ciudad no encontrada' if isinstance(exc,ValueError) else 'Clima no disponible · reintentando')
        wake.wait(retry)
