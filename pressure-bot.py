import datetime
import time
from threading import Thread
from flask import Flask, request, render_template
import json
import requests
import hashlib, uuid
from config import *
import threading

app = Flask(__name__)
contracts = set()
last_push = 0

def delayed(delay, f, args):
    timer = threading.Timer(delay, f, args=args)
    timer.start()


def load():
    global contracts
    try:
        with open('data.json', 'r') as f:
            contracts = set(json.load(f))
    except:
        save()

def save():
    global contracts
    with open('data.json', 'w') as f:
        json.dump(list(contracts), f)

def check_digit(number):
    try:
        int(number)
        return True
    except:
        return False


load()

def delayed(delay, f, args):
    timer = threading.Timer(delay, f, args=args)
    timer.start()

def check_digit(number):
    try:
        int(number)
        return True
    except:
        return False

@app.route('/init', methods=['POST'])
def init():
    data = request.json

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    contract_id = str(data['contract_id'])
    contracts.add(contract_id)
    save()

    return 'ok'


@app.route('/remove', methods=['POST'])
def remove():
    data = request.json

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    contract_id = str(data['contract_id'])
    contracts.discard(contract_id)
    save()

    return 'ok'


@app.route('/settings', methods=['GET'])
def settings():
    key = request.args.get('api_key', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    return "Этот интеллектуальный агент не требует настройки."


@app.route('/', methods=['GET'])
def index():
    return 'waiting for the thunder!'


@app.route('/settings', methods=['POST'])
def setting_save():
    key = request.args.get('api_key', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    return """
        <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
        """


def send(contract_id):
    data = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "Пожалуйста, заполните анкету по симптоматике COVID-19.",
            "action_link": "frame",
            "action_name": "Заполнить анкету",
            "action_onetime": True,
            "only_doctor": False,
            "only_patient": True,
        }
    }
    try:
        requests.post(MAIN_HOST + '/api/agents/message', json=data)
        print('sent to ' + contract_id)
    except Exception as e:
        print('connection error', e)

    save()


def send_warning(contract_id, a, b):
    data1 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "У вас наблюдаются вероятные симптому COVID-19. Мы уже направили уведомление вашему врачу.".format(
                a, b),
            "is_urgent": True,
            "only_patient": True,
        }
    }

    data2 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "У пациента наблюдаются сиптомы COVID 19 ({}).".format(', '.join(a)),
            "is_urgent": True,
            "only_doctor": True,
            "need_answer": True
        }
    }
    try:
        print('sending')
        result1 = requests.post(MAIN_HOST + '/api/agents/message', json=data1)
        result1 = requests.post(MAIN_HOST + '/api/agents/message', json=data2)
    except Exception as e:
        print('connection error', e)


def sender():
    while True:
        if time.time() - last_push > 60 * 60 * 24:
            for contract_id in contracts:
                send(contract_id)
        time.sleep(60)


@app.route('/message', methods=['POST'])
def save_message():
    data = request.json
    key = data['api_key']

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    return "ok"


@app.route('/frame', methods=['GET'])
def action():
    key = request.args.get('api_key', '')
    contract_id = str(request.args.get('contract_id', ''))

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."
    if contract_id not in contracts:
        return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."

    return render_template('measurement.html')


@app.route('/frame', methods=['POST'])
def action_save():
    key = request.args.get('api_key', '')
    contract_id = request.args.get('contract_id', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."
    if contract_id not in contracts:
        return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."

    warnings = []

    if request.form.get('temperature', 'normal') != 'normal':
        warnings.append('температура выше 38')
    if request.form.get('ad', 'normal') != 'normal':
        warnings.append('давление выходит за рамки нормы')
    if request.form.get('sorethroat', 'normal') != 'normal': # боль в горле
        warnings.append('боль в горле')
    if request.form.get('snuffle', 'normal'): # насморк
        warnings.append('кашель')
    if request.form.get('sputum', 'normal'): # мокрота
        warnings.append('насморк')
    if request.form.get('weakness', 'normal'):
        warnings.append('слабость')
    if request.form.get('myalgia', 'normal'):
        warnings.append('боль в мышцах')
    if request.form.get('tightness', 'normal'):
        warnings.append('тяжесть в грудной клетке')
    if request.form.get('dyspnea', 'normal'): # отдышка
        warnings.append('отдышка')

    if len(warnings) != 0:
        delayed(1, send_warning, [contract_id, warnings])

    save()

    return """
    <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
    """


t = Thread(target=sender)
t.start()
actions = [{
    "name": "График давления",
    "link": HOST + "/graph"
}]
print(json.dumps(actions))
app.run(port='9091', host='0.0.0.0')
