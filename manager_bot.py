# START OF FILE manager_bot.py

import subprocess
import time
import json
import os
import sys
import math
from threading import Thread

# Configurations
MAINTENANCE_FILE = 'maintenance.json'
RUN_TIME_HOURS = 5
MAINTENANCE_TIME_MINS = 10

# Process holders
p_app = None
p_main = None
p_info = None
p_api = None # Dedicated process holder for api.py

# Local DB Configurations
BAD_ACCS_FILE = 'bad_accounts.json'
BOT_FILE = 'bot.json'
VV_FILE = 'vv.json'
CHECK_FILE = 'check.txt'
LIVE_FILE = 'bots_live_status.json'
TARGETS_TXT = 'targets.txt'

# Reserve Folder System
ACCOUNT_DIR = 'account'
RESERVE_A = os.path.join(ACCOUNT_DIR, 'a.json') # Backup Tracker list (bot.json format)
RESERVE_B = os.path.join(ACCOUNT_DIR, 'b.json') # Backup Attack dict (vv.json format)

def load_json(path, default):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default(), f, indent=4)
        return default()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default()

def save_json(path, data):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# ==========================================================
# === PURE AUTO-SCALING (STABLE COLD-BOOT ACTIVE BASE) ===
# ==========================================================
def reconcile_and_scale_bots():
    """Calculates target lists based on LAST list size, moves bots directly from account/ to live"""
    try:
        # --- 1. TRACKER LOGIC (bot.json vs check.txt) ---
        check_data = load_json(CHECK_FILE, dict)
        n_check = 0
        if isinstance(check_data, dict):
            for v in check_data.values():
                if isinstance(v, list): n_check += len(v)
        elif isinstance(check_data, list):
            n_check = len(check_data)

        # Modified: Base tracker is always at least 1 so bot.json is never empty on cold boot
        needed_trackers = max(1, (n_check // 5) + 1 if n_check > 0 else 0)
        live_trackers = load_json(BOT_FILE, list)

        if len(live_trackers) < needed_trackers:
            deficit = needed_trackers - len(live_trackers)
            reserve_a = load_json(RESERVE_A, list)
            
            if reserve_a:
                bots_to_move = reserve_a[:deficit]
                reserve_a = reserve_a[deficit:] 
                live_trackers.extend(bots_to_move)
                
                save_json(RESERVE_A, reserve_a)
                save_json(BOT_FILE, live_trackers)
                print(f"[Scale-Up] Tracker added! Total: {len(live_trackers)}")
            else:
                pass


        # --- 2. ATTACKER LOGIC (vv.json vs targets.txt) ---
        targets_data = load_json(TARGETS_TXT, dict)
        n_targets = 0
        if isinstance(targets_data, dict):
            for v in targets_data.values():
                if isinstance(v, list): n_targets += len(v)
        elif isinstance(targets_data, list):
            n_targets = len(targets_data)

        # Modified: Base attacker is always at least 1 so vv.json is never empty on cold boot
        needed_attackers = max(1, (n_targets // 2) + 1 if n_targets > 0 else 0)
        live_attackers = load_json(VV_FILE, dict)

        if len(live_attackers) < needed_attackers:
            deficit = needed_attackers - len(live_attackers)
            reserve_b = load_json(RESERVE_B, dict)
            
            if reserve_b:
                keys_to_move = list(reserve_b.keys())[:deficit]
                moved_count = 0
                
                for k in keys_to_move:
                    live_attackers[k] = reserve_b.pop(k)
                    moved_count += 1
                
                save_json(RESERVE_B, reserve_b)
                save_json(VV_FILE, live_attackers)
                print(f"[Scale-Up] Attacker added! Total: {len(live_attackers)}")
            else:
                pass

    except Exception as e:
        print(f"[!] Error in reconcile_and_scale_bots: {e}")

# ===================================================
# === BAD ACCOUNTS & SELF-HEALING LOGIC ===
# ===================================================
def process_bad_accounts():
    """Removes bad accounts from live files. Next scaling loop will auto-replace them."""
    try:
        bad_accs = load_json(BAD_ACCS_FILE, list)
        if not bad_accs:
            return
            
        save_json(BAD_ACCS_FILE, [])

        live_trackers = load_json(BOT_FILE, list)
        live_attackers = load_json(VV_FILE, dict)
        live_status = load_json(LIVE_FILE, dict)
        
        changed_bot = False
        changed_vv = False
        changed_status = False

        for bad in bad_accs:
            uid = str(bad.get('uid')).strip()
            source = str(bad.get('source', '')).strip()

            if source == 'bot.json':
                original_len = len(live_trackers)
                live_trackers = [b for b in live_trackers if isinstance(b, dict) and str(b.get('uid')).strip() != uid]
                if len(live_trackers) < original_len:
                    changed_bot = True

            elif source == 'vv.json':
                if uid in live_attackers:
                    del live_attackers[uid]
                    changed_vv = True

            keys_to_delete = []
            for k, v in live_status.items():
                if str(v.get('Game uid')) == uid or str(v.get('Id')) == uid:
                    keys_to_delete.append(k)
            for k in keys_to_delete:
                del live_status[k]
                changed_status = True

        if changed_bot: save_json(BOT_FILE, live_trackers)
        if changed_vv: save_json(VV_FILE, live_attackers)
        if changed_status: save_json(LIVE_FILE, live_status)
        
        if changed_bot or changed_vv:
            print(f"[Self-Heal] Bad accounts purged. Current Trackers: {len(live_trackers)}, Attackers: {len(live_attackers)}")
            
    except Exception as e:
        print(f"[!] Error in process_bad_accounts: {e}")

def daemon_watcher():
    """1-Second daemon thread for moving bots and purging bad ones"""
    while True:
        try:
            process_bad_accounts()
            reconcile_and_scale_bots()
        except Exception as e:
            pass
        time.sleep(1)

def set_maintenance(status, duration_secs=0):
    end_time = int(time.time() + duration_secs) if status else 0
    data = {"status": status, "end_time": end_time}
    with open(MAINTENANCE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    status_str = "ON" if status else "OFF"
    print(f"[*] Maintenance mode turned {status_str}")

def start_process(script_name):
    print(f"[+] Starting {script_name}...")
    return subprocess.Popen([sys.executable, '-u', script_name])

def stop_process(proc, script_name):
    if proc and proc.poll() is None:
        print(f"[-] Stopping {script_name}...")
        proc.terminate()
        proc.wait()

def main():
    global p_app, p_main, p_info, p_api
    
    print("=========================================")
    print("    OUT OF LAW - SUPERVISOR ACTIVE       ")
    print("=========================================\n")
    
    set_maintenance(False)

    # Ensure required files exist
    load_json(RESERVE_A, list)
    load_json(RESERVE_B, dict)
    load_json(BOT_FILE, list)
    load_json(VV_FILE, dict)

    # Start watcher loop thread
    watcher_thread = Thread(target=daemon_watcher, daemon=True)
    watcher_thread.start()
    print("[✓] Pure Auto-Scaler Active (1s Loop running).")

    # 🚀 API process started first so it binds to port 30161 before other apps call it
    p_api = start_process('api.py')
    time.sleep(3)
    p_app = start_process('app.py')
    time.sleep(3)
    p_info = start_process('info.py')
    time.sleep(2)
    p_main = start_process('main.py')
    
    print("\n[✓] ALL SYSTEMS ARE ONLINE AND RUNNING!")

    run_time_secs = RUN_TIME_HOURS * 3600
    maintenance_time_secs = MAINTENANCE_TIME_MINS * 60

    try:
        while True:
            print(f"\n[*] Next maintenance scheduled in {RUN_TIME_HOURS} hours.")
            time.sleep(run_time_secs)

            print("\n[!] === INITIATING SCHEDULED MAINTENANCE ===")
            set_maintenance(True, maintenance_time_secs)
            
            stop_process(p_main, 'main.py')
            stop_process(p_info, 'info.py')
            stop_process(p_api, 'api.py') # Rest api.py during scheduled maintenance
            
            print(f"[*] System is resting... Waiting for {MAINTENANCE_TIME_MINS} minutes.")
            time.sleep(maintenance_time_secs)

            print("\n[!] === ENDING MAINTENANCE ===")
            set_maintenance(False)
            
            p_api = start_process('api.py')
            time.sleep(3)
            p_info = start_process('info.py')
            time.sleep(2)
            p_main = start_process('main.py')
            
            print("[✓] SYSTEM RESTORED SUCCESSFULLY!")

    except KeyboardInterrupt:
        print("\n\n[!] Manager Bot stopped manually. Cleaning up processes...")
        stop_process(p_app, 'app.py')
        stop_process(p_info, 'info.py')
        stop_process(p_main, 'main.py')
        stop_process(p_api, 'api.py') # Shutdown api.py safely on manual stop
        set_maintenance(False)
        print("[✓] All processes closed safely. Exiting.")

if __name__ == "__main__":
    main()

# END OF FILE manager_bot.py
