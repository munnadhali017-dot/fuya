# xC4.py - Final Version with All Logic

import requests, json, binascii, time, urllib3, base64, datetime, re, socket, threading, random, os, sys, psutil
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from random import choice

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Encryption Keys (OB51) ---
Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def Ua():
    # Random User Agent for realism
    agents = [
        "Dalvik/2.1.0 (Linux; U; Android 10; SM-A205F Build/QP1A.190711.020)",
        "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
        "Dalvik/2.1.0 (Linux; U; Android 11; RMX3231 Build/RP1A.201005.001)"
    ]
    return random.choice(agents)

# --- Encryption Functions ---
def EnC_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def EnC_PacKeT(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

def DEc_PacKeT(HeX, K, V):
    return unpad(AES.new(K, AES.MODE_CBC, V).decrypt(bytes.fromhex(HeX)), 16).hex()

# --- Protobuf Helpers ---
def DecodE_HeX(H):
    R = hex(H)
    F = str(R)[2:]
    if len(F) == 1: F = "0" + F
    return F

def EnC_Vr(N):
    if N < 0: return b''
    H = []
    while True:
        BesTo = N & 0x7F; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)

def CrEaTe_VarianT(f, v):
    return EnC_Vr((f << 3) | 0) + EnC_Vr(v)

def CrEaTe_LenGTh(f, v):
    encoded = v.encode() if isinstance(v, str) else v
    return EnC_Vr((f << 3) | 2) + EnC_Vr(len(encoded)) + encoded

def CrEaTe_ProTo(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(CrEaTe_LenGTh(field, value))
    return packet

def GeneRaTePk(Pk, N, K, V):
    PkEnc = EnC_PacKeT(Pk, K, V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    head = N + ("000000" if len(_) == 2 else "00000" if len(_) == 3 else "0000")
    return bytes.fromhex(head + _ + PkEnc)

def xBunnEr():
    return int(random.choice(['902000016', '902000031', '902000011', '902000065', '902000306']))

# ==========================================
# === ATTACK PACKETS (UPDATED LOGIC) ===
# ==========================================

def Fake_Profile_Join(target_uid, region, K, V):
    """
    Fake Profile Packet (Fixed for Members)
    - Field 3: Random Fake Team ID (Fixes member visibility issue)
    - Field 4: 2 (Invite Type)
    """
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'

    # Random Badges
    badge_list = [64, 4096, 8192, 16384, 32768, 1048576]
    selected_badge = random.choice(badge_list)
    
    # Random Rank Score
    random_rank_score = random.choice([1000, 9999, 20000, 5000, 3210])
    
    # Random Fake Team ID (To look like a real team invite)
    fake_team_id = random.randint(2000000000, 3000000000)

    fields = {
        1: 33, 
        2: {
            1: int(target_uid),
            2: region if region else "BD",
            
            # [CRITICAL FIX HERE]
            3: int(fake_team_id),  # Random Team ID (Instead of 1)
            4: 2,                  # Type: 2 = INVITE (Visible to everyone)
            
            # Byte Flags (Member Visibility)
            5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]), 
            
            6: "[FF0000]System[FFFF00]Error", 
            7: 330,
            8: random_rank_score, 
            9: 100,
            10: "DZ",
            
            # Signature Bytes
            11: bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56, 97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53]), 
            
            12: 1,
            13: int(target_uid),
            
            # Signature Data
            14: {
                1: 2203434355,
                2: 8,
                3: b"\x10\x15\x08\n\x0b\x13\x0c\x0f\x11\x04\x07\x02\x03\r\x0e\x12\x01\x05\x06"
            },
            
            16: 1, 17: 1, 18: 312, 19: 46,
            
            23: bytes([16, 1, 24, 1]), 
            24: xBunnEr(), 
            
            26: "", 28: "",
            
            # Random Badge
            31: {1: 1, 2: selected_badge}, 
            32: selected_badge,
            
            # Profile Info
            34: {
                1: int(target_uid), 
                2: 8, 
                3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])
            }
        }
    }
    
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), packet_id, K, V)

def Make_Team_Packet(uid, region, K, V):
    """Creates new team with RANDOM Mode (1,2,62,73) and Size (Duo/Squad)"""
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'
    
    # Randomizing settings
    mode = random.choice([1, 2, 62, 73]) 
    size = random.choice([1, 3]) # 1=Duo, 3=Squad
    
    # Step 1: Open Team
    fields_open = {1: 1, 2: {2: "\u0001", 3: 1, 4: 1, 5: "en", 9: 1, 11: 1, 13: 1, 14: {2: 5756, 6: 11, 8: "1.111.5", 9: 2, 10: 4}}}
    pkt1 = GeneRaTePk(str(CrEaTe_ProTo(fields_open).hex()), packet_id, K, V)
    
    # Step 2: Change Settings
    fields_change = {1: 17, 2: {1: int(uid), 2: 1, 3: size, 4: mode, 5: "\u001a", 8: 5, 13: 329}}
    pkt2 = GeneRaTePk(str(CrEaTe_ProTo(fields_change).hex()), packet_id, K, V)
    
    return [pkt1, pkt2]

def Leave_Team_Packet(uid, region, K, V):
    """Leave current team"""
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'
    fields = {1: 7, 2: {1: int(uid)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), packet_id, K, V)

def Simple_Invite_Packet(target_uid, region, K, V):
    """Standard Invite Packet"""
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'
    fields = {1: 2, 2: {1: int(target_uid), 2: region, 4: 1}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), packet_id, K, V)

# --- SYSTEM HELPERS ---

def AuTo_ResTartinG():
    time.sleep(6 * 60 * 60)
    print("Restarting...")
    os.execl(sys.executable, sys.executable, *sys.argv)

def GeT_Time(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.hour, dt.minute, dt.second
    
# ==========================================
# === NEW ROOM SPAM PACKETS ===
# ==========================================

def Open_Room_Packet(K, V):
    """Creates a Custom Room (Action 2)"""
    fields = {
        1: 2,  
        2: {   
            1: 1, 2: 15, 3: 5, 4: "Xyron", 5: "1", 6: 12, 7: 1, 8: 1, 9: 1,
            11: 1, 12: 2, 14: 36981056,
            15: {1: "IDC3", 2: 126, 3: "ME"},
            16: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000f\u000e\u0016\u0019\u001a \u001d",
            18: 2368584, 27: 1, 34: "\u0000\u0001", 40: "en", 48: 1,
            49: {1: 21},
            50: {1: 36981056, 2: 2368584, 5: 2}
        }
    }
    # Header 0E15 for Custom Room
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)

def Room_Invite_Packet(target_uid, K, V):
    """Invites Target to Room (Action 22)"""
    fields = {
        1: 22,     
        2: {1: int(target_uid)}
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)

def Destroy_Room_Packet(bot_uid, K, V):
    """Leaves/Destroys the Room (Action 7)"""
    # Header 0E15 ব্যবহার করতে হবে কারণ এটি কাস্টম রুম
    fields = {1: 7, 2: {1: int(bot_uid)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)