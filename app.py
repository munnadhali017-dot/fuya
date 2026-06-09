# START OF FILE app.py

import os
import json
import time
import math
import requests
import threading
from datetime import timedelta
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

app = Flask(__name__, template_folder='templates')
app.secret_key = "out_of_law_super_secret_key"

# --- Configurations ---
# Modified: Using our own local distributed api.py instead of external IP
API_URL = "http://127.0.0.1:30161/player-info?uid="
USERS_DIR = 'users'

FILES = {
    'active': 'active.json', 
    'profile': 'profile.json', 
    'history': 'history.json',
    'data': 'data.json', 
    'vv': 'vv.json', 
    'live': 'bots_live_status.json',
    'check_txt': 'check.txt', 
    'targets_txt': 'targets.txt', 
    'maintenance': 'maintenance.json',
    'whitelist': 'whitelist.json',
    'info': 'info.json',
    'bot': 'bot.json',
    'members': 'members.json',
    'target_logs': 'target_logs.json',
    'bad_accounts': 'bad_accounts.json',
    'auto_index': 'auto_index.json',
    'limit_json': 'limit.json'
}

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f: 
            json.dump(default, f, indent=4)
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except: 
        return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f: 
        json.dump(data, f, indent=4)

def check_maintenance():
    return load_json(FILES['maintenance'], {"status": False, "end_time": 0}).get("status", False)

def get_user_bots(username):
    path = os.path.join(USERS_DIR, f"{username}.json")
    return load_json(path, {"bot": [], "vv": [], "failed": []})

def save_user_bots(username, data):
    path = os.path.join(USERS_DIR, f"{username}.json")
    save_json(path, data)

def init_files():
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs('account', exist_ok=True)
    
    load_json('account/a.json', list)
    load_json('account/b.json', dict)
    
    # Initialize unified limit config dynamically with default values
    load_json(FILES['limit_json'], {"max_active_limit": 1000, "max_web_target_limit": 200})
    
    for key, path in FILES.items():
        if key == 'vv': 
            load_json(path, {})
        elif key == 'live': 
            load_json(path, {})
        elif key == 'maintenance': 
            load_json(path, {"status": False, "end_time": 0})
        elif key == 'whitelist': 
            load_json(path, {"players": [], "guilds": []})
        elif key == 'auto_index':
            load_json(path, {"index": 1})
        elif key in ['profile', 'data', 'info', 'check_txt', 'targets_txt']: 
            load_json(path, {})
        elif key.endswith('.json') and key not in ['members']: 
            load_json(path, [])
    
    members = load_json(FILES['members'], [])
    if not members:
        members.append({
            "name": "System Owner",
            "pic": "902000003",
            "username": "owner",
            "password": "123",
            "role": "owner",
            "limit": 999999
        })
        save_json(FILES['members'], members)

def add_history(action, uid, name):
    history = load_json(FILES['history'], [])
    history.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action, "uid": uid, "name": name})
    save_json(FILES['history'], history[:100])

def add_target_log(action, uid, name, duration, by_user):
    logs = load_json(FILES['target_logs'], [])
    logs.insert(0, {
        "action": action,
        "uid": uid,
        "name": name,
        "duration": duration,
        "by": by_user,
        "time": int(time.time() * 1000)
    })
    save_json(FILES['target_logs'], logs[:1000])

def compile_master_bots():
    master_bot = []
    master_vv = {}
    
    for filename in os.listdir(USERS_DIR):
        if filename.endswith('.json'):
            username = filename[:-5]
            data = get_user_bots(username)
            master_bot.extend(data.get('bot', []))
            for v in data.get('vv', []):
                master_vv[str(v['uid'])] = v['password']
                
    save_json(FILES['bot'], master_bot)
    save_json(FILES['vv'], master_vv)

def get_user_usable_limit(username):
    members = load_json(FILES['members'], [])
    user = next((m for m in members if m['username'] == username), None)
    if not user: 
        return 0
    
    if user.get('role') == 'owner': 
        return 999999
    
    user_bots = get_user_bots(username)
    total_bot_json = len(user_bots.get('bot', []))
    total_vv_json = len(user_bots.get('vv', []))
    
    supported_by_bot_json = total_bot_json * 5
    usable = min(total_vv_json, supported_by_bot_json)
    
    return min(usable, user.get('limit', 0))

