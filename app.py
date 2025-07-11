from flask import Flask, request
from datetime import datetime, timedelta
import threading
import time
import json
import os
import requests
import httpx

app = Flask(__name__)
jwt_token = None
key2 = "projects_xxx_3ei93k_codex_xdfox"
STORAGE_FILE = 'uid_storage.json'
storage_lock = threading.Lock()

# 🟢 جلب التوكن
def get_jwt_token():
    global jwt_token
    try:
        url = "https://token-free.vercel.app/get?uid=3823924635&password=E6304F7F5103865FC221A1F309E07F04ABC95991CEB470EBF15B7E80045AD0EC"
        res = httpx.get(url)
        data = res.json()
        jwt_token = data.get('token')
        if jwt_token:
            print("✅ JWT Token:", jwt_token)
        else:
            print("⚠️ Token not found in response")
    except Exception as e:
        print("❌ Error getting JWT:", e)

# 🔄 تجديد التوكن كل 8 ساعات
def token_updater():
    while True:
        get_jwt_token()
        time.sleep(8 * 3600)

# 🧠 استخراج اسم اللاعب من API
def get_player_name(uid):
    try:
        res = requests.get(f"https://get-info-ishak.vercel.app/accinfo?uid={uid}")
        if res.status_code == 200:
            data = res.json()
            name = data.get("basicInfo", {}).get("nickname")
            if name:
                return name
    except Exception as e:
        print("⚠️ خطأ أثناء استخراج الاسم:", e)
    return "غير معروف"

# 📁 تأكد من وجود ملف التخزين
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

# 🧹 حذف المنتهية صلاحيتهم
def cleanup_expired_uids():
    while True:
        with storage_lock:
            uids = load_uids()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expired = [uid for uid, exp in uids.items() if exp != "permanent" and exp <= now]
            for uid in expired:
                if jwt_token:
                    requests.get(f"https://remevid.vercel.app/remove_friend?token={jwt_token}&id={uid}")
                print("🗑️ حذف:", uid)
                del uids[uid]
            save_uids(uids)
        time.sleep(1)

# ➕ إضافة UID
@app.route('/add_uid', methods=['GET'])
def add_uid():
    uid = request.args.get('uid')
    time_value = request.args.get('time')
    time_unit = request.args.get('type')
    permanent = request.args.get('permanent', 'false').lower() == 'true'

    if not uid:
        return "❌ يرجى تحديد uid", 400

    player_name = get_player_name(uid)

    if permanent:
        expiration = "permanent"
        if jwt_token:
            requests.get(f"https://add-taupe.vercel.app/adding_friend?token={jwt_token}&id={uid}")
        response = (
            f"✅ تمت إضافة اللاعب {player_name}\n"
            f"🆔 UID: {uid}\n"
            f"🟢 هذا اللاعب مضاف بشكل دائم ولن تنتهي صلاحيته."
        )
    else:
        if not time_value or not time_unit:
            return "❌ الوقت أو النوع غير محدد", 400
        try:
            time_value = int(time_value)
        except:
            return "❌ قيمة الوقت غير صالحة", 400

        now = datetime.now()
        if time_unit == 'days':
            expire_at = now + timedelta(days=time_value)
        elif time_unit == 'months':
            expire_at = now + timedelta(days=time_value * 30)
        elif time_unit == 'years':
            expire_at = now + timedelta(days=time_value * 365)
        elif time_unit == 'seconds':
            expire_at = now + timedelta(seconds=time_value)
        else:
            return "❌ النوع غير مدعوم", 400

        expiration = expire_at.strftime('%Y-%m-%d %H:%M:%S')
        if jwt_token:
            requests.get(f"https://add-taupe.vercel.app/adding_friend?token={jwt_token}&id={uid}")

        remaining = expire_at - now
        remaining_dict = {
            'days': remaining.days,
            'hours': remaining.seconds // 3600,
            'minutes': (remaining.seconds % 3600) // 60,
            'seconds': remaining.seconds % 60
        }

        response = (
            f"✅ تمت إضافة اللاعب {player_name}\n"
            f"🆔 UID: {uid}\n"
            f"⏳ الوقت المتبقي:\n"
            f"الأيام: {remaining_dict['days']}\n"
            f"الساعات: {remaining_dict['hours']}\n"
            f"الدقائق: {remaining_dict['minutes']}\n"
            f"الثواني: {remaining_dict['seconds']}"
        )

    with storage_lock:
        uids = load_uids()
        uids[uid] = expiration
        save_uids(uids)

    return response, 200

# 🕒 عرض الوقت المتبقي
@app.route('/get_time/<string:uid>', methods=['GET'])
def get_time(uid):
    with storage_lock:
        uids = load_uids()
        if uid not in uids:
            return "❌ UID غير موجود", 404

        player_name = get_player_name(uid)
        exp = uids[uid]

        if exp == "permanent":
            return (
                f"✅ حالة اللاعب {player_name}\n"
                f"🆔 UID: {uid}\n"
                f"🟢 هذا UID دائم ولن تنتهي صلاحيته."
            )

        expire_at = datetime.strptime(exp, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        if now > expire_at:
            return "❌ انتهت صلاحية هذا UID", 400

        remaining = expire_at - now
        remaining_dict = {
            'days': remaining.days,
            'hours': remaining.seconds // 3600,
            'minutes': (remaining.seconds % 3600) // 60,
            'seconds': remaining.seconds % 60
        }

        return (
            f"✅ حالة اللاعب {player_name}\n"
            f"🆔 UID: {uid}\n"
            f"⏳ الوقت المتبقي:\n"
            f"الأيام: {remaining_dict['days']}\n"
            f"الساعات: {remaining_dict['hours']}\n"
            f"الدقائق: {remaining_dict['minutes']}\n"
            f"الثواني: {remaining_dict['seconds']}"
        )

# 📋 عرض كل UIDات
@app.route('/list_all_uids', methods=['GET'])
def list_uids():
    with storage_lock:
        uids = load_uids()
        if not uids:
            return "📭 لا توجد UIDات مسجلة"

        output = "📋 قائمة UIDات:\n"
        for uid, exp in uids.items():
            status = "🟢 دائم" if exp == "permanent" else f"⏳ ينتهي في {exp}"
            output += f"• {uid} - {status}\n"
        return output

# 🧹 مسح الكل
@app.route('/clear_all', methods=['GET'])
def clear_all():
    with storage_lock:
        save_uids({})
    return "🧹 تم مسح جميع UIDات بنجاح!", 200

# ⏳ تشغيل الخدمات
if __name__ == '__main__':
    ensure_storage_file()
    app.run(host='0.0.0.0', port=50022, debug=False)