# START OF FILE api.py

import asyncio
import json
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from cachetools import TTLCache
from datetime import datetime
from functools import wraps

from manager import GetAccountInformation, ACCOUNTS

app = Flask(__name__)
CORS(app)

# Cache setup (Keeps successful profiles in memory for 5 minutes)
cache = TTLCache(maxsize=200, ttl=300)

# ========================================================
# 🚀 SECURED NON-BLOCKING ANTI-CRASH BATCH LIMITER
# ========================================================
class AntiCrashLimiter:
    def __init__(self, limit=20, max_waiting=30):
        self.limit = limit
        self.max_waiting = max_waiting 
        self.semaphore = threading.Semaphore(limit)
        self.lock = threading.Lock()
        self.current_waiting = 0 

    def acquire(self):
        with self.lock:
            # Overload protection: if waiting queue exceeds 30, shed load instantly
            if self.current_waiting >= self.max_waiting:
                return False
            self.current_waiting += 1
            
        # Non-blocking Semaphore: Wait at most 8 seconds to prevent server freeze
        acquired = self.semaphore.acquire(timeout=8.0)
        
        with self.lock:
            self.current_waiting -= 1 
        return acquired

    def release(self):
        # Clean release without blocking time.sleep() bottlenecks
        self.semaphore.release()

# Limiters configuration
limiter = AntiCrashLimiter(limit=20, max_waiting=30)

# ==========================================
# Caching Decorator
# ==========================================
def cached_endpoint(ttl=300):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            key = (request.path, tuple(request.args.items()))
            if key in cache:
                return cache[key]
            res = fn(*a, **k)
            cache[key] = res
            return res
        return wrapper
    return decorator

@app.route("/")
def home():
    return jsonify({
        "App Name": "Info Flask Api",
        "Version": "7.5.0 (Non-Blocking Overload Protected)",
        "Modified by": "OUT_OF_LAW",
        "End Point": "/player-info?uid=1765197992",
        "Accounts Pool": f"{len(ACCOUNTS)} Accounts Loaded",
        "Developer": "Shuvo",
        "Copyright": "© 2025 Zero Gravity - All rights reserved.",
        "Region": "Global",  
        "TIKTOK": "@OUT_OF_LAW",
        "Status": "Active, Stable & Auto-Recoverable",
        "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/player-info')
@cached_endpoint(ttl=300)
def get_account_info():
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    # Acquire connection slot safely
    if not limiter.acquire():
        return jsonify({
            "error": "Server is currently experiencing extremely high traffic. Please try again in a few seconds.",
            "status": 503
        }), 503

    try:
        # Run asynchronous Garena fetch securely
        return_data = asyncio.run(GetAccountInformation(uid, "7", "/GetPlayerPersonalShow"))
        
        formatted_json = json.dumps(return_data, indent=2, ensure_ascii=False)
        return formatted_json, 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch info: {str(e)}"}), 500
        
    finally:
        # Always release slot safely even on failure
        limiter.release()

if __name__ == '__main__':
    # Running on exact port requested: 30161
    app.run(host='0.0.0.0', port=30161)

# END OF FILE api.py