# ==============================================================
# SECURE ACTIVE JSON DEDUPLICATION & BOT AUTO-WHITELIST
# ==============================================================
def auto_whitelist_bots():
    """Reads online bots and auto-adds them to whitelist so we don't attack ourselves"""
    live_status = load_json(FILES['live'], {})
    whitelist = load_json(FILES['whitelist'], {"players": [], "guilds": []})
    changed = False
    
    for k, v in live_status.items():
        bot_uid = str(v.get("Game uid", "")).strip()
        if bot_uid and bot_uid not in whitelist["players"]:
            whitelist["players"].append(bot_uid)
            changed = True
            
    if changed:
        save_json(FILES['whitelist'], whitelist)

def deduplicate_active_json():
    """Ensures absolutely NO duplicate UIDs exist in active.json"""
    active_data = load_json(FILES['active'], [])
    seen_uids = set()
    new_active = []
    changed = False
    
    active_data.sort(key=lambda x: 1 if str(x.get('id', '')).startswith('auto_') else 0)
    
    for t in active_data:
        if not isinstance(t, dict) or 'uid' not in t:
            changed = True
            continue
        uid = str(t['uid']).strip()
        if uid in seen_uids:
            changed = True
            continue
        seen_uids.add(uid)
        new_active.append(t)
        
    if changed:
        save_json(FILES['active'], new_active)

def distribute_targets():
    bot_data = load_json(FILES['bot'], [])
    active_data = load_json(FILES['active'], [])
    
    user_targets = {}
    for t in active_data:
        if not isinstance(t, dict):
            continue
        uname = t.get('addedByUsername', 'owner')
        if uname not in user_targets: 
            user_targets[uname] = []
        user_targets[uname].append(t)
        
    running_uids = []
    changed_active = False
    
    for uname, targets in user_targets.items():
        usable_limit = get_user_usable_limit(uname)
        
        targets.sort(key=lambda x: (1 if str(x.get('id', '')).startswith('auto_') else 0, x.get('addTime', 0))) 
        
        for i, t in enumerate(targets):
            new_status = 'Running' if i < usable_limit else 'Paused (Need Bots)'
            if t.get('status') != new_status:
                t['status'] = new_status
                changed_active = True
                
            if new_status == 'Running':
                running_uids.append(t['uid'])

    if changed_active:
        save_json(FILES['active'], active_data)
    
    # Restructure check.txt list keys based on Bot Count
    bot_count = len(bot_data) if isinstance(bot_data, list) and len(bot_data) > 0 else 1
    distribution = {str(i): [] for i in range(1, bot_count + 1)}
    
    for index, uid in enumerate(running_uids): 
        distribution[str((index % bot_count) + 1)].append(uid)
            
    old_distribution = load_json(FILES['check_txt'], {})
    if old_distribution != distribution:
        save_json(FILES['check_txt'], distribution)

def fix_orphan_targets(active_data):
    members = load_json(FILES['members'], [])
    owner_user = next((m for m in members if m.get('role') == 'owner'), None)
    if not owner_user: 
        return False

    changed = False
    for t in active_data:
        if isinstance(t, dict) and not t.get('addedByUsername'):
            t['addedByUsername'] = owner_user['username']
            t['addedByName'] = owner_user.get('name', owner_user['username'])
            t['addedByRole'] = 'owner'
            changed = True
    return changed

def check_expired_targets():
    if check_maintenance(): 
        return
    active_data = load_json(FILES['active'], [])
    profiles = load_json(FILES['profile'], {})
    current_time = int(time.time() * 1000)
    
    new_active = []
    changed = False
    
    if fix_orphan_targets(active_data):
        changed = True
        
    for t in active_data:
        if not isinstance(t, dict):
            continue
        expire_at = t.get('expireAt')
        
        is_expired = False
        if expire_at == 'permanent':
            is_expired = False
        elif isinstance(expire_at, (int, float)):
            is_expired = int(expire_at) <= current_time
        elif isinstance(expire_at, str) and expire_at.isdigit():
            is_expired = int(expire_at) <= current_time
        else:
            is_expired = True

        if not is_expired:
            new_active.append(t)
        else:
            changed = True
            add_history("Expired", t.get('uid', 'N/A'), t.get('name', 'Unknown'))
            add_target_log("EXPIRED", t.get('uid', 'N/A'), t.get('name', 'Unknown'), t.get('duration', 'N/A'), "System")
            uid = t.get('uid')
            if uid and uid in profiles: 
                del profiles[uid]
                
    if changed:
        save_json(FILES['active'], new_active)
        save_json(FILES['profile'], profiles)
        distribute_targets()

