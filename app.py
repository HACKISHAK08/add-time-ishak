from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import json
import os
import threading
import time
import requests
import httpx
from threading import Thread  

app = Flask(__name__)

####################################
key2 = "projects_xxx_3ei93k_codex_xdfox"
jwt_token = None  

def get_jwt_token():
    global jwt_token
    url = "https://project-token-ishak.vercel.app/get?uid=3823924635&password=E6304F7F5103865FC221A1F309E07F04ABC95991CEB470EBF15B7E80045AD0EC"
    try:
        response = httpx.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                jwt_token = data['token']
                print(jwt_token)
            else:
                print("Failed to get JWT token:", data)
        else:
            print("Failed to get JWT token, status code:", response.status_code)
    except httpx.RequestError as e:
        print(f"Request error: {e}")

def token_updater():
    while True:
        get_jwt_token()
        time.sleep(8 * 3600)

token_thread = Thread(target=token_updater, daemon=True)
token_thread.start()

####################################
STORAGE_FILE = 'uid_storage.json'
storage_lock = threading.Lock()

def ensure_storage_file():
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, 'w') as file:
            json.dump({}, file)

def load_uids():
    ensure_storage_file()
    with open(STORAGE_FILE, 'r') as file:
        return json.load(file)

def save_uids(uids):
    ensure_storage_file()
    with open(STORAGE_FILE, 'w') as file:
        json.dump(uids, file, default=str)

def cleanup_expired_uids():
    while True:
        with storage_lock:
            uids = load_uids()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expired_uids = [uid for uid, exp_time in uids.items() if exp_time != 'permanent' and exp_time <= current_time]
            for uid in expired_uids:
                if jwt_token:  
                    requests.get(f"https://remevid-isso.vercel.app/remove_friend?token={jwt_token}&id={uid}")
                del uids[uid]
                print(f"Deleted expired UID: {uid}")
            save_uids(uids)
        time.sleep(1)

cleanup_thread = threading.Thread(target=cleanup_expired_uids, daemon=True)
cleanup_thread.start()

@app.route('/add_uid', methods=['GET'])
def add_uid():
    uid = request.args.get('uid')
    time_value = request.args.get('time')
    time_unit = request.args.get('type')
    permanent = request.args.get('permanent', 'false').lower() == 'true'

    if not uid:
        return jsonify({'error': 'Missing parameter: uid'}), 400

    if permanent:
        expiration_time = 'permanent'
        if jwt_token: 
            requests.get(f"https://add-isso.vercel.app/adding_friend?token={jwt_token}&id={uid}")
    else:
        if not time_value or not time_unit:
            return jsonify({'error': 'Missing parameters: time or unit'}), 400
        try:
            time_value = int(time_value)
        except ValueError:
            return jsonify({'error': 'Invalid time value. Must be an integer.'}), 400

        current_time = datetime.now()
        if time_unit == 'days':
            expiration_time = current_time + timedelta(days=time_value)
        elif time_unit == 'months':
            expiration_time = current_time + timedelta(days=time_value * 30) 
        elif time_unit == 'years':
            expiration_time = current_time + timedelta(days=time_value * 365)
        elif time_unit == 'seconds':
            expiration_time = current_time + timedelta(seconds=time_value)
        else:
            return jsonify({'error': 'Invalid type. Use "days", "months", "years", or "seconds".'}), 400
        expiration_time = expiration_time.strftime('%Y-%m-%d %H:%M:%S')
        if jwt_token:
            requests.get(f"https://add-isso.vercel.app/adding_friend?token={jwt_token}&id={uid}")

    with storage_lock:
        uids = load_uids()
        uids[uid] = expiration_time
        save_uids(uids)

    return jsonify({
        'uid': uid,
        'expires_at': expiration_time if not permanent else 'never'
    })

@app.route('/get_time/<string:uid>', methods=['GET'])
def check_time(uid):
    with storage_lock:
        uids = load_uids()
        if uid not in uids:
            return jsonify({'error': 'UID not found'}), 404
        expiration_time = uids[uid]        
        if expiration_time == 'permanent':
            return jsonify({           
                'uid': uid,
                'status': 'permanent',
                'message': 'This UID will never expire.'
            })
        expiration_time = datetime.strptime(expiration_time, '%Y-%m-%d %H:%M:%S')
        current_time = datetime.now()
        if current_time > expiration_time:
            return jsonify({'error': 'UID has expired'}), 400
        remaining_time = expiration_time - current_time
        days = remaining_time.days
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return jsonify({
                'uid': uid,
                'remaining_time': {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds
            }
        })

if __name__ == '__main__':
    ensure_storage_file()
    app.run(host='0.0.0.0', port=50022, debug=False)