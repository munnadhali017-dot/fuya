# START OF FILE main.py

import os, psutil, sys, jwt, json, binascii, time, urllib3, xKEys, base64, re, socket, threading
import asyncio, gc, random, aiohttp
from io import BytesIO
from protobuf_decoder.protobuf_decoder import Parser
from xC4 import *
from google.protobuf.timestamp_pb2 import Timestamp
from threading import Thread, Lock
import datetime as dt_mod

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# === ZOMBIE PROCESS KILLER ===
# ==========================================
def Kill_Zombie_Processes():
    """Kills any old instances of main.py to prevent connection conflicts"""
    current_pid = os.getpid()
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = p.info['cmdline']
            if cmd and 'main.py' in ' '.join(cmd) and 'python' in ' '.join(cmd).lower():
                if p.info['pid'] != current_pid:
                    print(f"[!] Killing Zombie main.py (PID: {p.info['pid']})")
                    p.kill()
        except: pass

Kill_Zombie_Processes()

# ==========================================
# === GLOBAL STORAGE & DYNAMIC SYNC ===
# ==========================================
ATTACK_TARGETS_DICT = {} 
TARGET_FILE = "targets.txt"
LIVE_STATUS_FILE = "bots_live_status.json" 

BOT_STATUS_DATA = {}
STATUS_LOCK = Lock()

TOTAL_BOTS_DICT = {} 

HTTP_SESSION = None

async def get_http_session():
    global HTTP_SESSION
    if HTTP_SESSION is None:
        connector = aiohttp.TCPConnector(ssl=False, limit=0)
        HTTP_SESSION = aiohttp.ClientSession(connector=connector)
    return HTTP_SESSION

# ==========================================
# === HELPER FUNCTIONS ===
# ==========================================
def save_bad_account(uid, source="vv.json", reason="Login Failed"):
    """Safe bad account saver with 5x retries to bypass Windows file locks"""
    path = 'bad_accounts.json'
    for _ in range(5):
        try:
            bad_data = []
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    try: bad_data = json.load(f)
                    except: bad_data = []
            bad_data.append({
                "uid": str(uid),
                "source": source,
                "reason": reason,
                "time": dt_mod.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(bad_data, f, indent=4)
            break 
        except:
            time.sleep(0.5) 

def Update_Bot_Status(bot_id, status_msg, uid="Unknown", nickname="Unknown", vv_key="Unknown"):
    with STATUS_LOCK:
        BOT_STATUS_DATA[str(bot_id)] = {
            "Id": vv_key,
            "Name": nickname,
            "Status": status_msg,
            "Timestamp": dt_mod.datetime.now().strftime("%H:%M:%S"),
            "Game uid": uid
        }

# ========================================================
# 🚀 SECURED LINUX ATOMIC SWAP LIVE STATUS WRITER
# ========================================================
def Live_Status_Writer():
    while True:
        try:
            with STATUS_LOCK:
                data_to_save = BOT_STATUS_DATA.copy()
            
            temp_file = LIVE_STATUS_FILE + ".tmp"
            # Write to temporary file first
            with open(temp_file, "w", encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4)
                
            # Perform Atomic Swap in Linux (Guarantees zero-collision reads by app.py)
            os.replace(temp_file, LIVE_STATUS_FILE)
        except Exception as e:
            pass
        time.sleep(4) # Writes status updates every 4 seconds stably

def ResTarTinG():
    print('\n [System] Restarting System Internally... ! ')
    try:
        p = psutil.Process(os.getpid())
        for f in p.open_files():
            try: os.close(f.fd)
            except: pass
        for conn in p.net_connections(kind='inet'):
            try: os.close(conn.fd)
            except: pass
    except: pass
    time.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

def AuTo_ResTartinG():
    while True:
        time.sleep(6 * 60 * 60)
        ResTarTinG()

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint": field_data['data'] = result.data
        elif result.wire_type == "string": field_data['data'] = result.data
        elif result.wire_type == "bytes": field_data['data'] = result.data
        elif result.wire_type == 'length_delimited': field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        return json.dumps(Fix_PackEt(parsed_results))
    except: return None

# ==========================================
# === HIGH SPEED ASYNC LOGIN FUNCTIONS ===
# ==========================================
async def G_AccEss(U, P):
    session = await get_http_session()
    UrL = "https://100067.connect.garena.com/oauth/guest/token/grant"
    HE = {
        "Host": "100067.connect.garena.com", 
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; SM-A515F Build/QP1A.190711.020)", 
        "Content-Type": "application/x-www-form-urlencoded", 
        "Accept-Encoding": "gzip", 
        "Connection": "keep-alive"
    }
    dT = {
        "uid": f"{U}", "password": f"{P}", "response_type": "token", 
        "client_type": "2", "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3", 
        "client_id": "100067"
    }
    try:
        async with session.post(UrL, headers=HE, data=dT, timeout=10) as R:
            if R.status == 200:
                data = await R.json()
                return data["access_token"], data["open_id"]
    except: pass
    return None, None

async def MajorLoGin(PyL):
    session = await get_http_session()
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    headers = {
        "X-Unity-Version": "2018.4.11f1", 
        "ReleaseVersion": "OB53", 
        "Content-Type": "application/x-www-form-urlencoded", 
        "X-GA": "v1 1", 
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; SM-A515F Build/QP1A.190711.020)", 
        "Host": "loginbp.ggblueshark.com", 
        "Connection": "Keep-Alive", 
        "Accept-Encoding": "gzip"
    }
    try:
        async with session.post(url, data=PyL, headers=headers, timeout=15) as response:
            if response.status in [200, 201]:
                raw_data = await response.read()
                return raw_data.hex()
    except Exception: pass
    return None