# ==============================================================
# BACKGROUND DAEMON FOR LIVE SYNCING
# ==============================================================
def background_live_sync_task():
    """Runs every 2 seconds to ensure active.json and check.txt are perfectly synced"""
    while True:
        try:
            auto_whitelist_bots()
            deduplicate_active_json()
            check_expired_targets()
            distribute_targets()
        except Exception as e:
            pass
        time.sleep(2)

def fetch_and_parse_ff_api(uid):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    for attempt in range(1, 4):
        try:
            print(f"[*] API Attempt {attempt} - Connecting to Garena Database for UID: {uid}...")
            resp = requests.get(f"{API_URL}{uid}", headers=headers, timeout=15)
            if resp.status_code == 200:
                raw_data = resp.json()
                
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)
                    
                if "error" not in raw_data:
                    basic = raw_data.get("basicInfo") or raw_data.get("basic_info") or {}
                    clan = raw_data.get("clanBasicInfo") or raw_data.get("clan_basic_info") or {}
                    social = raw_data.get("socialInfo") or raw_data.get("social_info") or {}
                    
                    try: create_at = int(basic.get("createAt") or basic.get("create_at") or 0)
                    except: create_at = 0

                    try: last_login_at = int(basic.get("lastLoginAt") or basic.get("last_login_at") or 0)
                    except: last_login_at = 0

                    try: level = int(basic.get("level") or 0)
                    except: level = 0

                    try: liked = int(basic.get("liked") or 0)
                    except: liked = 0

                    try: head_pic = int(basic.get("headPic") or basic.get("head_pic") or 902000003)
                    except: head_pic = 902000003

                    try: banner_id = int(basic.get("bannerId") or basic.get("banner_id") or 901000001)
                    except: banner_id = 901000001

                    data = {
                        "basicInfo": {
                            "nickname": basic.get("nickname", "Unknown"), 
                            "level": level,
                            "headPic": head_pic,
                            "bannerId": banner_id,
                            "region": basic.get("region", "N/A"), 
                            "liked": liked,
                            "createAt": create_at,
                            "lastLoginAt": last_login_at
                        },
                        "clanBasicInfo": {
                            "clanName": clan.get("clanName") or clan.get("clan_name") or "No Guild", 
                            "clanId": clan.get("clanId") or clan.get("clan_id") or "N/A",
                            "captainId": clan.get("captainId") or clan.get("captain_id") or "N/A"
                        },
                        "socialInfo": {
                            "signature": social.get("signature", "Default Signature")
                        }
                    }
                    print("[✓] API data fetched and mapped successfully!")
                    return {"success": True, "data": data}
                else:
                    print(f"[-] API Error Response structure: {raw_data}")
                    return {"success": False, "msg": raw_data.get("error", "Player not found.")}
        except Exception as e:
            print(f"[!] Network exception on attempt {attempt}: {e}")
            time.sleep(1)
            
    return {"success": False, "msg": "API Network Error. Please try again."}

init_files()

