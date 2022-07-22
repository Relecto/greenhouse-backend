from MicroWebSrv2 import *
from time import sleep

from helpers import map, constrain

import dht
import machine
import time

humiditySensorA = machine.ADC(machine.Pin(32))
humiditySensorA.atten(machine.ADC.ATTN_11DB)
humiditySensorB = machine.ADC(machine.Pin(33))
humiditySensorB.atten(machine.ADC.ATTN_11DB)

humidityA = 0
humidityB = 0

temperatureSensor = dht.DHT11(machine.Pin(22))

# pumpA = machine.Pin(26, machine.Pin.OUT)
# pumpB = machine.Pin(27, machine.Pin.OUT)

# 200/1000
pumpA = machine.PWM(machine.Pin(27))
pumpA.deinit()
pumpB = machine.PWM(machine.Pin(26))
pumpB.deinit()

vent = machine.Pin(14, machine.Pin.OUT)
lights = machine.Pin(13, machine.Pin.OUT)

rtc = machine.RTC()

mws2 = MicroWebSrv2()

mws2.SetEmbeddedConfig()
mws2.BufferSlotsCount = 4
mws2.BufferSlotSize = 512

mws2.RootPath = 'public/'

# Показания датчиков здесь
metrics = {
    'temperature': 0,
    'moisture': 0,
    'soilA': 0,
    'soilB': 0,
}

# Пороги активации
ranges = {
    'pumpA': {
        'lower': 44.4,
        'upper': 77.7,
    },
    'pumpB': {
        'lower': 44.4,
        'upper': 77.7,
    },
    'vent': {
        'lower': 22,
        'upper': 80,
    },
    # Ну со светом я хз как лучше сделать, если честно
    'lights': {
        'lower': 9,
        'upper':18, 
    },
}

# Лимиты для валидации
limits = {
    'pumpA': {
        'lower': 0,
        'upper': 100,
    },
    'pumpB': {
        'lower': 0,
        'upper': 100,
    },
    'vent': {
        'lower': -40,
        'upper': 80,
    },
    # По прежнему - ХЗ
    'lights': {
        'lower': 0,
        'upper': 24,
    },
}

manual_control = False

active = {
    'pumpA': False,
    'pumpB': False,
    'vent': False,
    'lights': False
}

# Снимаем показания
def measure():
    # Инвертируем показания датчиков почвы
    metrics['soilA'] = map(humiditySensorA.read() / 40.95, 100, 0, 0, 100)
    metrics['soilB'] = map(humiditySensorB.read() / 40.95, 100, 0, 0, 100)

    try:
        temperatureSensor.measure()
        metrics['temperature'] = temperatureSensor.temperature()
        metrics['moisture'] = temperatureSensor.humidity()
    except Exception as e:
        print('could not read from DHT')
        print(e)


# Проверяем пороги
def check():
    if manual_control:
        return

    soilA = constrain(metrics['soilA'], limits['pumpA']['lower'], limits['pumpA']['upper'])
    soilB = constrain(metrics['soilB'], limits['pumpB']['lower'], limits['pumpB']['upper'])
    temp = constrain(metrics['temperature'], limits['vent']['lower'], limits['vent']['upper'])
    hour = rtc.datetime()[4]

    active['pumpA'] = soilA >= ranges['pumpA']['lower'] and soilA <= ranges['pumpA']['upper']
    active['pumpB'] = soilB >= ranges['pumpB']['lower'] and soilB <= ranges['pumpB']['upper']
    active['vent'] = temp >= ranges['vent']['lower'] and temp <= ranges['vent']['upper']
    active['lights'] = hour >= ranges['lights']['lower'] and hour <= ranges['lights']['upper']

# Рулим железом
def do():
    # pumpA.value(active['pumpA'])
    # pumpB.value(active['pumpB'])
    if active['pumpA']:
        pumpA.init()
        pumpA.duty(200)
        pumpA.freq(1000)
    else:
        pumpA.deinit()

    if active['pumpB']:
        pumpB.init()
        pumpB.duty(200)
        pumpB.freq(1000)
    else:
        pumpB.deinit()

    vent.value(active['vent'])
    lights.value(not active['lights'])


def try_sync_with_client_time(req):
    time = req.GetHeader('x-client-time')
    if time == '':
        return 
    
    # parse and validate
    time = time.split('-')
    time = tuple(int(i) for i in time if i.isdigit())
    if len(time) != 8:
        return

    print('syncing time...')
    print(time)
    rtc.init(time)

    return

@WebRoute(GET, '/metrics')
def metrics_get(srv, req):
    try_sync_with_client_time(req)
    req.Response.ReturnJSON(200, metrics)


@WebRoute(GET, '/ranges')
def thresholds_get(srv, req):
    try_sync_with_client_time(req)
    req.Response.ReturnJSON(200, ranges)


@WebRoute(POST, '/manual/start')
def manual_start(srv, req):
    global manual_control

    data = req.GetPostedJSONObject()
    if data == None:
        req.Response.ReturnJSON(400, {
            'error': 'bad request: malformed post body'
        })

    manual_control = True

    active['pumpA'] = data.get('pumpA', False)
    active['pumpB'] = data.get('pumpB', False)


    req.Response.ReturnJSON(200, {'ok': True})


@WebRoute(POST, '/manual/stop')
def manual_stop(srv, req):
    global manual_control
    manual_control = False

    active['pumpA'] = False
    active['pumpB'] = False

    req.Response.ReturnJSON(200, {'ok': True})


@WebRoute(GET, '/serial')
def serial(srv, req):
    import hw_info

    req.Response.ReturnJSON(200, {
        'serial': hw_info.SERIAL,
        'name': hw_info.NAME
    })


"""
POST /ranges
Задает пороговые значения.

Принимает JSON, состоящий из названий диапазонов и из верхних и нижниж границ.
Доступнные диапазоны: pumpA, pumpB, vent, lights

Пример:
POST /ranges
{
    "pumpA": {
        "upper": 27.1,
        "lower": 11.1
    },
    "pumpB": {
        "upper": 27.1,
        "lower": 11.1
    }
}

200 OK
{ "ok": true }

"""
@WebRoute(POST, '/ranges')
def thresholds_post(srv, req):
    data = req.GetPostedJSONObject()
    if data == None:
        req.Response.ReturnJSON(400, {
            'error': 'bad request: malformed post body'
        })

    for key, val in data.items():
        # Валидация
        # Проверяем, что есть такой порог и заданы верхнее и нижнее значение
        limit = limits.get(key)
        if limit and 'upper' in val and 'lower' in val:
            valid = ( 
                val['lower'] >= limit['lower'] and
                val['lower'] <= limit['upper'] and
                val['upper'] >= limit['lower'] and
                val['upper'] <= limit['upper'] and
                val['lower'] < val['upper']
            )
            
            if not valid:
                req.Response.ReturnJSON(400, {
                    'error': 'value out of bounds'
                })
                return
        
        # все ок, задаем значение
        ranges[key] = val

    req.Response.ReturnJSON(200, { "ok": True })

mws2.StartManaged()

# Main program loop until keyboard interrupt,
try :
    while True :
        measure()
        check()
        do()

        print(metrics)
        print(active)

        sleep(1)
except KeyboardInterrupt :
    mws2.Stop()