# ==========================================
# === FF CLIENT CLASS ===
# ==========================================
class FF_CLient:
    def __init__(self, U, P, bot_id):
        self.bot_uid = None
        self.nickname = "Unknown"
        self.vv_key = U
        self.bot_id = bot_id 
        self.writer2 = None
        self.attack_task = None
        self.is_running = True
        self.packet_cache = {}

    async def STarT(self, JwT_ToKen, AutH_ToKen, ip, port, ip2, port2, key, iv, bot_uid):
        region = "BD"
        if not self.attack_task or self.attack_task.done():
            self.attack_task = asyncio.create_task(self.Self_Driving_Attack(bot_uid, region, key, iv))
            
        await self.OnLinE(ip2, port2, AutH_ToKen, bot_uid, key, iv)

    async def OnLinE(self, host2, port2, tok, bot_uid, key, iv):
        disconnect_count = 0
        while self.is_running:
            try:
                self.reader2, self.writer2 = await asyncio.open_connection(host2, int(port2))
                self.writer2.write(bytes.fromhex(tok))
                await self.writer2.drain()
                
                # Success online & attacking status write
                Update_Bot_Status(self.bot_id, "✅ Online & Attacking", bot_uid, self.nickname, self.vv_key)
                disconnect_count = 0 
                
                while self.is_running:
                    data = await self.reader2.read(9999)
                    if not data:
                        raise ConnectionError("Garena Server Closed Connection")
                        
            except Exception: 
                if self.writer2:
                    try: self.writer2.close()
                    except: pass
                self.writer2 = None 
                
                disconnect_count += 1
                if disconnect_count >= 3:
                    Update_Bot_Status(self.bot_id, "❌ Disconnected permanently", bot_uid, self.nickname, self.vv_key)
                    save_bad_account(self.vv_key, "vv.json", "Attack Login Failed (3x)")
                    self.is_running = False
                    break 
                
                Update_Bot_Status(self.bot_id, f"⚠️ Reconnecting ({disconnect_count}/3)...", bot_uid, self.nickname, self.vv_key)
                await asyncio.sleep(5)

    def get_cached_packets(self, target, bot_uid, region, key, iv):
        if target not in self.packet_cache:
            self.packet_cache[target] = {
                'team': Make_Team_Packet(bot_uid, region, key, iv),
                'invite': Simple_Invite_Packet(target, region, key, iv),
                'leave': Leave_Team_Packet(bot_uid, region, key, iv),
                'room_open': Open_Room_Packet(key, iv),
                'room_inv': Room_Invite_Packet(target, key, iv),
                'fake_join': Fake_Profile_Join(target, region, key, iv)
            }
        return self.packet_cache[target]

    async def Spam_Single_Target(self, target, bot_uid, region, key, iv):
        try:
            if not self.writer2 or self.writer2.is_closing() or not self.is_running:
                return

            pkts = self.get_cached_packets(target, bot_uid, region, key, iv)

            def write_room():
                self.writer2.write(pkts['room_open'])
                self.writer2.write(pkts['room_inv'])
            
            def write_invite():
                for p in pkts['team']: self.writer2.write(p)
                self.writer2.write(pkts['invite'])
                self.writer2.write(pkts['leave'])

            def write_join():
                for p in pkts['team']: self.writer2.write(p)
                self.writer2.write(pkts['fake_join'])
                self.writer2.write(pkts['leave'])
            
            write_invite(); await self.writer2.drain(); await asyncio.sleep(0.5)
            write_room(); await self.writer2.drain(); await asyncio.sleep(0.5)
            write_join(); await self.writer2.drain(); await asyncio.sleep(0.5)
            write_room(); await self.writer2.drain(); await asyncio.sleep(0.5)
            write_join(); await self.writer2.drain(); await asyncio.sleep(0.5)
            write_room(); await self.writer2.drain()

        except Exception: 
            if self.writer2:
                try: self.writer2.close()
                except: pass
            self.writer2 = None

    async def Self_Driving_Attack(self, bot_uid, region, key, iv):
        while self.is_running:
            try:
                if not self.writer2: 
                    await asyncio.sleep(1); continue 

                if not ATTACK_TARGETS_DICT:
                    Update_Bot_Status(self.bot_id, "💤 Idle (No Targets)", bot_uid, self.nickname, self.vv_key)
                    await asyncio.sleep(2); continue

                # ========================================================
                # 🛑 PERFECT MATHEMATICAL TIME BARRIER 🛑
                # ========================================================
                now = time.time()
                sleep_time = 3.0 - (now % 3.0)
                await asyncio.sleep(sleep_time)
                
                total_lists = len(ATTACK_TARGETS_DICT)
                if total_lists == 0: continue
                
                ROTATION_STEP = int(time.time() / 3.0)
                
                my_list_id = ((self.bot_id + ROTATION_STEP - 1) % total_lists) + 1
                my_targets = ATTACK_TARGETS_DICT.get(str(my_list_id), [])
                
                if my_targets:
                    Update_Bot_Status(self.bot_id, f"🔥 Spamming List-{my_list_id}", bot_uid, self.nickname, self.vv_key)
                    tasks = [asyncio.create_task(self.Spam_Single_Target(t, bot_uid, region, key, iv)) for t in my_targets]
                    await asyncio.gather(*tasks)
                else:
                    Update_Bot_Status(self.bot_id, "💤 Idle", bot_uid, self.nickname, self.vv_key)

            except Exception:
                await asyncio.sleep(1)

    def GeT_Key_Iv(self, serialized_data):
        my_message = xKEys.MyMessage()
        my_message.ParseFromString(serialized_data)
        ts_obj = Timestamp(); ts_obj.FromNanoseconds(my_message.field21)
        return ts_obj.seconds * 1_000_000_000 + ts_obj.nanos, my_message.field22, my_message.field23

    async def GeT_LoGin_PorTs(self, JwT_ToKen, PayLoad, bot_uid, auth_url):
        session = await get_http_session()
        nickname = "Unknown"
        
        async def fetch_nickname():
            try:
                api_url = f"https://munna2233.vercel.app/player-info?uid={bot_uid}"
                async with session.get(api_url, timeout=7) as api_res:
                    if api_res.status == 200:
                        data = await api_res.json()
                        return data.get('basic_info', {}).get('nickname', 'Unknown')
            except: pass
            return "Unknown"

        async def fetch_garena_data():
            url = f"{auth_url}/GetLoginData" 
            headers = {
                "Authorization": f"Bearer {JwT_ToKen}", 
                "ReleaseVersion": "OB53", 
                "Content-Type": "application/x-www-form-urlencoded", 
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; SM-A515F Build/QP1A.190711.020)",
                "X-GA": "v1 1",
                "X-Unity-Version": "2018.4.11f1"
            }
            try:
                async with session.post(url, headers=headers, data=PayLoad, timeout=15) as res:
                    if res.status == 200:
                        raw = await res.read()
                        return raw.hex()
            except Exception: pass
            return None

        nick_task = asyncio.create_task(fetch_nickname())
        data_task = asyncio.create_task(fetch_garena_data())
        nickname, hex_data = await asyncio.gather(nick_task, data_task)

        if hex_data:
            try:
                data = json.loads(DeCode_PackEt(hex_data))
                if nickname == "Unknown":
                    nickname = data.get("4", {}).get("data", "Unknown")
                    
                a1, a2 = data["32"]["data"], data["14"]["data"]
                return a1[:-6], a1[-5:], a2[:-6], a2[-5:], nickname
            except: pass
        return None, None, None, None, nickname

    async def ToKen_GeneRaTe(self, U, P):
        try:
            acc, open_id = await G_AccEss(U, P)
            if not acc: return None
            
            pyl = {
                3: str(dt_mod.datetime.now())[:-7], 4: "free fire", 5: 1, 7: "1.123.1", 
                8: "Android OS 10 / API-29", 9: "mt6769t", 10: "Grameenphone", 
                11: "WIFI", 12: 1080, 13: 2340, 14: "440", 15: "AArch64 Processor rev 4 (aarch64) | 8 cores", 
                16: 4096, 17: "Mali-G52 MC2", 18: "OpenGL ES 3.2 v1.r14p0-01rel0", 
                19: f"android|{random.randint(10000000,99999999)}", 20: "127.0.0.1", 21: "en", 22: open_id, 
                23: "4", 24: "Handheld", 25: {6: 55, 8: 81}, 29: acc, 30: 1, 41: "Grameenphone", 42: "WIFI", 
                57: "7428b253defc164018c604a1ebbfebdf", 60: 114441, 61: 25432, 62: 114441, 63: 25432, 
                64: 25432, 65: 114441, 66: 25432, 67: 114441, 73: 3, 
                74: "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64", 76: 1, 
                77: "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk", 
                78: 3, 79: 2, 81: "64", 83: "2019118695", 86: "OpenGLES2", 87: 16383, 88: 4, 
                89: b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg==", 92: random.randint(12000, 15000), 
                93: "android", 94: "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY=", 
                95: 110009, 97: 1, 98: 0, 99: "4", 100: "4"
            }
            payload_hex = CrEaTe_ProTo(pyl).hex()
            final_payload = bytes.fromhex(EnC_AEs(payload_hex))
            
            resp = await MajorLoGin(final_payload)
            if resp:
                besto = json.loads(DeCode_PackEt(resp))
                uid = besto["1"]["data"]
                jwt_token = besto["8"]["data"]
                auth_url = besto.get("10", {}).get("data", "https://clientbp.ggblueshark.com")
                ts, key, iv = self.GeT_Key_Iv(bytes.fromhex(resp))
                ip, port, ip2, port2, nickname = await self.GeT_LoGin_PorTs(jwt_token, final_payload, uid, auth_url)
                
                if ip and port:
                    return (jwt_token, key, iv, ts, ip, port, ip2, port2, uid, nickname)
        except Exception: pass
        return None

    async def Get_FiNal_ToKen_0115(self, U, P):
        for attempt in range(1, 4):
            # Phase 2: Status write "Logging In"
            Update_Bot_Status(self.bot_id, "⏳ Logging In...", "Unknown", "Unknown", U)
            res = await self.ToKen_GeneRaTe(U, P)
            if res:
                token, key, iv, ts, ip, port, ip2, port2, bot_uid, nickname = res
                self.bot_uid = bot_uid
                self.nickname = nickname
                
                print("="*50)
                print(f"✅ LOGIN SUCCESSFUL! [Bot #{self.bot_id}]")
                print(f"👤 NAME: {self.nickname}") 
                print(f"🆔 UID : {self.bot_uid}")  
                print("="*50)
                
                # Phase 3: Status write "Connecting to gameplay socket"
                Update_Bot_Status(self.bot_id, "⏳ Connecting to Socket...", bot_uid, nickname, U)
                
                acc_id = jwt.decode(token, options={"verify_signature": False}).get("account_id")
                enc_acc = hex(acc_id)[2:]
                ts_hex = DecodE_HeX(ts)
                token_enc = EnC_PacKeT(token.encode().hex(), key, iv)
                zeros = "0000000" if len(enc_acc) == 9 else "00000000"
                self.AutH_ToKen = f"0115{zeros}{enc_acc}{ts_hex}00000{hex(len(token_enc)//2)[2:]}{token_enc}"
                
                asyncio.create_task(self.STarT(token, self.AutH_ToKen, ip, port, ip2, port2, key, iv, bot_uid))
                return
            await asyncio.sleep(3)
            
        print(f" [Bot #{self.bot_id}] ❌ Login Failed 3 times. Removing and saving to bad_accounts.")
        save_bad_account(U, "vv.json", "Attack Login Failed (3x)")
        Update_Bot_Status(self.bot_id, "❌ Login Failed (Removed)", "Error", "Error", U)
        self.is_running = False