@app.before_request
def check_valid_session():
    if request.endpoint in ['login', 'static']:
        return
        
    if session.get('logged_in') and 'user' in session:
        current_username = session['user'].get('username')
        current_password = session['user'].get('password')
        
        members = load_json(FILES['members'], [])
        db_user = next((m for m in members if m['username'] == current_username), None)
        
        if not db_user or db_user.get('password') != current_password:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({"error": "Session expired or password changed", "logout": True}), 401
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username').strip()
        pwd = request.form.get('password').strip()
        remember = request.form.get('remember')
        
        members = load_json(FILES['members'], [])
        user_data = next((m for m in members if m['username'] == user and m['password'] == pwd), None)
        
        if user_data:
            session['logged_in'] = True
            session['user'] = user_data
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = False
            return redirect(url_for('index'))
        else:
            return render_template('index.html', show_login=True, error="Invalid Credentials!")
    
    if session.get('logged_in') and session.get('user'): 
        return redirect(url_for('index'))
    return render_template('index.html', show_login=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in') or not session.get('user'): 
        session.clear()
        return redirect(url_for('login'))
    
    members = load_json(FILES['members'], [])
    current_username = session['user']['username']
    updated_user = next((m for m in members if m['username'] == current_username), None)
    if updated_user:
        session['user'] = updated_user
    else:
        session.clear()
        return redirect(url_for('login'))
        
    return render_template('index.html', show_login=False, current_user=session['user'])

# --- BOT MANAGEMENT ROUTES ---
@app.route('/api/my_bots', methods=['GET'])
def get_my_bots():
    if not session.get('logged_in'): 
        return jsonify({}), 401
        
    res_a = load_json('account/a.json', list)
    res_b = load_json('account/b.json', dict)
    live_bot = load_json(FILES['bot'], list)
    live_vv = load_json(FILES['vv'], dict)
    
    return jsonify({
        "provided_a": len(res_a),
        "provided_b": len(res_b),
        "provided_bot": len(live_bot),
        "provided_vv": len(live_vv),
        "bots_a": res_a,
        "bots_b": list(res_b.keys()),
        "bots_live_bot": live_bot,
        "bots_live_vv": list(live_vv.keys())
    })

# ==============================================================
# SECURED MANUAL BOT REGISTRATION (CROSS-RESERVE DUPLICATE CHECK)
# ==============================================================
@app.route('/api/add_bot', methods=['POST'])
def add_my_bot():
    if not session.get('logged_in'): 
        return jsonify({"success": False}), 401
    data = request.json
    uid = str(data.get('uid')).strip()
    pwd = str(data.get('password')).strip()
    bot_type = str(data.get('type', 'tracker')).strip() # 'tracker' or 'attacker'
    
    if not uid or not pwd:
        return jsonify({"success": False, "msg": "UID and Password cannot be empty!"})
        
    res_a = load_json('account/a.json', list)
    res_b = load_json('account/b.json', dict)
    
    in_a = any(isinstance(b, dict) and str(b.get('uid')).strip() == uid for b in res_a)
    in_b = uid in res_b
    
    if in_a or in_b:
        existing_file = "Tracker Reserve (a.json)" if in_a else "Attacker Reserve (b.json)"
        return jsonify({"success": False, "msg": f"Bot already exists in the system inside {existing_file}!"})
        
    if bot_type == 'tracker':
        res_a.append({"uid": uid, "password": pwd})
        save_json('account/a.json', res_a)
        msg = "Added successfully to Tracker Reserve (a.json)."
    else:
        res_b[uid] = pwd
        save_json('account/b.json', res_b)
        msg = "Added successfully to Attacker Reserve (b.json)."
        
    return jsonify({"success": True, "msg": msg})

# ==============================================================
# SECURED BULK BOT JSON FILE UPLOADER (CROSS-RESERVE DUPLICATE CHECK)
# ==============================================================
@app.route('/api/upload_bots', methods=['POST'])
def upload_bots():
    if not session.get('logged_in'): 
        return jsonify({"success": False}), 401
        
    file_type = request.form.get('type') # 'a' (Tracker) or 'b' (Attacker)
    if file_type not in ['a', 'b']:
        return jsonify({"success": False, "msg": "Invalid target reserve file selected."})
        
    if 'file' not in request.files:
        return jsonify({"success": False, "msg": "No file uploaded."})
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "msg": "No file selected."})
        
    try:
        raw_data = json.load(file)
    except Exception as e:
        return jsonify({"success": False, "msg": f"Invalid JSON format: {str(e)}"})
        
    added_count = 0
    duplicate_count = 0
    
    res_a = load_json('account/a.json', list)
    res_b = load_json('account/b.json', dict)
    
    existing_uids = set()
    for b in res_a:
        if isinstance(b, dict) and 'uid' in b:
            existing_uids.add(str(b.get('uid')).strip())
    for k in res_b.keys():
        existing_uids.add(str(k).strip())
        
    if file_type == 'a':
        if isinstance(raw_data, list):
            for b in raw_data:
                if isinstance(b, dict) and 'uid' in b:
                    uid = str(b.get('uid')).strip()
                    pwd = str(b.get('password', b.get('pwd', ''))).strip()
                    if uid and uid not in existing_uids:
                        res_a.append({"uid": uid, "password": pwd})
                        existing_uids.add(uid) 
                        added_count += 1
                    else:
                        duplicate_count += 1
        elif isinstance(raw_data, dict):
            for uid, pwd in raw_data.items():
                uid_str = str(uid).strip()
                if uid_str and uid_str not in existing_uids:
                    res_a.append({"uid": uid_str, "password": str(pwd).strip()})
                    existing_uids.add(uid_str)
                    added_count += 1
                else:
                    duplicate_count += 1
        save_json('account/a.json', res_a)
        msg = f"Successfully imported {added_count} Tracker bots to a.json. (Skipped {duplicate_count} duplicates present in a.json or b.json)"
        
    else:
        if isinstance(raw_data, list):
            for b in raw_data:
                if isinstance(b, dict) and 'uid' in b:
                    uid = str(b.get('uid')).strip()
                    pwd = str(b.get('password', b.get('pwd', ''))).strip()
                    if uid and uid not in existing_uids:
                        res_b[uid] = pwd
                        existing_uids.add(uid)
                        added_count += 1
                    else:
                        duplicate_count += 1
        elif isinstance(raw_data, dict):
            for uid, pwd in raw_data.items():
                uid_str = str(uid).strip()
                if uid_str and uid_str not in existing_uids:
                    res_b[uid_str] = str(pwd).strip()
                    added_count += 1
                else:
                    duplicate_count += 1
        save_json('account/b.json', res_b)
        msg = f"Successfully imported {added_count} Attacker bots to b.json. (Skipped {duplicate_count} duplicates present in a.json or b.json)"
        
    return jsonify({"success": True, "msg": msg})

