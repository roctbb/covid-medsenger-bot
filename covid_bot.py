import datetime
import time
from threading import Thread
from flask import Flask, request, render_template
import json
import requests
import hashlib, uuid
from config import *
import threading
import datetime

app = Flask(__name__)
contracts = {}


def load():
    global contracts
    try:
        with open('data.json', 'r') as f:
            contracts = json.load(f)
    except:
        save()


def save():
    global contracts
    with open('data.json', 'w') as f:
        json.dump(contracts, f)


def check_digit(number):
    try:
        int(number)
        return True
    except:
        return False


load()

@app.route('/status', methods=['POST'])
def status():
    data = request.json

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    load()

    answer = {
        "is_tracking_data": True,
        "supported_scenarios": [],
        "tracked_contracts": [int(contract_id) for contract_id in contracts]
    }

    return json.dumps(answer)

@app.route('/init', methods=['POST'])
def init():
    data = request.json

    load()

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    contract_id = str(data['contract_id'])
    contracts[contract_id] = {
        "mode": "once",
        "last_push": 0
    }
    save()

    return 'ok'


@app.route('/remove', methods=['POST'])
def remove():
    data = request.json

    load()

    if data['api_key'] != APP_KEY:
        return 'invalid key'

    contract_id = str(data['contract_id'])
    if contract_id in contracts:
        del contracts[contract_id]
    save()

    return 'ok'


@app.route('/settings', methods=['GET'])
def settings():
    key = request.args.get('api_key', '')

    load()

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    contract_id = request.args.get('contract_id', '')

    if contract_id not in contracts:
        return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."

    return render_template('settings.html', contract=contracts[contract_id])


@app.route('/', methods=['GET'])
def index():
    return 'waiting for the thunder!'


@app.route('/settings', methods=['POST'])
def setting_save():
    key = request.args.get('api_key', '')
    load()

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."

    contract_id = request.args.get('contract_id', '')
    if contract_id not in contracts:
        return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."

    contracts[contract_id]['mode'] = request.form.get('mode', 'once')
    save()

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
            "action_deadline": int(time.time()) + 6 * 60 * 60
        }
    }
    try:
        requests.post(MAIN_HOST + '/api/agents/message', json=data)
        print('sent to ' + contract_id)
    except Exception as e:
        print('connection error', e)

    save()


def send_warning(contract_id, a):
    data1 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "Мы направили уведомление о симптомах вашему лечащему врачу, он свяжется с вами в ближайшее время.",
            "is_urgent": True,
            "only_patient": True,
        }
    }

    data2 = {
        "contract_id": contract_id,
        "api_key": APP_KEY,
        "message": {
            "text": "У пациента наблюдаются вероятные симптомы COVID 19 ({}).".format(', '.join(a)),
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

def tasks():
    load()
    now = datetime.datetime.now()
    print(now.hour)
    if now.hour == 21:
        for contract_id in contracts:
            if contracts[contract_id]['mode'] in ['once', 'double', 'triple'] and time.time() - contracts[contract_id]['last_push'] > 60 * 60:
                send(contract_id)
                contracts[contract_id]['last_push'] = time.time()
    if now.hour == 10:
        for contract_id in contracts:
            if contracts[contract_id]['mode'] in ['double', 'triple'] and time.time() - contracts[contract_id]['last_push'] > 60 * 60:
                send(contract_id)
                contracts[contract_id]['last_push'] = time.time()
    if now.hour == 15:
        for contract_id in contracts:
            if contracts[contract_id]['mode'] in ['triple'] and time.time() - contracts[contract_id]['last_push'] > 60 * 60:
                send(contract_id)
                contracts[contract_id]['last_push'] = time.time()
    save()

def sender():
    global contracts
    while True:
        tasks()
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
    load()
    contract_id = str(request.args.get('contract_id', ''))

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."
    if contract_id not in contracts:
        return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."

    return render_template('measurement.html')


@app.route('/frame', methods=['POST'])
def action_save():
    key = request.args.get('api_key', '')
    load()
    contract_id = request.args.get('contract_id', '')

    if key != APP_KEY:
        return "<strong>Некорректный ключ доступа.</strong> Свяжитесь с технической поддержкой."
    if contract_id not in contracts:
        return "<strong>Запрашиваемый канал консультирования не найден.</strong> Попробуйте отключить и заного подключить интеллектуального агента. Если это не сработает, свяжитесь с технической поддержкой."

    warnings = []

    if request.form.get('temperature', ''):
        warnings.append('температура выше 38')
    if request.form.get('ad', ''):
        warnings.append('давление выходит за рамки нормы')
    if request.form.get('pulse', ''):  # боль в горле
        warnings.append('пульс в покое выходит за рамки нормы')
    if request.form.get('snuffle', ''):  # насморк
        warnings.append('кашель с кровью в мокроте')
    if request.form.get('sputum', ''):  # мокрота
        warnings.append('насморк с примесью крови и гнойными выделениями')
    if request.form.get('weakness', ''):
        warnings.append('сильная слабость')
    if request.form.get('myalgia', ''):
        warnings.append('боль в мышцах')
    if request.form.get('tightness', ''):
        warnings.append('тяжесть в грудной клетке')
    if request.form.get('dyspnea', ''):  # отдышка
        warnings.append('отдышка')

    if len(warnings) != 0:
        send_warning(contract_id, warnings)

    save()

    return """
    <strong>Спасибо, окно можно закрыть</strong><script>window.parent.postMessage('close-modal-success','*');</script>
    """

if __name__ == "__main__":
    t = Thread(target=sender)
    t.start()

    app.run(port=PORT, host=HOST)