# ==========================================
# === DYNAMIC WATCHERS & TIMERS ===
# ==========================================
async def Target_Loader_Async():
    global ATTACK_TARGETS_DICT
    if not os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "w") as f: json.dump({"1":[]}, f)
    prev_targets = ""
    while True:
        try:
            with open(TARGET_FILE, "r") as f: data = json.load(f)
            curr = json.dumps(data, sort_keys=True)
            if curr != prev_targets:
                ATTACK_TARGETS_DICT = data; prev_targets = curr
                print(" [UPDATE] Target List Refreshed")
        except: pass
        await asyncio.sleep(5)

async def VV_Watcher_Async():
    """Watches vv.json dynamically and starts/stops bots without restarting"""
    global TOTAL_BOTS_DICT
    last_state = ""
    bot_id_counter = 0
    
    while True:
        try:
            if not os.path.exists("vv.json"):
                with open("vv.json", "w") as f: json.dump({}, f)
                
            with open("vv.json", "r") as f: 
                current_accounts = json.load(f)
            
            curr_state = json.dumps(current_accounts, sort_keys=True)
            if curr_state != last_state:
                print("\n [SYSTEM] vv.json change detected. Syncing active bots...")
                
                # Check for REMOVED bots
                for active_uid in list(TOTAL_BOTS_DICT.keys()):
                    if active_uid not in current_accounts:
                        print(f" [-] Removing Bot: {active_uid}")
                        bot_obj = TOTAL_BOTS_DICT.pop(active_uid)
                        bot_obj.is_running = False
                        if bot_obj.writer2: bot_obj.writer2.close()
                        
                        with STATUS_LOCK:
                            bot_id_str = str(bot_obj.bot_id)
                            if bot_id_str in BOT_STATUS_DATA:
                                del BOT_STATUS_DATA[bot_id_str]
                
                # Check for NEW bots
                for u, p in current_accounts.items():
                    if u not in TOTAL_BOTS_DICT:
                        print(f" [+] Starting New Bot: {u}")
                        bot_id_counter += 1
                        new_bot = FF_CLient(u, p, bot_id_counter)
                        TOTAL_BOTS_DICT[u] = new_bot
                        
                        # Phase 1: Status write "Booting..."
                        Update_Bot_Status(bot_id_counter, "⏳ Booting...", "Unknown", "Unknown", u)
                        
                        asyncio.create_task(new_bot.Get_FiNal_ToKen_0115(u, p))
                        await asyncio.sleep(0.5) 
                        
                last_state = curr_state
        except Exception: pass
        await asyncio.sleep(5)

async def StarT_SerVer_Async():
    await get_http_session()

    if os.path.exists(LIVE_STATUS_FILE):
        try: os.remove(LIVE_STATUS_FILE)
        except: pass
        
    Thread(target=Live_Status_Writer, daemon=True).start()
    Thread(target=AuTo_ResTartinG, daemon=True).start()
    
    asyncio.create_task(Target_Loader_Async())
    asyncio.create_task(VV_Watcher_Async())
    
    print("\n [🚀] Main Attack Server Running (Original Perfect Logic)")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(StarT_SerVer_Async())
    except KeyboardInterrupt:
        print("\n[STOP] Bot Stopped Manually.")

# END OF FILE main.py