@app.route('/api/remove_failed_bot', methods=['POST'])
def remove_failed_bot():
    return jsonify({"success": True})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"error": "Unauthorized"}), 401
        
    active_targets = load_json(FILES['active'], [])
    live_bots = load_json(FILES['live'], {})
    bots_list = [{"no": i+1, "name": d.get("Name", "Unknown"), "uid": d.get("Game uid", "N/A"), "status": d.get("Status", "Offline")} for i, (b, d) in enumerate(live_bots.items())]
    
    user = session['user']
    usage = sum(1 for t in active_targets if isinstance(t, dict) and t.get('addedByUsername') == user['username']) if user['role'] != 'owner' else len(active_targets)
    
    return jsonify({
        "total_targets": len(active_targets), 
        "total_bots": len(bots_list), 
        "bots": bots_list,
        "user_usage": usage
    })

@app.route('/api/user_stats', methods=['GET'])
def get_user_stats():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    members = load_json(FILES['members'], [])
    active_targets = load_json(FILES['active'], [])
    stats = {}
    for m in members:
        username = m['username']
        active_count = sum(1 for t in active_targets if isinstance(t, dict) and t.get('addedByUsername') == username)
        stats[username] = {
            "name": m.get('name', username),
            "limit": m.get('limit', 0),
            "role": m.get('role', 'admin'),
            "active": active_count
        }
    return jsonify(stats)

@app.route('/api/targets', methods=['GET'])
def get_targets():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify([]), 401
    targets = load_json(FILES['active'], [])
    profiles = load_json(FILES['profile'], {})
    for t in targets:
        if not isinstance(t, dict):
            continue
        uid = t.get('uid')
        p_data = profiles.get(uid)
        
        if not isinstance(p_data, dict):
            p_data = {}
            
        p_basic = p_data.get('basicInfo', {}) if isinstance(p_data.get('basicInfo'), dict) else {}
        p_clan = p_data.get('clanBasicInfo', {}) if isinstance(p_data.get('clanBasicInfo'), dict) else {}
        
        t['headPic'] = p_basic.get('headPic') or p_basic.get('head_pic') or '902000003'
        t['level'] = p_basic.get('level', 0)
        t['liked'] = p_basic.get('liked', 0)
        t['region'] = p_basic.get('region', 'N/A')
        t['guild'] = p_clan.get('clanName') or p_clan.get('clan_name') or "No Guild"
        t['guildId'] = str(p_clan.get('clanId') or p_clan.get('clan_id') or "N/A")
        t['leader'] = str(p_clan.get('captainId') or p_clan.get('captain_id') or "N/A")
        
        if 'addedByRole' not in t: 
            t['addedByRole'] = 'admin'
        if 'addedByName' not in t or not t['addedByName']: 
            t['addedByName'] = t.get('addedByUsername', 'System')
            
    return jsonify(targets)

# ==============================================================
# SECURED MANUAL BOT REGISTRATION (CROSS-LIMIT COMPLIANT)
# ==============================================================
@app.route('/api/target/add', methods=['POST'])
def add_target():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"success": False, "msg": "Unauthorized"})
    user = session['user']
    data = request.get_json(force=True)
    uid = str(data.get('uid')).strip()
    reason = data.get('reason', '')
    duration_str = data.get('duration', '1 day')
    
    active_data = load_json(FILES['active'], [])
    
    # DYNAMIC: Read the manual web limit on-the-fly from limit.json!
    limit_config = load_json(FILES['limit_json'], {"max_active_limit": 1000, "max_web_target_limit": 200})
    max_web_limit = limit_config.get("max_web_target_limit", 200)
    
    # Calculate W (Number of web-added targets only)
    web_count = sum(1 for t in active_data if isinstance(t, dict) and not str(t.get('id', '')).startswith('auto_'))
    
    if web_count >= max_web_limit: 
        return jsonify({"success": False, "msg": f"Global web manual target limit ({max_web_limit}) reached!"})
        
    if any(isinstance(t, dict) and str(t.get('uid')).strip() == uid for t in active_data): 
        return jsonify({"success": False, "msg": "Target already exists."})
    
    if user['role'] != 'owner':
        user_active_count = sum(1 for t in active_data if isinstance(t, dict) and t.get('addedByUsername') == user['username'])
        if user_active_count >= user.get('limit', 0):
            return jsonify({"success": False, "msg": "Your target limit is maxed. Please contact owner."})
    
    api_res = fetch_and_parse_ff_api(uid)
    if not api_res["success"]: 
        return jsonify({"success": False, "msg": api_res["msg"]})
        
    current_time = int(time.time() * 1000)
    durations = {'1 day': 86400000, '7 day': 86400000*7, '30 day': 86400000*30, 'permanent': 'permanent'}
    expire_at = 'permanent' if duration_str == 'permanent' else current_time + durations.get(duration_str, 86400000)
    
    target_name = api_res["data"]["basicInfo"].get("nickname", "Unknown")

    active_data.append({
        "id": f"t_{current_time}", "uid": uid, "name": target_name,
        "reason": reason, "duration": duration_str, "addTime": current_time, "expireAt": expire_at,
        "addedByUsername": user['username'],
        "addedByName": user.get('name', user['username']), 
        "addedByRole": user['role'],
        "status": "Running"
    })
    save_json(FILES['active'], active_data)
    
    profiles = load_json(FILES['profile'], {})
    profiles[uid] = api_res["data"]
    save_json(FILES['profile'], profiles)
    
    add_target_log("ADD", uid, target_name, duration_str, user.get('name', user['username']))
    distribute_targets()
    return jsonify({"success": True, "msg": "Protocol active on target!"})

# ==============================================================
# SECURED TARGET SWEEPER DELETION (INCLUDING AUTOBOT LEADERS)
# ==============================================================
@app.route('/api/target/delete', methods=['POST'])
def delete_target():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"success": False, "msg": "Unauthorized"})
    user = session['user']
    uid = str(request.json.get('uid')).strip()
    active_data = load_json(FILES['active'], [])
    
    target_to_del = next((t for t in active_data if isinstance(t, dict) and str(t.get('uid')).strip() == uid), None)
    if not target_to_del: 
        return jsonify({"success": False, "msg": "Target not found."})
    
    is_auto = str(target_to_del.get('id', '')).startswith('auto_')
    if user['role'] != 'owner' and target_to_del.get('addedByUsername') != user['username'] and not is_auto:
        return jsonify({"success": False, "msg": "You do not have permission to delete this target."})

    new_active = [t for t in active_data if isinstance(t, dict) and str(t.get('uid')).strip() != uid]
    save_json(FILES['active'], new_active)
    
    add_target_log("DELETE", uid, target_to_del.get('name', 'Unknown'), target_to_del.get('duration', 'N/A'), user.get('name', user['username']))
    distribute_targets()
    return jsonify({"success": True})

# --- OWNER ONLY ROUTES ---
@app.route('/api/users', methods=['GET'])
def get_users():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify([]), 401
    return jsonify(load_json(FILES['members'], []))

@app.route('/api/users/save', methods=['POST'])
def save_user():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify({"success": False, "msg": "Unauthorized"})
    data = request.json
    username = data.get('username').strip()
    password = data.get('password').strip()
    name = data.get('name', 'Unknown Admin').strip()
    pic = str(data.get('pic', '902000003')).strip()
    limit = int(data.get('limit', 0))
    role = data.get('role', 'admin')
    
    if not username or not password or not name: 
        return jsonify({"success": False, "msg": "Fields cannot be empty"})
    if username == "owner" and session['user']['username'] != "owner": 
        return jsonify({"success": False, "msg": "Cannot modify root owner."})

    members = load_json(FILES['members'], [])
    existing = next((m for m in members if m['username'] == username), None)
    
    if existing:
        existing['password'] = password
        existing['name'] = name
        existing['pic'] = pic
        existing['limit'] = limit
        existing['role'] = role
    else:
        members.append({"username": username, "password": password, "name": name, "pic": pic, "role": role, "limit": limit})
        
    save_json(FILES['members'], members)
    distribute_targets() 
    return jsonify({"success": True})

@app.route('/api/users/delete', methods=['POST'])
def delete_user():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify({"success": False, "msg": "Unauthorized"})
    username = request.json.get('username')
    
    if username == "owner" or username == session['user']['username']:
        return jsonify({"success": False, "msg": "Cannot delete owner/yourself."})
        
    members = load_json(FILES['members'], [])
    new_members = [m for m in members if m['username'] != username]
    save_json(FILES['members'], new_members)
    
    path = os.path.join(USERS_DIR, f"{username}.json")
    if os.path.exists(path): 
        os.remove(path)
    compile_master_bots()
    distribute_targets()
    
    return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify([]), 401
    return jsonify(load_json(FILES['target_logs'], []))

@app.route('/api/fetch_profile', methods=['POST'])
def fetch_profile():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json(force=True)
    uid = str(data.get('uid')).strip()
    save_profile = data.get('save', True)
    force_refresh = data.get('force', False)
    
    profiles = load_json(FILES['profile'], {})
    if not force_refresh and uid in profiles: 
        return jsonify({"success": True, "data": profiles[uid]})
        
    api_res = fetch_and_parse_ff_api(uid)
    if api_res["success"] and save_profile:
        profiles[uid] = api_res["data"]
        save_json(FILES['profile'], profiles)
    return jsonify(api_res)

@app.route('/api/info', methods=['GET'])
def get_info():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    info_data = load_json(FILES['info'], {})
    profiles = load_json(FILES['profile'], {})
    
    for uid, d in info_data.items():
        if not isinstance(d, dict):
            continue
        p_data = profiles.get(uid)
        if not isinstance(p_data, dict):
            p_data = {}
        p_basic = p_data.get('basicInfo', {}) if isinstance(p_data.get('basicInfo'), dict) else {}
        p_clan = p_data.get('clanBasicInfo', {}) if isinstance(p_data.get('clanBasicInfo'), dict) else {}
        
        d['name'] = p_basic.get('nickname', 'Unknown')
        d['headPic'] = p_basic.get('headPic', '902000003')
        d['level'] = p_basic.get('level', 0)
        d['liked'] = p_basic.get('liked', 0)
        d['region'] = p_basic.get('region', 'N/A')
        d['guild'] = p_clan.get('clanName', 'No Guild')
        d['guildId'] = str(p_clan.get('clanId', 'N/A'))
        d['guild_leader'] = str(p_clan.get('captainId', 'N/A'))
        
    return jsonify(info_data)

@app.route('/api/data', methods=['GET'])
def get_data():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    history_data = load_json(FILES['data'], {})
    profiles = load_json(FILES['profile'], {})
    
    result = {}
    for uid, leaders in history_data.items():
        if not isinstance(leaders, list):
            continue
        p_data = profiles.get(uid)
        if not isinstance(p_data, dict):
            p_data = {}
        p_basic = p_data.get('basicInfo', {}) if isinstance(p_data.get('basicInfo'), dict) else {}
        p_clan = p_data.get('clanBasicInfo', {}) if isinstance(p_data.get('clanBasicInfo'), dict) else {}
        
        formatted_leaders = []
        for l in leaders:
            try:
                l_uid, timestamp = l.split(': ', 1)
                l_profile = profiles.get(l_uid, {})
                if not isinstance(l_profile, dict):
                    l_profile = {}
                l_basic = l_profile.get('basicInfo', {}) if isinstance(l_profile.get('basicInfo'), dict) else {}
                l_clan = l_profile.get('clanBasicInfo', {}) if isinstance(l_profile.get('clanBasicInfo'), dict) else {}
                
                formatted_leaders.append({
                    "uid": l_uid, "timestamp": timestamp, "name": l_basic.get('nickname', 'Unknown'),
                    "headPic": l_basic.get('headPic', '902000003'), 
                    "guild": l_clan.get('clanName', 'No Guild'),
                    "guildId": str(l_clan.get('clanId', 'N/A'))
                })
            except: 
                pass
                
        result[uid] = {
            "leaders": formatted_leaders, "name": p_basic.get('nickname', 'Unknown'),
            "headPic": p_basic.get('headPic', '902000003'), "level": p_basic.get('level', 0),
            "liked": p_basic.get('liked', 0), "region": p_basic.get('region', 'N/A'),
            "guild": p_clan.get('clanName', 'No Guild'),
            "guildId": str(p_clan.get('clanId', 'N/A')),
            "leader": str(p_clan.get('captainId', 'N/A'))
        }
    return jsonify(result)

@app.route('/api/spam', methods=['GET'])
def get_spam():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    targets = load_json(FILES['targets_txt'], {})
    active = {str(t['uid']): t for t in load_json(FILES['active'], []) if isinstance(t, dict)}
    info = load_json(FILES['info'], {})
    
    l_to_t = {}
    for t_uid, d in info.items():
        if isinstance(d, dict):
            l_uid = d.get('leader')
            if l_uid and l_uid != "N/A": 
                l_to_t[l_uid] = t_uid
            
    result = {}
    for bot, uids in targets.items():
        if not isinstance(uids, list):
            continue
        res_list = []
        for u in uids:
            u_str = str(u)
            if u_str in active: 
                src = "Added By Web (Target)"
            elif u_str in l_to_t: 
                src = f"Leader of {l_to_t[u_str]}"
            else: 
                src = "Auto-Discovered Leader"
            res_list.append({"uid": u_str, "source": src})
        result[bot] = res_list
    return jsonify(result)

@app.route('/api/whitelist', methods=['GET'])
def get_whitelist():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify({"players": [], "guilds": []}), 401
    return jsonify(load_json(FILES['whitelist'], {"players": [], "guilds": []}))

@app.route('/api/whitelist/add', methods=['POST'])
def add_whitelist():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify({"success": False}), 401
    data = request.json
    w_type = data.get('type')
    w_id = str(data.get('id')).strip()
    wl = load_json(FILES['whitelist'], {"players": [], "guilds": []})
    if w_id not in wl[w_type]:
        wl[w_type].append(w_id)
        save_json(FILES['whitelist'], wl)
    return jsonify({"success": True})

@app.route('/api/whitelist/remove', methods=['POST'])
def remove_whitelist():
    if not session.get('logged_in') or not session.get('user') or session['user']['role'] != 'owner': 
        return jsonify({"success": False}), 401
    data = request.json
    w_type = data.get('type')
    w_id = str(data.get('id')).strip()
    wl = load_json(FILES['whitelist'], {"players": [], "guilds": []})
    if w_id in wl[w_type]:
        wl[w_type].remove(w_id)
        save_json(FILES['whitelist'], wl)
    return jsonify({"success": True})

if __name__ == '__main__':
    # Start the robust live background sync thread
    threading.Thread(target=background_live_sync_task, daemon=True).start()
    # use_reloader=False is crucial to prevent running the background thread twice!
    app.run(host='0.0.0.0', port=21292, debug=True, use_reloader=False)

# END OF FILE app.py