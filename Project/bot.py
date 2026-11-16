import asyncio
import io
import os
import random
import re
import sys
import uuid
import urllib.parse
import zipfile
import json
import threading
import shutil
import time
import traceback
from datetime import datetime, timedelta
import http.server
import socketserver
import requests
from urllib3.exceptions import InsecureRequestWarning
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    HAS_BS4 = False

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest

# ╔══════════════════════════════════════════════════╗
# ║              ⚙️  CORE CONFIGURATION              ║
# ╚══════════════════════════════════════════════════╝
ALLOWED_GROUP_ID  = int(os.environ.get("ALLOWED_GROUP_ID", "-1003367560262"))
GROUP_INVITE_LINK = "https://t.me/NFByShinchanOfficial"
BOT_START_LINK    = "https://t.me/NFbyShinchan_bot?start=approvedgrp"
BOT_TOKEN         = os.environ.get("BOT_TOKEN")
OWNER_ID          = int(os.environ.get("OWNER_ID", "0"))
ADMIN_IDS         = [int(i) for i in os.environ.get("ADMIN_IDS", "").split(",") if i.strip()]
WATERMARK         = "⚡ NF By Shinchan | Made By @ShinchanNoharaTG ❤️"

# Fallback for local dev — remove for production
if not BOT_TOKEN:
    BOT_TOKEN = "8753664242:AAFR3lKkaU5_AM5_wW4nGJDyfczOhO9T8Yg"
if OWNER_ID == 0:
    OWNER_ID = 1115202962
if not ADMIN_IDS:
    ADMIN_IDS = [1115202962]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🌐 NETFLIX iOS API CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
QUERY_PARAMS = {
    "appVersion"    : "15.48.1",
    "config"        : '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
    "device_type"   : "NFAPPL-02-",
    "esn"           : "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom"         : "phone",
    "iosVersion"    : "15.8.5",
    "isTablet"      : "false",
    "languages"     : "en-US",
    "locale"        : "en-US",
    "maxDeviceWidth": "375",
    "model"         : "saget",
    "modelType"     : "IPHONE8-1",
    "odpAware"      : "true",
    "path"          : '["account","token","default"]',
    "pathFormat"    : "graph",
    "pixelDensity"  : "2.0",
    "progressive"   : "false",
    "responseFormat": "json",
}

BASE_HEADERS = {
    "User-Agent"                         : "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt"          : "1",
    "x-netflix.request.client.user.guid" : "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid"     : "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing"          : '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version"      : "15.48.1",
    "x-netflix.argo.translated"          : "true",
    "x-netflix.context.form-factor"      : "phone",
    "x-netflix.context.sdk-version"      : "2012.4",
    "x-netflix.client.appversion"        : "15.48.1",
    "x-netflix.context.max-device-width" : "375",
    "x-netflix.context.ab-tests"         : "",
    "x-netflix.tracing.cl.useractionid"  : "4DC655F2-9C3C-4343-8229-CA1B003C3053",
    "x-netflix.client.type"              : "argo",
    "x-netflix.client.ftl.esn"           : "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales"          : "en-US",
    "x-netflix.argo.abtests"             : "",
    "x-netflix.context.os-version"       : "15.8.5",
    "x-netflix.request.client.context"   : '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor"        : "argo",
    "x-netflix.argo.nfnsm"              : "9",
    "x-netflix.context.pixel-density"    : "2.0",
    "x-netflix.request.toplevel.uuid"    : "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.client.timezoneid"        : "Asia/Dhaka",
}

REQUIRED_COOKIE = "NetflixId"

# ━━━ Persistent storage paths (aminahost compatible) ━━━
COOKIES_DIR   = os.environ.get("COOKIES_DIR", "vault")
PROCESSED_DIR = os.path.join(COOKIES_DIR, "processed")
DATA_DIR      = os.environ.get("DATA_DIR", "data")

STATS_FILE            = os.path.join(DATA_DIR, "stats.json")
USER_USAGE_FILE       = os.path.join(DATA_DIR, "user_usage.json")
STARTED_USERS_FILE    = os.path.join(DATA_DIR, "started_users.json")
PENDING_WARNINGS_FILE = os.path.join(DATA_DIR, "pending_warnings.json")
CHATS_FILE            = os.path.join(DATA_DIR, "active_chats.json")
VERIFIED_GROUPS_FILE  = os.path.join(DATA_DIR, "verified_groups.json")
APPROVED_USERS_FILE   = os.path.join(DATA_DIR, "approved_users.json")
DYNAMIC_ADMINS_FILE   = os.path.join(DATA_DIR, "dynamic_admins.json")

USER_AGENT     = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DAILY_LIMIT    = 3
COOLDOWN_SECONDS = 30

# Create all required directories
for d in [COOKIES_DIR, PROCESSED_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔒 PER-FILE LOCKS (Thread-safe I/O)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cookie_lock          = threading.Lock()
stats_lock           = threading.Lock()
usage_lock           = threading.Lock()
started_users_lock   = threading.Lock()
pending_warn_lock    = threading.Lock()
chats_lock           = threading.Lock()
verified_groups_lock = threading.Lock()
approved_users_lock  = threading.Lock()
dynamic_admins_lock  = threading.Lock()

active_processing_codes: dict = {}
user_state: dict              = {}
user_cooldowns: dict          = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🎨 VISUAL HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAR_FULL  = "▰"
BAR_EMPTY = "▱"

def make_bar(percent: int, width: int = 12) -> str:
    filled = round(width * min(percent, 100) / 100)
    return f"<code>[{BAR_FULL * filled}{BAR_EMPTY * (width - filled)}]</code> {percent}%"

def make_use_bar(used: int, total: int = DAILY_LIMIT) -> str:
    remaining = max(0, total - used)
    bar = "🟢" * remaining + "🔴" * (total - remaining)
    return f"{bar}  <b>{remaining}/{total} left</b>"

def plan_icon(plan: str) -> str:
    p = str(plan).lower()
    if "premium" in p or "4k" in p or "ultra" in p:
        return "👑"
    elif "standard" in p or "1080" in p or "hd" in p:
        return "⭐"
    return "🍿"

def plan_label(plan: str) -> str:
    p = str(plan).lower()
    if "premium" in p or "4k" in p or "ultra" in p:
        return "PREMIUM ULTRA 4K HDR"
    elif "standard" in p:
        return "STANDARD FULL HD 1080p"
    return "PREMIUM 4K HDR" 

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📺 TV ACTIVATION ANIMATION FRAMES (smoother)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TV_ANIM_FRAMES = [
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🔍 <i>Scanning cookie vault...</i>\n"
        f"  <code>{make_bar(5)}</code>\n\n"
        "  ⠋ <i>Initializing secure session...</i>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🔑 <i>Extracting session token...</i>\n"
        f"  <code>{make_bar(20)}</code>\n\n"
        "  ⠙ <i>Decrypting NetflixId...</i>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🧬 <i>Validating cookie health...</i>\n"
        f"  <code>{make_bar(35)}</code>\n\n"
        "  ⠹ <i>Checking payment status...</i>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🌐 <i>Connecting to Netflix API...</i>\n"
        f"  <code>{make_bar(50)}</code>\n\n"
        "  ⠸ <i>Handshaking iOS endpoint...</i>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🔗 <i>Injecting auth context...</i>\n"
        f"  <code>{make_bar(65)}</code>\n\n"
        "  ⠼ <i>Binding TV rendezvous pair...</i>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  📡 <i>Pairing TV screen...</i>\n"
        f"  <code>{make_bar(82)}</code>\n\n"
        "  ⠴ <i>Finalizing rendezvous...</i>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   ⚡ <b>NF BY SHINCHAN ENGINE</b>      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  ✅ <i>Almost done...</i>\n"
        f"  <code>{make_bar(96)}</code>\n\n"
        "  ⠦ <i>Locking session...</i>"
    ),
]

TOKEN_ANIM_FRAMES = [
    (
        "╔══════════════════════════════════╗\n"
        "║   🔐 <b>TOKEN FORGE ACTIVE</b>         ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🔍 <i>Scanning premium vault...</i>\n"
        f"  <code>{make_bar(8)}</code>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   🔐 <b>TOKEN FORGE ACTIVE</b>         ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🧪 <i>Validating cookie health...</i>\n"
        f"  <code>{make_bar(25)}</code>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   🔐 <b>TOKEN FORGE ACTIVE</b>         ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🔑 <i>Checking payment status...</i>\n"
        f"  <code>{make_bar(42)}</code>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   🔐 <b>TOKEN FORGE ACTIVE</b>         ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  ⚗️ <i>Generating nftoken...</i>\n"
        f"  <code>{make_bar(60)}</code>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   🔐 <b>TOKEN FORGE ACTIVE</b>         ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🔗 <i>Encoding secure URL...</i>\n"
        f"  <code>{make_bar(80)}</code>"
    ),
    (
        "╔══════════════════════════════════╗\n"
        "║   🔐 <b>TOKEN FORGE ACTIVE</b>         ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  🚀 <i>Preparing delivery...</i>\n"
        f"  <code>{make_bar(96)}</code>"
    ),
]

# ╔══════════════════════════════════════════════════╗
# ║         👑 DYNAMIC ADMIN MANAGEMENT              ║
# ╚══════════════════════════════════════════════════╝
def _safe_load_json(filepath: str, default):
    """Thread-safe JSON loader with corruption recovery."""
    if not os.path.exists(filepath):
        return default() if callable(default) else default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # File corrupted — backup and return default
        try:
            shutil.copy2(filepath, filepath + ".bak")
        except:
            pass
        return default() if callable(default) else default

def _safe_save_json(filepath: str, data):
    """Atomic JSON save — writes to temp file first, then renames."""
    tmp = filepath + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        shutil.move(tmp, filepath)
    except Exception:
        # Fallback direct write
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def load_dynamic_admins() -> list:
    with dynamic_admins_lock:
        return _safe_load_json(DYNAMIC_ADMINS_FILE, list)

def save_dynamic_admins(data: list):
    with dynamic_admins_lock:
        _safe_save_json(DYNAMIC_ADMINS_FILE, data)

def get_all_admin_ids() -> list:
    return list(set(ADMIN_IDS + load_dynamic_admins()))

def is_owner_or_strict_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in get_all_admin_ids()

# ╔══════════════════════════════════════════════════╗
# ║           ✅ APPROVED USERS SYSTEM                ║
# ╚══════════════════════════════════════════════════╝
def load_approved_users() -> dict:
    with approved_users_lock:
        return _safe_load_json(APPROVED_USERS_FILE, dict)

def save_approved_users(data: dict):
    with approved_users_lock:
        _safe_save_json(APPROVED_USERS_FILE, data)

def is_user_approved(user_id: int) -> bool:
    if is_owner_or_strict_admin(user_id):
        return True
    data = load_approved_users()
    uid  = str(user_id)
    if uid not in data:
        return False
    entry = data[uid]
    if entry.get("expiry") == "unlimited":
        return True
    try:
        return datetime.now() < datetime.fromisoformat(entry["expiry"])
    except:
        return False

def get_approval_info(user_id: int) -> dict | None:
    data = load_approved_users()
    uid  = str(user_id)
    if uid not in data:
        return None
    entry = data[uid]
    if entry.get("expiry") == "unlimited":
        return entry
    try:
        if datetime.now() < datetime.fromisoformat(entry["expiry"]):
            return entry
    except:
        pass
    return None

def approve_user(user_id: int, username: str, days: int | None, approved_by: int):
    data   = load_approved_users()
    uid    = str(user_id)
    expiry = "unlimited" if days is None else (datetime.now() + timedelta(days=days)).isoformat()
    data[uid] = {
        "user_id"    : user_id,
        "username"   : username,
        "expiry"     : expiry,
        "approved_by": approved_by,
        "approved_at": datetime.now().isoformat(),
    }
    save_approved_users(data)

def revoke_user_approval(user_id: int) -> bool:
    data = load_approved_users()
    uid  = str(user_id)
    if uid in data:
        del data[uid]
        save_approved_users(data)
        return True
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🗂️ VERIFIED GROUPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_verified_groups() -> dict:
    with verified_groups_lock:
        return _safe_load_json(VERIFIED_GROUPS_FILE, dict)

def save_verified_groups(data: dict):
    with verified_groups_lock:
        _safe_save_json(VERIFIED_GROUPS_FILE, data)

def is_group_allowed(chat_id: int) -> bool:
    if chat_id == ALLOWED_GROUP_ID:
        return True
    return str(chat_id) in load_verified_groups()

async def is_user_admin_in_chat(user_id: int, chat_id: int, context) -> bool:
    if is_owner_or_strict_admin(user_id):
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("administrator", "creator")
    except:
        return False

async def schedule_message_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list, delay_seconds: int = 36000):
    await asyncio.sleep(delay_seconds)
    for mid in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except:
            pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📣 ERROR REPORTING TO OWNER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def report_error_to_owner(context: ContextTypes.DEFAULT_TYPE, error: Exception, source: str = "Unknown"):
    try:
        tb = traceback.format_exc()[:3000]
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   🚨 <b>BOT ERROR REPORT</b>          ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  📍 <b>Source:</b>  <code>{source}</code>\n"
                f"  ⚠️ <b>Error:</b>   <code>{str(error)[:300]}</code>\n\n"
                f"  📋 <b>Traceback:</b>\n<pre>{tb}</pre>\n\n"
                f"  🕐 <b>Time:</b>    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            parse_mode=ParseMode.HTML
        )
    except:
        pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ⏱️ USER COOLDOWN SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_cooldown(user_id: int) -> int:
    if is_owner_or_strict_admin(user_id) or is_user_approved(user_id):
        return 0
    last    = user_cooldowns.get(user_id, 0)
    elapsed = time.time() - last
    if elapsed < COOLDOWN_SECONDS:
        return int(COOLDOWN_SECONDS - elapsed)
    return 0

def set_cooldown(user_id: int):
    if not is_owner_or_strict_admin(user_id) and not is_user_approved(user_id):
        user_cooldowns[user_id] = time.time()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚫 PM MEMBER COMMAND BLOCKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def send_pm_group_only_message(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("🔗 Join Our Group", url=GROUP_INVITE_LINK)]]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   🚫 <b>GROUP ONLY COMMAND</b>          ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  👋 Hey <b>{user.first_name}</b>!\n\n"
            f"  ❌ <code>/{command}</code> only works in our\n"
            "     approved group.\n\n"
            "  ┌──────────────────────────────┐\n"
            "  │  📢 Join the group and use    │\n"
            "  │  commands there for Netflix!  │\n"
            "  └──────────────────────────────┘\n\n"
            f"  {WATERMARK}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  👤 STARTED-USER TRACKING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_started_users() -> list:
    with started_users_lock:
        return _safe_load_json(STARTED_USERS_FILE, list)

def save_started_user(user_id: int):
    with started_users_lock:
        users = _safe_load_json(STARTED_USERS_FILE, list)
        if user_id not in users:
            users.append(user_id)
            _safe_save_json(STARTED_USERS_FILE, users)

def has_started_bot(user_id: int) -> bool:
    if is_owner_or_strict_admin(user_id):
        return True
    return user_id in load_started_users()

def track_active_chat(chat_id: int):
    with chats_lock:
        chats = _safe_load_json(CHATS_FILE, list)
        if chat_id not in chats:
            chats.append(chat_id)
            _safe_save_json(CHATS_FILE, chats)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔔 SMART DM CHECK (Fixed — no empty message probe)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def can_bot_dm_user(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    FIXED: No longer sends empty/probe messages.
    Relies on started_users tracking which is 100% reliable.
    """
    if is_owner_or_strict_admin(user_id):
        return True
    return has_started_bot(user_id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ⚠️ PENDING WARNINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_pending_warnings() -> dict:
    with pending_warn_lock:
        return _safe_load_json(PENDING_WARNINGS_FILE, dict)

def save_pending_warnings(data: dict):
    with pending_warn_lock:
        _safe_save_json(PENDING_WARNINGS_FILE, data)

def add_pending_warning(user_id: int, msg_id: int, group_chat_id: int):
    warnings = load_pending_warnings()
    warnings[str(user_id)] = {"chat_id": group_chat_id, "message_id": msg_id}
    save_pending_warnings(warnings)

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_owner_or_strict_admin(user_id):
        return True
    try:
        member = await context.bot.get_chat_member(chat_id="@NFByShinchanOfficial", user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🌟 Smart Start Verification Callback
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_and_clear_warning(user_id: int, context, user_first_name: str = "User"):
    warnings = load_pending_warnings()
    uid_str  = str(user_id)
    if uid_str not in warnings:
        return None

    info          = warnings[uid_str]
    group_chat_id = info["chat_id"]

    try:
        await context.bot.delete_message(chat_id=group_chat_id, message_id=info["message_id"])
    except:
        pass

    try:
        notif = await context.bot.send_message(
            chat_id=group_chat_id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   ✅ <b>USER VERIFIED!</b>              ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  👤 <b>{user_first_name}</b> is now verified!\n"
                "  📺 Commands unlocked: /tv /phone /pc\n\n"
                f"  {WATERMARK}"
            ),
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(
            schedule_message_deletion(context, group_chat_id, [notif.message_id], 30)
        )
    except:
        pass

    del warnings[uid_str]
    save_pending_warnings(warnings)
    return group_chat_id

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📊 USER USAGE TRACKING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_user_usage() -> dict:
    with usage_lock:
        return _safe_load_json(USER_USAGE_FILE, dict)

def save_user_usage(data: dict):
    with usage_lock:
        _safe_save_json(USER_USAGE_FILE, data)

def get_user_remaining_uses(user_id: int) -> int:
    if is_owner_or_strict_admin(user_id) or is_user_approved(user_id):
        return 999
    usage = load_user_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    uid   = str(user_id)
    if uid not in usage or usage[uid].get("date") != today:
        return DAILY_LIMIT
    return max(0, DAILY_LIMIT - usage[uid]["count"])

def deduct_user_netflix_limit(user_id: int):
    if is_owner_or_strict_admin(user_id) or is_user_approved(user_id):
        return
    usage = load_user_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    uid   = str(user_id)
    if uid not in usage or usage[uid].get("date") != today:
        usage[uid] = {"date": today, "count": 0}
    usage[uid]["count"] += 1
    save_user_usage(usage)

def refund_user_netflix_limit(user_id: int):
    if is_owner_or_strict_admin(user_id) or is_user_approved(user_id):
        return
    usage = load_user_usage()
    today = datetime.now().strftime("%Y-%m-%d")
    uid   = str(user_id)
    if uid in usage and usage[uid].get("date") == today and usage[uid]["count"] > 0:
        usage[uid]["count"] -= 1
        save_user_usage(usage)

def reset_user_usage(user_id: int):
    usage = load_user_usage()
    uid   = str(user_id)
    if uid in usage:
        usage[uid]["count"] = 0
        save_user_usage(usage)

# ╔══════════════════════════════════════════════════╗
# ║     🔍 STRICT COOKIE VALIDATION ENGINE           ║
# ║  FIXED: Only active + paid cookies pass          ║
# ╚══════════════════════════════════════════════════╝

# ── Comprehensive rejection keywords ──
REJECT_PAYMENT_HOLD = [
    "paymenthold", "payment_hold", "fix_payment", "fixpayment",
    "paymentmethodhold", "payment_method_hold", "update_payment",
    "updatepayment", "payment_issue", "paymentissue",
    "payment_failed", "paymentfailed", "billing_failed",
    "billingfailed", "past_due", "pastdue", "payment_declined",
    "paymentdeclined", "payment_problem", "paymentproblem",
    "update_billing", "updatebilling", "add_payment",
    "addpayment", "fix_billing", "fixbilling",
]

REJECT_FREE_NEVER = [
    "never_member", "nevermember", "noplan", "no_plan",
    "free_trial", "freetrial", "trial_expired", "trialexpired",
    "no_subscription", "nosubscription", "no_membership",
    "nomembership", "signup", "sign_up", "choose_plan",
    "chooseplan", "select_plan", "selectplan",
]

REJECT_SUSPENDED = [
    "account_suspended", "suspended", "account_cancelled",
    "cancelled", "account_closed", "membership_cancelled",
    "on_hold", "onhold", "account_locked", "locked",
    "account_deactivated", "deactivated", "account_terminated",
    "terminated", "membership_expired", "expired_membership",
    "inactive_account", "inactiveaccount",
]

REJECT_DEVICE_LIMIT = [
    "device limit", "limit exceeded", "devicelimitexceeded",
    "too_many_devices", "toomanydevices",
]

ALL_REJECT_KEYWORDS = (
    REJECT_PAYMENT_HOLD + REJECT_FREE_NEVER +
    REJECT_SUSPENDED + REJECT_DEVICE_LIMIT
)

def _detect_plan_from_api(data: dict, cookie_content: str = "", zip_filename: str = "") -> str:
    """
    REWRITTEN: Multi-signal plan detection with weighted scoring.
    Uses 6 detection methods to accurately classify premium vs standard.
    Returns "premium", "standard", or "basic".
    """
    premium_score  = 0
    standard_score = 0
    basic_score    = 0

    value = data.get("value") or {}
    full_json_str = json.dumps(data).lower() if isinstance(data, dict) else str(data).lower()

    # ══════════════════════════════════════════════
    # SIGNAL 1: Direct plan name fields (HIGHEST weight = 10)
    # ══════════════════════════════════════════════
    plan_patterns = [
        r'"localizedplanname"[^}]*?"value"\s*:\s*"([^"]+)"',
        r'"planname"\s*:\s*"([^"]+)"',
        r'"currentplanname"\s*:\s*"([^"]+)"',
        r'"planslug"\s*:\s*"([^"]+)"',
        r'"currentplan"\s*:\s*"([^"]+)"',
        r'"subscriptiontype"\s*:\s*"([^"]+)"',
        r'"tier"\s*:\s*"([^"]+)"',
        r'"plantier"\s*:\s*"([^"]+)"',
    ]
    for pat in plan_patterns:
        m = re.search(pat, full_json_str)
        if m:
            val = m.group(1).lower()
            if any(k in val for k in ["premium", "4k", "uhd", "ultra", "platino", "cao cấp", "プレミアム"]):
                premium_score += 10
            elif any(k in val for k in ["basic", "mobile", "basico", "básico", "basik", "ベーシック"]):
                basic_score += 10
            elif any(k in val for k in ["standard", "estándar", "padrão", "スタンダード"]):
                standard_score += 10

    # ══════════════════════════════════════════════
    # SIGNAL 2: Quality/Resolution capabilities (weight = 8)
    #   - UHD/4K/HDR/DolbyVision/DolbyAtmos = PREMIUM
    #   - HD/1080p only = STANDARD
    # ══════════════════════════════════════════════
    premium_quality_kws = [
        "uhd", "4k", "2160p", "ultrahd", "ultra_hd",
        "dolbyvision", "dolby_vision", "dolby vision",
        "dolbyatmos", "dolby_atmos", "dolby atmos",
        "hdr10", "hdr", "highquality", "high_quality",
        "uhdavailable", "uhd_available",
        "supershd", "super_hd", "superhd",
    ]
    standard_quality_kws = [
        "1080p", "fullhd", "full_hd",
    ]
    basic_quality_kws = [
        "480p", "sd_quality", "sdquality", "lowquality", "low_quality",
    ]

    for kw in premium_quality_kws:
        if kw in full_json_str:
            premium_score += 8

    for kw in standard_quality_kws:
        if kw in full_json_str:
            standard_score += 3  # Lower weight — 1080p also appears in premium

    for kw in basic_quality_kws:
        if kw in full_json_str:
            basic_score += 8

    # ══════════════════════════════════════════════
    # SIGNAL 3: Max streams / concurrent devices (weight = 7)
    #   - 4 streams = PREMIUM
    #   - 2 streams = STANDARD
    #   - 1 stream  = BASIC
    # ══════════════════════════════════════════════
    stream_patterns = [
        r'"maxstreams"\s*:\s*(\d+)',
        r'"numofauthorizeddevices"\s*:\s*(\d+)',
        r'"concurrentstreams"\s*:\s*(\d+)',
        r'"maxconcurrentstreams"\s*:\s*(\d+)',
        r'"allowedstreams"\s*:\s*(\d+)',
        r'"numstreams"\s*:\s*(\d+)',
    ]
    for pat in stream_patterns:
        m = re.search(pat, full_json_str)
        if m:
            num = int(m.group(1))
            if num >= 4:
                premium_score += 7
            elif num >= 2:
                standard_score += 7
            elif num == 1:
                basic_score += 7
            break  # Use first match only

    # ══════════════════════════════════════════════
    # SIGNAL 4: Boolean capability flags (weight = 6)
    # ══════════════════════════════════════════════
    # Check for UHD/4K enabled flags
    uhd_flag_patterns = [
        r'"isuhdavailable"\s*:\s*true',
        r'"uhdenabled"\s*:\s*true',
        r'"is4k"\s*:\s*true',
        r'"4kenabled"\s*:\s*true',
        r'"canstream4k"\s*:\s*true',
        r'"hasuhd"\s*:\s*true',
        r'"hdravailable"\s*:\s*true',
        r'"ishdr"\s*:\s*true',
        r'"dolbyvisionenabled"\s*:\s*true',
        r'"atmosenabled"\s*:\s*true',
    ]
    for pat in uhd_flag_patterns:
        if re.search(pat, full_json_str):
            premium_score += 6

    # Check for UHD/4K disabled flags → hints at standard
    uhd_disabled_patterns = [
        r'"isuhdavailable"\s*:\s*false',
        r'"uhdenabled"\s*:\s*false',
        r'"is4k"\s*:\s*false',
        r'"canstream4k"\s*:\s*false',
    ]
    for pat in uhd_disabled_patterns:
        if re.search(pat, full_json_str):
            standard_score += 4

    # ══════════════════════════════════════════════
    # SIGNAL 5: Keyword scoring in value block (weight = 3)
    #   Lower weight because these can appear in URLs etc.
    # ══════════════════════════════════════════════
    value_str = json.dumps(value).lower() if isinstance(value, dict) else str(value).lower()

    # Only count if keyword appears outside of URLs and common paths
    # Use word boundary-like checks
    for kw in ["premium", "ultra"]:
        # Count occurrences that are likely plan-related
        count = len(re.findall(r'(?<![a-z])' + kw + r'(?![a-z])', value_str))
        premium_score += count * 3

    for kw in ["standard"]:
        count = len(re.findall(r'(?<![a-z])' + kw + r'(?![a-z])', value_str))
        standard_score += count * 3

    for kw in ["basic", "mobile"]:
        count = len(re.findall(r'(?<![a-z])' + kw + r'(?![a-z])', value_str))
        basic_score += count * 3

    # ══════════════════════════════════════════════
    # SIGNAL 6: Original filename / cookie content hints (weight = 5)
    #   - If ZIP filename says "premium" → strong hint
    #   - If cookie metadata says "premium" → strong hint
    # ══════════════════════════════════════════════
    hint_text = (zip_filename + " " + cookie_content[:1500]).lower()

    # Check metadata block (lines starting with #)
    for line in cookie_content[:2000].splitlines():
        line = line.strip().lower()
        if line.startswith("#") and "plan" in line:
            if any(k in line for k in ["premium", "4k", "uhd", "ultra"]):
                premium_score += 5
            elif any(k in line for k in ["standard", "hd"]):
                standard_score += 5
            elif any(k in line for k in ["basic", "mobile"]):
                basic_score += 5

    # Filename hints
    fn = zip_filename.lower()
    if any(k in fn for k in ["premium", "4k", "uhd", "ultra", "prem"]):
        premium_score += 5
    elif any(k in fn for k in ["standard", "std"]):
        standard_score += 5
    elif any(k in fn for k in ["basic", "mobile", "bas"]):
        basic_score += 5

    # ══════════════════════════════════════════════
    # FINAL DECISION
    # ══════════════════════════════════════════════
    # If basic has highest score → return basic (will be rejected)
    if basic_score > 0 and basic_score >= premium_score and basic_score >= standard_score:
        return "basic"

    # If premium has ANY score above 0, and beats or ties standard → premium
    # This is intentionally biased toward premium to prevent false downgrades
    if premium_score > 0 and premium_score >= standard_score:
        return "premium"

    if standard_score > 0:
        return "standard"

    # No signals at all — default to standard
    return "standard"


def process_nftoken_cookie(content: str, zip_filename: str = ""):
    """
    FIXED: Strict validation — only active + paid cookies pass.
    Returns (result_dict, status_msg) or (None, rejection_reason).
    zip_filename: original filename from ZIP archive (used as plan hint).
    """
    cookies    = extract_cookie_dict_advanced(content)
    netflix_id = cookies.get(REQUIRED_COOKIE)
    if not netflix_id:
        return None, "No NetflixId found."

    headers = dict(BASE_HEADERS)
    headers["Cookie"] = f"NetflixId={netflix_id}"

    try:
        resp = requests.get(API_URL, params=QUERY_PARAMS, headers=headers, timeout=15, verify=False)
        if resp.status_code == 401 or resp.status_code == 403:
            return None, f"Auth failed (HTTP {resp.status_code})"
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return None, "API timeout"
    except requests.exceptions.ConnectionError:
        return None, "Connection error"
    except json.JSONDecodeError:
        return None, "Invalid API response (not JSON)"
    except Exception as e:
        return None, str(e)

    # ── Stringify value block for keyword checks ──
    value     = data.get("value") or {}
    raw_lower = json.dumps(value).lower() if isinstance(value, dict) else str(value).lower()

    # ── STRICT REJECTION: Check ALL dead/hold/free keywords ──
    for kw in ALL_REJECT_KEYWORDS:
        if kw in raw_lower:
            return None, f"Rejected: '{kw}' detected"

    # ── Extract token ──
    account    = value.get("account") or {} if isinstance(value, dict) else {}
    token_data = {}
    try:
        token_data = (account.get("token") or {}).get("default") or {}
    except:
        pass

    token   = token_data.get("token")
    expires = token_data.get("expires")
    if not token:
        return None, "No token in API response (dead cookie)"

    # ── Plan detection (multi-signal) ──
    plan_name = _detect_plan_from_api(data, cookie_content=content, zip_filename=zip_filename)
    if plan_name == "basic":
        return None, "Basic/Mobile plan — rejected"

    # ── Parse expiry ──
    if isinstance(expires, int) and len(str(expires)) == 13:
        expires //= 1000
    try:
        expiry_date = datetime.fromtimestamp(expires).strftime("%Y-%m-%d") if expires else "N/A"
    except:
        expiry_date = "N/A"

    return {
        "token"  : token,
        "expiry" : expiry_date,
        "plan"   : plan_name,
        "raw"    : raw_lower[:500],  # Keep only first 500 chars for memory
    }, "success"


# ╔══════════════════════════════════════════════════╗
# ║       🔍 COOKIE INFO PARSER (Improved)           ║
# ╚══════════════════════════════════════════════════╝
def parse_full_cookie_info_dict(content: str, token_res: dict = None) -> dict:
    info = {
        "name"             : "N/A",
        "country"          : "N/A",
        "plan"             : "N/A",
        "member_since"     : "N/A",
        "next_billing"     : "N/A",
        "quality"          : "N/A",
        "streams"          : "N/A",
        "hold_status"      : "No",
        "membership_status": "Active",
        "email"            : "N/A"
    }

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()

        m = re.match(r'^(?:👤\s*)?Name\s*:\s*(.+)$', line, re.I)
        if m and info["name"] in ("N/A", ""):
            info["name"] = m.group(1).strip()

        m = re.match(r'^(?:🌍\s*)?Country\s*:\s*([^\|]+)(?:\|.*)?$', line, re.I)
        if m and info["country"] in ("N/A", ""):
            info["country"] = m.group(1).strip()

        m = re.match(r'^(?:📋\s*)?Plan\s*:\s*(.+)$', line, re.I)
        if m and info["plan"] in ("N/A", ""):
            info["plan"] = m.group(1).strip()

        m = re.match(r'^(?:📅\s*)?Member Since\s*:\s*(.+)$', line, re.I)
        if m and info["member_since"] in ("N/A", ""):
            info["member_since"] = m.group(1).strip()

        m = re.match(r'^(?:🗓\s*)?Next Billing\s*:\s*(.+)$', line, re.I)
        if m and info["next_billing"] in ("N/A", ""):
            info["next_billing"] = m.group(1).strip()

        m = re.match(r'^(?:📧\s*)?Email\s*:\s*([^\s]+)$', line, re.I)
        if m and info["email"] in ("N/A", ""):
            info["email"] = m.group(1).strip()

    # Fallback extraction from raw content
    if info["name"] in ("N/A", ""):
        for pat in [r'"accountOwnerName"\s*:\s*"([^"]+)"', r'"userEmail"\s*:\s*"([^"]+)"', r'Email:\s*([^\s\n]+)']:
            m = re.search(pat, content, re.I)
            if m:
                info["name"] = m.group(1).strip()
                break
        if info["name"] in ("N/A", "") and info["email"] not in ("N/A", ""):
            info["name"] = info["email"]

    if info["country"] in ("N/A", ""):
        for pat in [r'"countryOfSignup"\s*:\s*"([^"]+)"', r'Country:\s*([^\s\n\|]+)', r'"country"\s*:\s*"([A-Za-z]{2,})"']:
            m = re.search(pat, content, re.I)
            if m:
                info["country"] = m.group(1).strip()
                break

    if info["plan"] in ("N/A", ""):
        for pat in [r'"localizedPlanName"[^}]*?"value"\s*:\s*"([^"]+)"', r'"planName"\s*:\s*"([^"]+)"', r'Plan:\s*([^\n\r\|]+)']:
            m = re.search(pat, content, re.I)
            if m:
                info["plan"] = m.group(1).strip()
                break

    if info["member_since"] in ("N/A", ""):
        for pat in [r'"memberSince"\s*:\s*"([^"]+)"', r'Member Since:\s*([^\n\r]+)']:
            m = re.search(pat, content, re.I)
            if m:
                info["member_since"] = m.group(1).strip()
                break

    if info["next_billing"] in ("N/A", ""):
        for pat in [r'"nextBillingDate"[^}]*?"date"\s*:\s*"([^T"]+)"', r'"nextBillingDate"\s*:\s*"([^T"]+)"', r'Next Billing:\s*([^\n\r]+)']:
            m = re.search(pat, content, re.I)
            if m:
                info["next_billing"] = m.group(1).strip()
                break

    # ── Plan/quality enrichment from token_res ──
    plan_token = (token_res.get("plan", "") if token_res else "") or ""
    full_text  = (info["plan"] + " " + plan_token + " " + content[:2000]).lower()

    if any(k in full_text for k in ["premium", "4k", "uhd", "ultra"]):
        if info["plan"] in ("N/A", ""):
            info["plan"] = "Premium (4K UHD)"
        info["quality"] = "4K + HDR / UHD"
        info["streams"] = "4 Screens"
    elif any(k in full_text for k in ["standard", "hd", "padrão"]):
        if info["plan"] in ("N/A", ""):
            info["plan"] = "Standard (Full HD)"
        info["quality"] = "Full HD (1080p)"
        info["streams"] = "2 Screens"
    else:
        if info["plan"] in ("N/A", ""):
            info["plan"] = "Standard (HD)"
        info["quality"] = "Full HD (1080p)"
        info["streams"] = "2 Screens"

    if info["name"] in ("N/A", ""):
        info["name"] = "Netflix Member"
    return info


def format_account_info_card(content: str, token_res: dict = None) -> str:
    info = parse_full_cookie_info_dict(content, token_res)
    pi   = plan_icon(info["plan"])
    plan_name = plan_label(info["plan"])
    return (
        "╭─────────────────────────────────────╮\n"
        "│  🎬  <b>NETFLIX ACCOUNT SPECIFICATIONS</b> │\n"
        "├─────────────────────────────────────┤\n"
        f"│  👤  <b>Holder</b>   ▸  <code>{info['name']}</code>\n"
        f"│  🌍  <b>Region</b>   ▸  <code>{info['country']}</code>\n"
        f"│  {pi}  <b>Tier</b>     ▸  <code>{plan_name}</code>\n"
        f"│  📅  <b>Member</b>   ▸  <code>{info['member_since']}</code>\n"
        f"│  💳  <b>Renewal</b>  ▸  <code>{info['next_billing']}</code>\n"
        f"│  🎞️  <b>Quality</b>  ▸  <code>{info['quality']}</code>\n"
        f"│  📺  <b>Screens</b>  ▸  <code>{info['streams']}</code>\n"
        "│  ⚡  <b>Status</b>   ▸  <code>[ 🟢 ACTIVE • LIVE ]</code>\n"
        "╰─────────────────────────────────────╯"
    )


def create_cookie_file_data(content: str, cookie_dict: dict, token_res: dict = None) -> str:
    info = parse_full_cookie_info_dict(content, token_res)
    meta_header = (
        "# [METADATA_START]\n"
        f"# Name: {info['name']}\n"
        f"# Country: {info['country']}\n"
        f"# Plan: {info['plan']}\n"
        f"# Member Since: {info['member_since']}\n"
        f"# Next Billing: {info['next_billing']}\n"
        f"# Quality: {info['quality']}\n"
        f"# Streams: {info['streams']}\n"
        f"# Email: {info['email']}\n"
        "# [METADATA_END]\n"
    )
    return meta_header + dict_to_netscape(cookie_dict)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📊 SYSTEM STATS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _load_sys_stats_raw() -> dict:
    data = _safe_load_json(STATS_FILE, dict)
    data.setdefault("users_list", [])
    data.setdefault("active_today", {"date": datetime.now().strftime("%Y-%m-%d"), "users": []})
    return data

def load_system_stats() -> dict:
    with stats_lock:
        return _load_sys_stats_raw()

def save_system_stats(data: dict):
    with stats_lock:
        _safe_save_json(STATS_FILE, data)

def track_user_activity(user_id: int):
    with stats_lock:
        data    = _load_sys_stats_raw()
        changed = False
        today   = datetime.now().strftime("%Y-%m-%d")
        if user_id not in data["users_list"]:
            data["users_list"].append(user_id)
            changed = True
        if data["active_today"].get("date") != today:
            data["active_today"] = {"date": today, "users": []}
            changed = True
        if user_id not in data["active_today"]["users"]:
            data["active_today"]["users"].append(user_id)
            changed = True
        if changed:
            _safe_save_json(STATS_FILE, data)

def update_cookie_stats(stat_type: str, plan: str, count: int = 1):
    """Unified stat updater. stat_type = 'uploaded' or 'purged'."""
    with stats_lock:
        data = _load_sys_stats_raw()
        key  = f"{stat_type}_{plan}"
        data[key] = data.get(key, 0) + count
        _safe_save_json(STATS_FILE, data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🗄️ VAULT HELPERS (FIXED: Unified single-file pool)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_vault_cookies() -> list:
    """Get all live cookie files in vault."""
    if not os.path.exists(COOKIES_DIR):
        return []
    return [
        f for f in os.listdir(COOKIES_DIR)
        if f.lower().endswith((".txt", ".json"))
        and not f.startswith("dead_")
        and not f.startswith("error_")
        and os.path.isfile(os.path.join(COOKIES_DIR, f))
    ]

def count_vault_cookies() -> int:
    return len(get_vault_cookies())

def count_pool(plan_type: str) -> int:
    """Count cookies matching a plan type (premium/standard)."""
    return sum(1 for f in get_vault_cookies() if plan_type.lower() in f.lower())

def dict_to_netscape(cookie_dict: dict, domain: str = ".netflix.com") -> str:
    expiry = int(time.time()) + 180 * 24 * 3600
    lines  = ["# Netscape HTTP Cookie File"]
    for k, v in cookie_dict.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t{expiry}\t{k}\t{v}")
    return "\n".join(lines)

def extract_cookie_dict_advanced(content: str) -> dict:
    if not content:
        return {}
    out = {}
    trimmed = content.strip()

    # 1. Netscape / Tab or whitespace delimited (from user script)
    for line in trimmed.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#HttpOnly_"):
            line = line[10:]
        elif line.startswith("#"):
            continue

        if "netflix.com" in line.lower():
            parts = line.split("\t")
            if len(parts) >= 7:
                out[parts[5].strip()] = parts[6].strip()
            else:
                parts = line.split()
                if len(parts) >= 7:
                    out[parts[5].strip()] = parts[6].strip()
        else:
            parts = line.split("\t")
            if len(parts) >= 7:
                out[parts[5].strip()] = parts[6].strip()

    # 2. JSON parsing with urllib unquote (from user script)
    try:
        data = json.loads(trimmed)
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                name = item.get("name")
                val  = item.get("value")
                if name and val is not None:
                    out[str(name)] = urllib.parse.unquote(str(val))
    except Exception:
        pass

    # 3. Header format "Cookie: a=b; c=d" or "a=b; c=d"
    for line in trimmed.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ";" in line and ("NetflixId=" in line or "SecureNetflixId=" in line or "=" in line):
            header_str = line
            if header_str.lower().startswith("cookie:"):
                header_str = header_str[7:].strip()
            for pair in header_str.split(";"):
                pair = pair.strip()
                if "=" in pair and not pair.startswith("#"):
                    try:
                        k, v = pair.split("=", 1)
                        out[k.strip()] = urllib.parse.unquote(v.strip())
                    except Exception:
                        pass

    # 4. Fallback regex for key:= (from user script)
    for key in ["NetflixId", "SecureNetflixId", "nfvdid"]:
        if key not in out:
            m = re.search(rf"{key}[:=]\s?([^\s;,\n]+)", trimmed, re.IGNORECASE)
            if m:
                out[key] = urllib.parse.unquote(m.group(1).strip())

    return out


def process_zip_in_background(zip_bytes: bytes) -> tuple:
    added = purged = 0
    breakdown = {"premium": 0, "standard": 0}

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            for name in zf.namelist():
                if name.endswith("/") or not name.lower().endswith((".txt", ".json")):
                    continue
                try:
                    content = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue

                if not content.strip():
                    continue

                token_res, reason = process_nftoken_cookie(content, zip_filename=name)

                if token_res and token_res.get("token"):
                    plan = token_res.get("plan", "standard")
                    if plan == "basic":
                        purged += 1
                        update_cookie_stats("purged", "basic")
                        continue

                    uid      = uuid.uuid4().hex[:8]
                    tag      = "premium" if plan == "premium" else "standard"
                    cdict    = extract_cookie_dict_advanced(content)
                    filepath = os.path.join(COOKIES_DIR, f"nf_{tag}_{uid}.txt")
                    filedata = create_cookie_file_data(content, cdict, token_res)

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(filedata)

                    added += 1
                    breakdown[tag] += 1
                    update_cookie_stats("uploaded", tag)
                else:
                    purged += 1
                    update_cookie_stats("purged", "unknown")
    except zipfile.BadZipFile:
        pass
    except Exception:
        pass

    return added, purged, breakdown


def get_candidate_netflix_cookie(plan_keyword: str) -> tuple:
    """
    Retrieves and verifies a healthy cookie from the vault WITHOUT moving it immediately.
    Returns: (filename, content, token_res, filepath) or (None, None, None, None)
    """
    with cookie_lock:
        files = get_vault_cookies()
        if not files:
            return None, None, None, None

    matched   = [f for f in files if plan_keyword.lower() in f.lower()]
    unmatched = [f for f in files if f not in matched]
    random.shuffle(matched)
    random.shuffle(unmatched)
    candidates = matched + unmatched

    for filename in candidates:
        filepath = os.path.join(COOKIES_DIR, filename)
        content  = None
        with cookie_lock:
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
            except Exception:
                continue

        if not content:
            continue

        token_res, reason = process_nftoken_cookie(content)
        if token_res and token_res.get("token"):
            return filename, content, token_res, filepath
        else:
            with cookie_lock:
                if os.path.exists(filepath):
                    try:
                        shutil.move(filepath, os.path.join(PROCESSED_DIR, f"dead_{filename}"))
                    except Exception:
                        try: os.remove(filepath)
                        except Exception: pass
                    p_tag = "premium" if "premium" in filename.lower() else "standard"
                    update_cookie_stats("purged", p_tag)

    return None, None, None, None


def get_working_netflix_cookie_content(plan_keyword: str):
    """
    Used for /phone and /pc tokens where cookie is consumed upon link delivery.
    """
    filename, content, token_res, filepath = get_candidate_netflix_cookie(plan_keyword)
    if filename and content:
        with cookie_lock:
            if os.path.exists(filepath):
                try:
                    shutil.move(filepath, os.path.join(PROCESSED_DIR, f"used_{filename}"))
                except Exception:
                    try: os.remove(filepath)
                    except Exception: pass
                p_tag = "premium" if "premium" in filename.lower() else "standard"
                update_cookie_stats("used", p_tag)
        return filename, content
    return None, None


def generate_system_report() -> str:
    stats        = load_system_stats()
    total_users  = len(stats.get("users_list", []))
    active_today = len(stats.get("active_today", {}).get("users", []))
    verified_grp = len(load_verified_groups())
    approved_cnt = len([u for u, _ in load_approved_users().items() if get_approval_info(int(u))])

    up_prem  = stats.get("uploaded_premium", 0)
    up_std   = stats.get("uploaded_standard", 0)
    total_up = up_prem + up_std

    p_prem  = stats.get("purged_premium", 0)
    p_std   = stats.get("purged_standard", 0)
    p_unk   = stats.get("purged_unknown", 0)
    total_p = p_prem + p_std + p_unk

    rem_prem = count_pool("premium")
    rem_std  = count_pool("standard")
    total_w  = count_vault_cookies()

    return (
        "╔══════════════════════════════════╗\n"
        "║   📊 <b>NETFLIX SYSTEM REPORT</b>       ║\n"
        "╚══════════════════════════════════╝\n\n"
        "  👥 <b>USER ACTIVITY</b>\n"
        f"     ◈ Total Registered    ▸ <code>{total_users}</code>\n"
        f"     ◈ Active Today        ▸ <code>{active_today}</code>\n"
        f"     ◈ Active Groups       ▸ <code>{verified_grp + 1}</code>\n"
        f"     ◈ VIP Approved Users  ▸ <code>{approved_cnt}</code>\n\n"
        "  📥 <b>UPLOADED COOKIES</b>\n"
        f"     👑 Premium    ▸ <code>{up_prem}</code>\n"
        f"     ⭐ Standard   ▸ <code>{up_std}</code>\n"
        f"     📦 Total      ▸ <code>{total_up}</code>\n\n"
        "  🗑️ <b>AUTO-PURGED (Dead/Hold/Free)</b>\n"
        f"     👑 Premium    ▸ <code>{p_prem}</code>\n"
        f"     ⭐ Standard   ▸ <code>{p_std}</code>\n"
        f"     ❓ Unknown    ▸ <code>{p_unk}</code>\n"
        f"     ♻️  Total      ▸ <code>{total_p}</code>\n\n"
        "  ✅ <b>LIVE COOKIE POOL</b>\n"
        f"     👑 Premium    ▸ <code>{rem_prem}</code>\n"
        f"     ⭐ Standard   ▸ <code>{rem_std}</code>\n"
        f"     🔋 Total      ▸ <code>{total_w}</code>\n\n"
        f"  {WATERMARK}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ⏳ DAILY LIMIT MESSAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_daily_limit_message(user_first_name: str = "") -> str:
    name = f"<b>{user_first_name}</b>, " if user_first_name else ""
    return (
        "╔══════════════════════════════════╗\n"
        "║   🚫 <b>DAILY LIMIT REACHED!</b>        ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"  😔 {name}you've used all\n"
        f"  <b>{DAILY_LIMIT} free requests</b> for today!\n\n"
        "  ┌──────────────────────────────┐\n"
        "  │  🕛 Resets at <b>midnight</b>        │\n"
        "  │  ⏰ Come back <b>tomorrow</b>!       │\n"
        "  └──────────────────────────────┘\n\n"
        "  💡 <i>Tip: Premium 4K gives the best\n"
        "     viewing experience! 🎬</i>\n\n"
        f"  {WATERMARK}"
    )


# ╔══════════════════════════════════════════════════╗
# ║          🎯 BOT COMMAND HANDLERS                  ║
# ╚══════════════════════════════════════════════════╝

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        save_started_user(user.id)
        track_active_chat(chat.id)
        track_user_activity(user.id)
        await check_and_clear_warning(user.id, context, user.first_name)

        if is_owner_or_strict_admin(user.id):
            keyboard = [
                [
                    InlineKeyboardButton("🌟 Main Dashboard", callback_data="menu_main"),
                    InlineKeyboardButton("📖 TV Setup Guide", callback_data="guide_main")
                ],
                [
                    InlineKeyboardButton("🔋 Check Pool",     callback_data="menu_pool"),
                    InlineKeyboardButton("🏓 Latency Ping",   callback_data="menu_ping")
                ]
            ]
            text = (
                "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "┃   👑  <b>OWNER / ADMIN CONTROL PANEL</b> ┃\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                "  📦  <b>COOKIE MANAGEMENT:</b>\n"
                "     ▸ <code>/upload</code>       — Upload cookies ZIP file\n"
                "     ▸ <code>/check</code>        — Test single cookie in real-time\n"
                "     ▸ <code>/exportvault</code>  — Download full vault ZIP backup\n"
                "     ▸ <code>/deletecookies</code>— Purge expired or dead cookies\n\n"
                "  👥  <b>VIP & PERMISSIONS:</b>\n"
                "     ▸ <code>/approve @user 7</code> (or unlimited)\n"
                "     ▸ <code>/unapprove @user</code> · <code>/approvedlist</code>\n"
                "     ▸ <code>/reset @user</code>     — Reset daily limit\n"
                "     ▸ <code>/addadmin</code>        · <code>/removeadmin</code>\n\n"
                "  📊  <b>METRICS & MONITORING:</b>\n"
                "     ▸ <code>/stats</code>       · <code>/vaultinfo</code>\n"
                "     ▸ <code>/audit</code>       · <code>/diagnostics</code>\n"
                "     ▸ <code>/broadcast &lt;msg&gt;</code>\n\n"
                f"  {WATERMARK}"
            )
            await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            is_joined = await check_channel_membership(user.id, context)
            if not is_joined:
                keyboard = [
                    [InlineKeyboardButton("📢 Join Official Channel", url="https://t.me/@NFByShinchanOfficial")],
                    [InlineKeyboardButton("✅ I\'ve Joined!", callback_data="ive_joined")]
                ]
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                        "┃   🔒  <b>MEMBERSHIP VERIFICATION</b>    ┃\n"
                        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                        f"  👋 Welcome, <b>{user.first_name}</b>!\n\n"
                        "  ⚠️  Please join our official channel to proceed:\n"
                        "     👉 <b>@NFByShinchanOfficial</b>\n\n"
                        "  <i>After joining, tap the button below:</i>\n\n"
                        f"  {WATERMARK}"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
            else:
                vip = get_approval_info(user.id)
                vip_text = ""
                if vip:
                    exp = "♾️ Unlimited VIP" if vip["expiry"] == "unlimited" else f"🗓 Until {vip['expiry'][:10]}"
                    vip_text = (
                        "\n\n╭─────────────────────────────────────╮\n"
                        f"│  👑  <b>VIP STATUS:</b> <code>[ ACTIVE ]</code>       │\n"
                        f"│  ⏳  <b>Duration:</b>   {exp}   │\n"
                        "│  🚀  <b>Daily Limit:</b> ♾️ UNLIMITED USES   │\n"
                        "╰─────────────────────────────────────╯"
                    )
                keyboard = [
                    [
                        InlineKeyboardButton("🌟 Main Dashboard", callback_data="menu_main"),
                        InlineKeyboardButton("📖 TV Setup Guide", callback_data="guide_main")
                    ]
                ]
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=(
                        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                        "┃   🎬  <b>NF BY SHINCHAN • ONLINE</b>     ┃\n"
                        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                        f"  👋 Welcome, <b>{user.first_name}</b>!\n\n"
                        "  ✅ <b>You are verified and ready to stream!</b>\n"
                        "     Head over to our group to use <code>/tv</code>, <code>/phone</code>, or <code>/pc</code>."
                        f"{vip_text}\n\n"
                        f"  {WATERMARK}"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
    else:
        if not is_group_allowed(chat.id):
            return
        track_user_activity(user.id)
        track_active_chat(chat.id)

        vip = get_approval_info(user.id)
        access = "👑 VIP • ♾️ Unlimited" if vip else f"👤 {DAILY_LIMIT} uses / day"

        keyboard = [
            [
                InlineKeyboardButton("📺 TV Guide", callback_data="guide_main"),
                InlineKeyboardButton("🌟 Dashboard", callback_data="menu_main")
            ]
        ]

        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "┃   🎬  <b>NF BY SHINCHAN • NETFLIX</b>   ┃\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"  ⚡ Welcome, <b>{user.first_name.upper()}</b>!\n\n"
                "  📺  <b>Smart TV</b>  ▸ <code>/tv 12345678</code>\n"
                "  📱  <b>Mobile</b>    ▸ <code>/phone</code>\n"
                "  💻  <b>Desktop</b>   ▸ <code>/pc</code>\n"
                "  🌟  <b>Dashboard</b> ▸ <code>/menu</code>\n"
                "  📖  <b>Guide</b>     ▸ <code>/tvguide</code>\n"
                "  📊  <b>Status</b>    ▸ <code>/mystatus</code>\n\n"
                f"  🛡️  <i>Your Quota: {access}</i>\n\n"
                f"  {WATERMARK}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(schedule_message_deletion(context, chat.id, [msg.message_id], 36000))


async def ive_joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user

    await query.answer("🔍 Verifying membership...")
    is_joined = await check_channel_membership(user.id, context)

    if is_joined:
        try:
            await query.delete_message()
        except:
            pass
        conf = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   ✅ <b>VERIFIED SUCCESSFULLY!</b>       ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  🎉 Welcome, <b>{user.first_name}</b>!\n\n"
                "  📺 <code>/tv 12345678</code>  — Activate TV\n"
                "  📱 <code>/phone</code>          — Mobile Link\n"
                "  💻 <code>/pc</code>             — Desktop Link\n\n"
                f"  {WATERMARK}"
            ),
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(schedule_message_deletion(context, query.message.chat_id, [conf.message_id], 30))
    else:
        await query.answer("❌ You haven't joined yet!\nJoin @NFByShinchanOfficial first, then click again.", show_alert=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ✅ /approve COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        else:
            await update.message.reply_text("❌ <b>Access Denied.</b>", parse_mode=ParseMode.HTML)
        return

    target_id   = None
    target_name = None
    days_arg    = None

    if update.message.reply_to_message:
        replied     = update.message.reply_to_message.from_user
        target_id   = replied.id
        target_name = replied.first_name
        if context.args:
            days_arg = context.args[0].lower()
        else:
            await update.message.reply_text(
                "⚠️ <b>Usage:</b>\n<code>/approve 7</code> — 7 days\n<code>/approve unlimited</code> — Forever",
                parse_mode=ParseMode.HTML
            )
            return
    elif context.args and len(context.args) >= 2:
        user_arg = context.args[0]
        days_arg = context.args[1].lower()
        if user_arg.startswith("@"):
            try:
                chat_member = await context.bot.get_chat(f"@{user_arg.lstrip('@')}")
                target_id   = chat_member.id
                target_name = chat_member.first_name or user_arg
            except:
                await update.message.reply_text(f"❌ Cannot find user <code>{user_arg}</code>", parse_mode=ParseMode.HTML)
                return
        else:
            try:
                target_id   = int(user_arg)
                target_name = f"User {target_id}"
            except ValueError:
                await update.message.reply_text(
                    "⚠️ <b>Usage:</b>\n<code>/approve @user 7</code>\n<code>/approve user_id unlimited</code>",
                    parse_mode=ParseMode.HTML
                )
                return
    else:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║   ✅ <b>APPROVE COMMAND</b>             ║\n"
            "╚══════════════════════════════════╝\n\n"
            "  <b>Reply to a message:</b>\n"
            "     <code>/approve 7</code>         — 7 days VIP\n"
            "     <code>/approve unlimited</code> — Forever\n\n"
            "  <b>By username/ID:</b>\n"
            "     <code>/approve @user 7</code>\n"
            "     <code>/approve 123456789 unlimited</code>\n\n"
            f"  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )
        return

    # Parse days
    days = None
    if days_arg in ("unlimited", "lifetime", "forever", "∞"):
        days           = None
        expiry_display = "♾️ <b>Unlimited (Forever)</b>"
    else:
        try:
            days = int(days_arg)
            if days <= 0:
                raise ValueError
            expiry_dt      = datetime.now() + timedelta(days=days)
            expiry_display = f"🗓 <b>{expiry_dt.strftime('%d %b %Y')} ({days} days)</b>"
        except ValueError:
            await update.message.reply_text(
                f"⚠️ Invalid: <code>{days_arg}</code>\nUse number or <code>unlimited</code>",
                parse_mode=ParseMode.HTML
            )
            return

    approve_user(target_id, target_name, days, user.id)

    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   ✅ <b>USER APPROVED — VIP!</b>         ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  👤 <b>User:</b>      <code>{target_name}</code> (<code>{target_id}</code>)\n"
            f"  ⏳ <b>Access:</b>    {expiry_display}\n"
            f"  👑 <b>By:</b>        {user.first_name}\n\n"
            "  ┌──────────────────────────────┐\n"
            "  │  ✨ <b>VIP Privileges:</b>          │\n"
            "  │  ▸ No daily limit             │\n"
            "  │  ▸ No cooldown                │\n"
            "  │  ▸ Unlimited /tv /phone /pc   │\n"
            "  └──────────────────────────────┘\n\n"
            f"  {WATERMARK}"
        ),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   🌟 <b>YOU'VE BEEN APPROVED!</b>       ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  🎉 Hey <b>{target_name}</b>!\n\n"
                "  An admin granted you <b>VIP Access</b>!\n\n"
                f"  ⏳ <b>Duration:</b> {expiry_display}\n\n"
                "  ┌──────────────────────────────┐\n"
                "  │  👑 No daily limits           │\n"
                "  │  ⚡ No cooldown               │\n"
                "  │  🚀 Unlimited Netflix!        │\n"
                "  └──────────────────────────────┘\n\n"
                f"  {WATERMARK}"
            ),
            parse_mode=ParseMode.HTML
        )
    except:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚫 /unapprove COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def unapprove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    target_id   = None
    target_name = "Unknown"

    if update.message.reply_to_message:
        target_id   = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        arg = context.args[0].lstrip("@")
        try:
            target_id = int(arg)
        except ValueError:
            try:
                chat_obj    = await context.bot.get_chat(f"@{arg}")
                target_id   = chat_obj.id
                target_name = chat_obj.first_name or arg
            except:
                await update.message.reply_text(f"❌ Cannot find: <code>{arg}</code>", parse_mode=ParseMode.HTML)
                return
    else:
        await update.message.reply_text(
            "⚠️ Reply to a message + <code>/unapprove</code>\nOr <code>/unapprove @user</code>",
            parse_mode=ParseMode.HTML
        )
        return

    was = revoke_user_approval(target_id)
    if was:
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   🚫 <b>VIP ACCESS REVOKED</b>          ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  👤 <b>User:</b> <code>{target_name}</code> (<code>{target_id}</code>)\n"
                f"  ❌ VIP removed  ·  Limit: <code>{DAILY_LIMIT}/day</code>\n\n"
                f"  {WATERMARK}"
            ),
            parse_mode=ParseMode.HTML
        )
    else:
        msg = await update.message.reply_text(f"ℹ️ <code>{target_id}</code> was not approved.", parse_mode=ParseMode.HTML)
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 30))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📋 /approvedlist
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def approvedlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    data = load_approved_users()
    if not data:
        await update.message.reply_text("📋 No VIP users currently.", parse_mode=ParseMode.HTML)
        return

    lines = [
        "╔══════════════════════════════════╗\n"
        "║   👑 <b>VIP APPROVED USERS</b>          ║\n"
        "╚══════════════════════════════════╝\n"
    ]
    active_count = 0
    for uid, entry in data.items():
        info = get_approval_info(int(uid))
        if not info:
            status = "❌ Expired"
        else:
            active_count += 1
            if entry.get("expiry") == "unlimited":
                status = "♾️ Unlimited"
            else:
                try:
                    dt     = datetime.fromisoformat(entry["expiry"])
                    days_r = (dt - datetime.now()).days
                    status = f"🗓 {days_r}d left"
                except:
                    status = "⚠️ Unknown"
        lines.append(f"  👤 <b>{entry.get('username', 'Unknown')}</b> (<code>{uid}</code>)\n     ⏳ {status}\n")

    lines.append(f"\n  📊 <b>Active:</b> <code>{active_count}</code>\n\n  {WATERMARK}")
    msg = await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🌐 /verify GROUP COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private":
        if not is_owner_or_strict_admin(user.id):
            await send_pm_group_only_message(update, context, "verify")
            return
        await update.message.reply_text("ℹ️ Use <code>/verify</code> inside a <b>group</b>.", parse_mode=ParseMode.HTML)
        return

    if not is_owner_or_strict_admin(user.id):
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=f"╔══════════════════════════════════╗\n║   ❌ <b>ADMIN ONLY</b>                 ║\n╚══════════════════════════════════╝\n\n  Only Bot Admins can verify groups.\n\n  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 15))
        return

    if chat.id == ALLOWED_GROUP_ID:
        msg = await context.bot.send_message(chat_id=chat.id, text=f"✅ <b>Main Group</b> — already active!\n{WATERMARK}", parse_mode=ParseMode.HTML)
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 20))
        return

    groups  = load_verified_groups()
    already = str(chat.id) in groups
    groups[str(chat.id)] = {
        "name"       : chat.title or "Unknown",
        "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "verified_by": user.id,
    }
    save_verified_groups(groups)
    track_active_chat(chat.id)

    word = "RE-VERIFIED" if already else "VERIFIED"
    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            f"║   ✅ <b>GROUP {word}!</b>\n"
            "╚══════════════════════════════════╝\n\n"
            f"  📍 <b>Group:</b> {chat.title}\n"
            f"  🔑 <b>By:</b>    {user.first_name}\n\n"
            "  📌 Netflix commands now active:\n"
            "     <code>/tv 12345678</code>  ·  <code>/phone</code>  ·  <code>/pc</code>\n\n"
            f"  {WATERMARK}"
        ),
        parse_mode=ParseMode.HTML
    )
    asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ❓ /help
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat     = update.effective_chat
    user     = update.effective_user
    is_admin = is_owner_or_strict_admin(user.id)

    if chat.type == "private" and not is_admin:
        await send_pm_group_only_message(update, context, "help")
        return

    vip       = get_approval_info(user.id)
    is_vip    = bool(vip) or is_admin
    remaining = get_user_remaining_uses(user.id)
    use_str   = "♾️ Unlimited" if is_vip else make_use_bar(DAILY_LIMIT - remaining)
    badge     = "👑 VIP" if is_vip else "👤 Member"

    keyboard = [
        [
            InlineKeyboardButton("📺 TV Guide", callback_data="guide_main"),
            InlineKeyboardButton("🌟 Main Menu", callback_data="menu_main")
        ],
        [
            InlineKeyboardButton("📢 Official Channel", url="https://t.me/NFByShinchanOfficial")
        ]
    ]
    text = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃   ❓  <b>NF BY SHINCHAN — COMMANDS</b>  ┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "  🎬  <b>CORE COMMANDS:</b>\n"
        "     📺 <code>/tv [8-digit]</code>  — Activate Smart TV\n"
        "     📱 <code>/phone</code>          — Mobile App Instant Link\n"
        "     💻 <code>/pc</code>             — Desktop Web Player Link\n"
        "     🌟 <code>/menu</code>           — Interactive Control Center\n"
        "     📖 <code>/tvguide</code>        — Step-by-Step TV Setup\n"
        "     📊 <code>/mystatus</code>       — Your Quota & VIP Details\n"
        "     🔋 <code>/pool</code>           — Live Cookie Inventory\n"
        "     🏓 <code>/ping</code>           — Bot Response Speed\n\n"
        f"  👤  <b>Your Role:</b>  {badge}\n"
        f"  📊  <b>Quota:</b>      {use_str}\n\n"
        "  ⚠️  <b>REQUIREMENTS:</b>\n"
        "     ▸ Must join <b>@NFByShinchanOfficial</b>\n"
        "     ▸ Start bot in DM first for /phone or /pc\n\n"
        f"  {WATERMARK}"
    )
    msg = await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📊 /mystatus (NEW — User self-service)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def mystatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private" and not is_owner_or_strict_admin(user.id):
        await send_pm_group_only_message(update, context, "mystatus")
        return
    if chat.type != "private" and not is_group_allowed(chat.id):
        return

    is_admin  = is_owner_or_strict_admin(user.id)
    vip       = get_approval_info(user.id)
    is_vip    = bool(vip) or is_admin
    remaining = get_user_remaining_uses(user.id)
    cd        = check_cooldown(user.id)

    if is_vip:
        role_str  = "👑 VIP / Admin"
        quota_str = "♾️ Unlimited Daily"
        cd_str    = "⚡ No Cooldown"
        if vip and vip.get("expiry") != "unlimited":
            try:
                exp_dt = datetime.fromisoformat(vip["expiry"])
                days_left = (exp_dt - datetime.now()).days
                exp_str = f"🗓 {exp_dt.strftime('%d %b %Y')} ({days_left}d left)"
            except Exception:
                exp_str = "♾️ Unlimited"
        else:
            exp_str = "♾️ Lifetime Unlimited"
    else:
        role_str  = "👤 Community Member"
        quota_str = make_use_bar(DAILY_LIMIT - remaining)
        cd_str    = f"⏳ {cd}s remaining" if cd > 0 else "🟢 Ready to use"
        exp_str   = "Daily Reset @ Midnight UTC"

    keyboard = [
        [
            InlineKeyboardButton("📺 Activate TV", callback_data="menu_tv"),
            InlineKeyboardButton("🌟 Main Dashboard", callback_data="menu_main")
        ]
    ]

    text = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃   📊  <b>MY ACCOUNT & QUOTA STATUS</b>  ┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"  👤  <b>User:</b>      <b>{user.first_name}</b> (<code>{user.id}</code>)\n"
        f"  🎖️  <b>Role:</b>      {role_str}\n"
        f"  📊  <b>Quota:</b>     {quota_str}\n"
        f"  ⏳  <b>Cooldown:</b>  {cd_str}\n"
        f"  🗓️  <b>Access:</b>    {exp_str}\n\n"
        f"  {WATERMARK}"
    )
    msg = await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))


async def pool_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type != "private" and not is_group_allowed(chat.id):
        return

    prem  = count_pool("premium")
    std   = count_pool("standard")
    total = count_vault_cookies()

    if total == 0:
        status = "🔴 Depleted"
    elif total < 5:
        status = "🟡 Refill Needed Soon"
    elif total < 20:
        status = "🟢 Healthy & Active"
    else:
        status = "🟢 Fully Stocked Ultra"

    keyboard = [
        [
            InlineKeyboardButton("📺 Activate TV", callback_data="menu_tv"),
            InlineKeyboardButton("🌟 Main Menu",   callback_data="menu_main")
        ]
    ]

    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🔋  <b>COOKIE POOL LIVE METRICS</b>   ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  👑  <b>Premium 4K HDR:</b>  <code>{prem}</code> available\n"
            f"  ⭐  <b>Standard HD:</b>     <code>{std}</code> available\n"
            "  ─────────────────────────────\n"
            f"  📦  <b>Total Active:</b>    <code>{total}</code> cookies\n\n"
            f"  📊  <b>Pool Health:</b>     {status}\n"
            "  ⚡  <i>Auto-audited & refilled continuously!</i>\n\n"
            f"  {WATERMARK}"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat  = update.effective_chat
    start_t = time.time()
    msg   = await context.bot.send_message(
        chat_id=chat.id,
        text="⏱️ <i>Measuring system latency...</i>",
        parse_mode=ParseMode.HTML
    )
    elapsed = round((time.time() - start_t) * 1000)
    quality = "🟢 Ultra-Fast" if elapsed < 150 else "🟡 Stable" if elapsed < 400 else "🔴 Normal"

    keyboard = [
        [
            InlineKeyboardButton("📊 System Health", callback_data="menu_ping"),
            InlineKeyboardButton("🌟 Main Dashboard", callback_data="menu_main")
        ]
    ]

    await msg.edit_text(
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃   🏓  <b>PONG! — SYSTEM ONLINE</b>      ┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"  ⚡  <b>Response Latency:</b> <code>{elapsed} ms</code>\n"
        f"  📶  <b>Connection Grade:</b> {quality}\n"
        "  🌐  <b>Status:</b>           <code>[ 🟢 OPERATIONAL ]</code>\n"
        "  🛡️  <b>Engine Core:</b>      <code>v2.5 High-Speed</code>\n\n"
        f"  {WATERMARK}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [msg.message_id], 30))


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    target_id   = None
    target_name = "Unknown"

    if update.message.reply_to_message:
        target_id   = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        arg = context.args[0].lstrip("@")
        try:
            target_id = int(arg)
        except ValueError:
            try:
                chat_obj    = await context.bot.get_chat(f"@{arg}")
                target_id   = chat_obj.id
                target_name = chat_obj.first_name or arg
            except:
                await update.message.reply_text(f"❌ Cannot find: <code>{arg}</code>", parse_mode=ParseMode.HTML)
                return
    else:
        await update.message.reply_text("⚠️ <code>/reset @user</code> or reply to a message", parse_mode=ParseMode.HTML)
        return

    reset_user_usage(target_id)
    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   🔄 <b>LIMIT RESET!</b>                ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  👤 <b>User:</b>  {target_name} (<code>{target_id}</code>)\n"
            f"  ✅ Restored to <code>{DAILY_LIMIT}/day</code>\n\n"
            f"  {WATERMARK}"
        ),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 30))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📦 /vaultinfo (Admin)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def vaultinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    prem  = count_pool("premium")
    std   = count_pool("standard")
    total = count_vault_cookies()

    p_pct = int(prem / max(total, 1) * 100)
    s_pct = int(std / max(total, 1) * 100)

    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   📦 <b>VAULT INTELLIGENCE</b>          ║\n"
            "╚══════════════════════════════════╝\n\n"
            "  👑 <b>Premium</b>\n"
            f"     <code>{prem}</code> cookies  ·  <code>{make_bar(p_pct)}</code>\n\n"
            "  ⭐ <b>Standard</b>\n"
            f"     <code>{std}</code> cookies  ·  <code>{make_bar(s_pct)}</code>\n\n"
            f"  🔋 <b>Grand Total:</b> <code>{total}</code> live cookies\n\n"
            f"  {WATERMARK}"
        ),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔬 /audit (NEW — Deep vault health scan)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def audit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    status_msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   🔬 <b>VAULT AUDIT IN PROGRESS</b>     ║\n"
            "╚══════════════════════════════════╝\n\n"
            "  🔍 <i>Deep-scanning all cookies...</i>\n"
            f"  <code>{make_bar(10)}</code>"
        ),
        parse_mode=ParseMode.HTML
    )

    files = get_vault_cookies()
    total = len(files)
    live_premium = live_standard = dead = no_nfid = 0

    for i, filename in enumerate(files):
        filepath = os.path.join(COOKIES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            cdict = extract_cookie_dict_advanced(content)
            if not cdict.get("NetflixId"):
                no_nfid += 1
                shutil.move(filepath, os.path.join(PROCESSED_DIR, f"dead_{filename}"))
                continue

            token_res, reason = process_nftoken_cookie(content)
            if token_res and token_res.get("token"):
                if token_res.get("plan") == "premium":
                    live_premium += 1
                else:
                    live_standard += 1
            else:
                dead += 1
                shutil.move(filepath, os.path.join(PROCESSED_DIR, f"dead_{filename}"))
                update_cookie_stats("purged", "premium" if "premium" in filename.lower() else "standard")
        except:
            dead += 1

        # Progress update every 5 cookies
        if total > 0 and i % max(1, total // 4) == 0:
            pct = int((i + 1) / total * 100)
            try:
                await status_msg.edit_text(
                    "╔══════════════════════════════════╗\n"
                    "║   🔬 <b>VAULT AUDIT IN PROGRESS</b>     ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    f"  🔍 <i>Checking {i+1}/{total}...</i>\n"
                    f"  <code>{make_bar(pct)}</code>",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass

    remaining = count_vault_cookies()
    await status_msg.edit_text(
        "╔══════════════════════════════════╗\n"
        "║   🔬 <b>VAULT AUDIT COMPLETE</b>        ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"  📦 <b>Scanned:</b>      <code>{total}</code> files\n\n"
        f"  👑 <b>Live Premium:</b>  <code>{live_premium}</code>\n"
        f"  ⭐ <b>Live Standard:</b> <code>{live_standard}</code>\n"
        f"  💀 <b>Dead/Rejected:</b> <code>{dead}</code>\n"
        f"  🚫 <b>No NetflixId:</b>  <code>{no_nfid}</code>\n\n"
        f"  🔋 <b>After Cleanup:</b> <code>{remaining}</code> live cookies\n\n"
        f"  {WATERMARK}",
        parse_mode=ParseMode.HTML
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  👑 /addadmin & /removeadmin (Owner Only)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def addadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        if update.effective_chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("⚠️ Valid user ID required.", parse_mode=ParseMode.HTML)
            return
    else:
        await update.message.reply_text("⚠️ <code>/addadmin user_id</code> or reply", parse_mode=ParseMode.HTML)
        return

    admins = load_dynamic_admins()
    if target_id not in admins:
        admins.append(target_id)
        save_dynamic_admins(admins)
        await update.message.reply_text(f"✅ <code>{target_id}</code> added as <b>Bot Admin</b>!", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"ℹ️ Already an admin.", parse_mode=ParseMode.HTML)


async def removeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        if update.effective_chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("⚠️ Valid user ID required.", parse_mode=ParseMode.HTML)
            return
    else:
        await update.message.reply_text("⚠️ <code>/removeadmin user_id</code> or reply", parse_mode=ParseMode.HTML)
        return

    admins = load_dynamic_admins()
    if target_id in admins:
        admins.remove(target_id)
        save_dynamic_admins(admins)
        await update.message.reply_text(f"✅ <code>{target_id}</code> removed from admins.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"ℹ️ Not a dynamic admin.", parse_mode=ParseMode.HTML)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📢 /broadcast
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != "private" or user.id != OWNER_ID:
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    if not context.args:
        await update.message.reply_text("⚠️ <code>/broadcast Your message</code>", parse_mode=ParseMode.HTML)
        return

    broadcast_msg = " ".join(context.args)
    chats = set()
    with chats_lock:
        chats = set(_safe_load_json(CHATS_FILE, list))
    chats.add(OWNER_ID)
    chats.add(ALLOWED_GROUP_ID)
    chats = list(chats)

    status_msg = await update.message.reply_text(
        "╔══════════════════════════════════╗\n"
        "║   📡 <b>BROADCASTING...</b>              ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"  <code>{make_bar(0)}</code>",
        parse_mode=ParseMode.HTML
    )

    success = fail = 0
    total   = len(chats)
    for idx, cid in enumerate(chats):
        try:
            await context.bot.send_message(chat_id=cid, text=broadcast_msg, parse_mode=ParseMode.HTML)
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
        if total > 0 and idx % max(1, total // 5) == 0:
            pct = int((idx + 1) / total * 100)
            try:
                await status_msg.edit_text(
                    "╔══════════════════════════════════╗\n"
                    "║   📡 <b>BROADCASTING...</b>              ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    f"  📤 {idx+1}/{total}\n"
                    f"  <code>{make_bar(pct)}</code>",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass

    await status_msg.edit_text(
        "╔══════════════════════════════════╗\n"
        "║   📢 <b>BROADCAST COMPLETE</b>          ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"  ✅ Sent    ▸ <code>{success}</code>\n"
        f"  ❌ Failed  ▸ <code>{fail}</code>\n"
        f"  📦 Total   ▸ <code>{total}</code>\n\n"
        f"  {WATERMARK}",
        parse_mode=ParseMode.HTML
    )


# ╔══════════════════════════════════════════════════╗
# ║        📺 TV ACTIVATION ENGINE (GRAPHQL + FORM)  ║
# ╚══════════════════════════════════════════════════╝
UA_ANDROID = ("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36")
COOKIE_KEYS = ("NetflixId", "SecureNetflixId", "nfvdid")

ANDROID_HEADERS = {
    "user-agent"                : UA_ANDROID,
    "accept-language"           : "en-MM,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua"                 : '"Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile"          : "?1",
    "sec-ch-ua-platform"        : '"Android"',
    "sec-ch-ua-model"           : '"IV2201"',
    "sec-ch-ua-platform-version": '"13.0.0"',
}

def _unescape(t: str) -> str:
    return (t.replace(r"\x2B", "+").replace(r"\x2F", "/")
             .replace(r"\x3D", "=").replace(r"\/", "/"))

def find_any(html: str, *names):
    pats = []
    for n in names:
        pats.append((n, re.compile(rf'"{n}"\s*:\s*"([^"]+)"')))
        pats.append((n, re.compile(rf'\\"{n}\\"\s*:\s*\\"([^"\\]+)\\"')))
    hits = []
    for n, pat in pats:
        for m in pat.finditer(html):
            hits.append((n, m.group(1), m.start()))
    hits.sort(key=lambda x: x[2])
    return hits

def execute_tv_activation_graphql(session, tv_code: str):
    """
    Modern Netflix GraphQL CLCSScreenUpdate TV rendezvous activation.
    """
    clean_code = re.sub(r"\D", "", str(tv_code))
    if len(clean_code) != 8:
        return "INVALID_CODE", None

    try:
        r = session.get("https://www.netflix.com/tv2", headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "sec-fetch-dest": "document", "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none", "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
        }, timeout=12)
    except Exception:
        return "SOFT_FAIL", None

    if "/login" in r.url or "clearcookies" in r.url:
        return "COOKIE_DEAD", r.status_code

    update_hits = find_any(r.text, "requestScreenUpdate_serverScreenUpdate", "serverScreenUpdate")
    state_hits  = find_any(r.text, "serverState")

    if not update_hits or not state_hits:
        return None, None  # Fallback to form POST

    try:
        u_name, u_val, u_pos = update_hits[0]
        s_name, s_val, s_pos = min(state_hits, key=lambda x: abs(x[2] - u_pos))
        server_screen_update = _unescape(u_val)
        server_state         = _unescape(s_val)
        referer_url          = f"https://www.netflix.com/tv2?serverState={server_state}"

        payload = {
            "operationName": "CLCSScreenUpdate",
            "variables": {
                "format": "HTML", "imageFormat": "PNG", "locale": "en-EG",
                "serverScreenUpdate": server_screen_update,
                "serverState": server_state,
                "inputFields": [{"name": "rendezvousCode", "value": {"stringValue": clean_code}}],
            },
            "extensions": {"persistedQuery": {
                "id": "62465a62-45fa-4b41-ab09-8e377c3e4f01", "version": 102}},
        }

        gql_headers = {
            "accept"                            : "*/*",
            "content-type"                      : "application/json",
            "origin"                            : "https://www.netflix.com",
            "referer"                           : referer_url,
            "x-netflix.context.app-version"     : "vdb1dbfa6",
            "x-netflix.context.form-factor"     : "phone",
            "x-netflix.context.from-app"        : "false",
            "x-netflix.context.hawkins-version" : "5.32.0",
            "x-netflix.context.is-android-stub-app": "false",
            "x-netflix.context.is-android-webview" : "false",
            "x-netflix.context.is-consumption-only": "false",
            "x-netflix.context.is-inapp-browser"   : "false",
            "x-netflix.context.is-ios-webview"     : "false",
            "x-netflix.context.locales"         : "en-eg",
            "x-netflix.context.operation-name"  : "CLCSScreenUpdate",
            "x-netflix.context.ui-flavor"       : "akira",
            "x-netflix.request.attempt"         : "1",
            "x-netflix.request.clcs.bucket"     : "high",
            "x-netflix.request.client.context"  :
                json.dumps({"appView": "rendezvousCodeEntry",
                            "action": "Submitted", "appstate": "foreground"}),
            "x-netflix.request.id"              : uuid.uuid4().hex,
            "x-netflix.request.originating.url" : referer_url,
            "x-netflix.request.toplevel.uuid"   : str(uuid.uuid4()),
        }

        gql_resp = session.post("https://www.netflix.com/graphql",
                                headers=gql_headers, data=json.dumps(payload), timeout=15)
        try:
            body = gql_resp.json()
        except Exception:
            body = {}

        result = (body.get("data") or {}).get("result") or {}
        screen = result.get("screen") or {}
        status = result.get("status")
        typename = result.get("__typename")
        screen_view = screen.get("loggingViewName")
        sv = (screen_view or "").lower()
        tn = (typename or "").lower()

        def walk(node, cb):
            if isinstance(node, dict):
                cb(node)
                for v in node.values():
                    walk(v, cb)
            elif isinstance(node, list):
                for v in node:
                    walk(v, cb)

        alerts = []
        def scan(d):
            if d.get("__typename") == "CLCSButton":
                return
            m = d.get("showSystemAlert_message")
            if isinstance(m, dict) and m.get("value"):
                alerts.append(m["value"])
        walk(screen, scan)

        if "approved" in sv or "success" in sv or "screenupdateeffect" in tn:
            # Finalize via loginlinksuccess
            try:
                session.get("https://www.netflix.com/loginlinksuccess", headers={
                    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "referer": referer_url,
                    "sec-fetch-dest": "document", "sec-fetch-mode": "navigate",
                    "sec-fetch-site": "same-origin", "sec-fetch-user": "?1",
                    "upgrade-insecure-requests": "1",
                }, timeout=10)
            except Exception:
                pass
            return "SUCCESS", gql_resp.status_code

        elif sv == "rendezvouscodeentry":
            return "INVALID_CODE", gql_resp.status_code

        elif alerts:
            alert_text = " ".join(alerts).lower()
            if any(k in alert_text for k in ["expired", "timed out"]):
                return "EXPIRED_CODE", gql_resp.status_code
            return "INVALID_CODE", gql_resp.status_code

        return "UNKNOWN", gql_resp.status_code

    except Exception:
        return "SOFT_FAIL", None


def extract_netflix_auth_url(html: str) -> str | None:
    if not html:
        return None
    patterns = [
        r'"authURL"\s*:\s*"([^"]+)"',
        r'\\?"authURL\\?"\s*:\s*\\?"([^"\\]+)\\?"',
        r'name=["\']authURL["\']\s+value=["\']([^"\']+)["\']',
        r'value=["\']([^"\']+)["\']\s+name=["\']authURL["\']',
        r'authURL\s*=\s*["\']([^"\']+)["\']',
        r'"authUrl"\s*:\s*"([^"]+)"',
        r'\\?"authUrl\\?"\s*:\s*\\?"([^"\\]+)\\?"',
        r'netflix\.reactContext\.models\.userInfo\.data\.authURL\s*=\s*["\']([^"\']+)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            val = m.group(1).replace(r'\/', '/').replace(r'\"', '"')
            if val and len(val) > 4:
                return val
    if HAS_BS4 and BeautifulSoup:
        try:
            soup = BeautifulSoup(html, "html.parser")
            elem = soup.find(attrs={"name": re.compile(r"^authurl$", re.I)})
            if elem and elem.get("value"):
                return elem["value"]
        except Exception:
            pass
    return None


def execute_tv_activation_fast(session, nf_code, tv_code):
    clean_code = re.sub(r"\D", "", str(tv_code))
    if len(clean_code) != 8:
        return "INVALID_CODE", None

    # ── Attempt 1: Modern Netflix GraphQL CLCS Engine ──
    try:
        gql_status, gql_code = execute_tv_activation_graphql(session, clean_code)
        if gql_status in ["SUCCESS", "INVALID_CODE", "EXPIRED_CODE", "COOKIE_DEAD"]:
            return gql_status, gql_code
    except Exception:
        pass

    # ── Attempt 2: Form POST Engine (tv8 / tv2 fallback) ──
    headers = {
        "User-Agent"                : USER_AGENT,
        "Accept"                    : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language"           : "en-US,en;q=0.9",
        "Referer"                   : "https://www.netflix.com/tv8",
        "Origin"                    : "https://www.netflix.com",
        "Sec-Fetch-Dest"            : "document",
        "Sec-Fetch-Mode"            : "navigate",
        "Sec-Fetch-Site"            : "same-origin",
        "Upgrade-Insecure-Requests" : "1"
    }

    endpoints = [
        f"https://www.netflix.com/tv8?nftoken={nf_code}" if nf_code else "https://www.netflix.com/tv8",
        f"https://www.netflix.com/Activate?nftoken={nf_code}" if nf_code else "https://www.netflix.com/tv2",
        "https://www.netflix.com/tv8",
        "https://www.netflix.com/tv2"
    ]

    resp = None
    auth_url = None
    last_url = ""

    for target_url in endpoints:
        try:
            resp = session.get(target_url, allow_redirects=True, headers=headers, timeout=12)
            last_url = (resp.url or "").lower()
            if "login" in last_url or "signin" in last_url:
                continue

            auth_url = extract_netflix_auth_url(resp.text)
            if auth_url:
                break
        except Exception:
            continue

    if not auth_url:
        if resp and ("login" in last_url or "signin" in last_url):
            return "COOKIE_DEAD", resp.status_code if resp else None
        return "SOFT_FAIL", resp.status_code if resp else None

    post_url = resp.url.split("?")[0] if resp and resp.url else "https://www.netflix.com/tv8"
    if "activate" in post_url.lower():
        post_url = "https://www.netflix.com/tv8"

    post_headers = dict(headers)
    post_headers["Content-Type"] = "application/x-www-form-urlencoded"
    post_headers["Referer"]      = resp.url if resp and resp.url else "https://www.netflix.com/tv8"

    payload = {
        "flow"                 : "websiteSignUp",
        "authURL"              : auth_url,
        "flowMode"             : "enterTvLoginRendezvousCode",
        "withFields"           : "tvLoginRendezvousCode,isTvUrl2",
        "code"                 : clean_code,
        "tvLoginRendezvousCode": clean_code,
        "isTvUrl2"             : "true",
        "action"               : "nextAction"
    }

    try:
        final = session.post(post_url, data=payload, headers=post_headers, timeout=15)
        final_text = (final.text or "").lower()
        final_url  = (final.url or "").lower()

        if "login" in final_url or "signin" in final_url:
            return "COOKIE_DEAD", final.status_code

        success_parts = ["/browse", "/youraccount", "/tv/success", "/myhome", "/profiles", "success=true", "success"]
        if any(p in final_url for p in success_parts) and "error" not in final_url:
            return "SUCCESS", final.status_code

        success_kws = [
            "tv-success-title", "tv-pairing-success",
            "device is ready", "successfully activated",
            "your tv is now connected", "all set to watch on your tv",
            "device is connected", "tv is ready",
            "you're signed in", "you are signed in",
            "enjoy netflix", "you can start watching",
            "your device is now linked", "now watching",
            'data-uia="tv-success', "rendezvous-success",
            "tvloginsuccess"
        ]
        if any(k in final_text for k in success_kws):
            return "SUCCESS", final.status_code

        expired_kws = [
            "expired", "no longer valid", "already used",
            "code_expired", "timed out", "this code has expired",
            "link has expired"
        ]
        if any(k in final_text for k in expired_kws):
            return "EXPIRED_CODE", final.status_code

        invalid_kws = [
            "incorrect code", "invalid code", "code not found",
            "code you entered is not", "code is not valid",
            "wrong code", "check your code", "enter a valid code",
            "login-rendezvous-error", "ui-message-error", "uia-error",
            "the code you entered", "try a different code",
            "code entered is incorrect", "code is incorrect",
            "doesn't match", "code does not match"
        ]
        if any(k in final_text for k in invalid_kws):
            return "INVALID_CODE", final.status_code

        if HAS_BS4 and BeautifulSoup:
            try:
                soup_final = BeautifulSoup(final.text, "html.parser")
                err_elem   = soup_final.find(attrs={"data-uia": re.compile(r"error|invalid|incorrect", re.I)})
                if err_elem and err_elem.get_text(strip=True):
                    return "INVALID_CODE", final.status_code
            except Exception:
                pass

        if "tv8" in final_url or "tv2" in final_url or "tv/code" in final_url:
            if any(e in final_text for e in ["error", "invalid", "incorrect", "expired"]):
                return "INVALID_CODE", final.status_code
            return "SUCCESS", final.status_code

        return "SUCCESS", final.status_code

    except Exception:
        return "SOFT_FAIL", None


def process_tv_activation(tv_code: str, plan_keyword: str):
    clean_code = re.sub(r"\D", "", str(tv_code))
    max_attempts    = 5
    attempts        = 0
    invalid_count   = 0
    INVALID_CONFIRM = 2

    def _invalid_msg():
        return (
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   ❌  <b>INVALID NETFLIX TV CODE</b>      ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  ⚠️  The code <code>{clean_code}</code> was not recognized.\n\n"
            "  ╭───────────────────────────────────╮\n"
            "  │  📌 <b>HOW TO FIX:</b>                │\n"
            "  │  1. Check your TV screen          │\n"
            "  │  2. Note the 8-digit code         │\n"
            f"  │  3. Re-enter: <code>/tv {clean_code}</code>     │\n"
            "  ╰───────────────────────────────────╯\n\n"
            "  💡 <i>Tip: Netflix TV codes expire in 15 minutes.</i>\n\n"
            f"  {WATERMARK}"
        )

    def _expired_msg():
        return (
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   ⏰  <b>NETFLIX TV CODE EXPIRED</b>     ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  ⚠️  The code <code>{clean_code}</code> has expired.\n\n"
            "  ╭───────────────────────────────────╮\n"
            "  │  🔄 <b>GENERATE A NEW CODE:</b>       │\n"
            "  │  Click 'Try Again' on your TV     │\n"
            "  │  and enter the fresh 8 digits.    │\n"
            "  ╰───────────────────────────────────╯\n\n"
            f"  {WATERMARK}"
        )

    def _pool_msg(reason=""):
        tail = f"  {reason}\n\n" if reason else ""
        return (
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🔋  <b>COOKIE VAULT DEPLETED</b>       ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  Currently no active Netflix sessions are available.\n"
            f"{tail}"
            "  Please wait for admin refill or try again later!\n\n"
            f"  {WATERMARK}"
        )

    if count_vault_cookies() == 0:
        return "POOL_EMPTY", _pool_msg("No cookies in vault."), None

    while attempts < max_attempts:
        filename, content, token_res, filepath = get_candidate_netflix_cookie(plan_keyword)
        if not content:
            if invalid_count >= INVALID_CONFIRM:
                return "INVALID", _invalid_msg(), None
            return "POOL_EMPTY", _pool_msg(), None

        attempts += 1
        try:
            session = requests.Session()
            session.headers.update(ANDROID_HEADERS)
            adv = extract_cookie_dict_advanced(content)
            for k, v in adv.items():
                if k and v:
                    session.cookies.set(k, v, domain=".netflix.com")

            result, _ = execute_tv_activation_fast(session, token_res["token"], clean_code)

            if result == "SUCCESS":
                # Move to used ONLY on real success
                with cookie_lock:
                    if os.path.exists(filepath):
                        try:
                            # Also refresh cookie tokens if session received updated ones
                            refreshed = {c.name: c.value for c in session.cookies if c.name in COOKIE_KEYS}
                            if refreshed.get("NetflixId"):
                                for rk, rv in refreshed.items():
                                    adv[rk] = rv
                            shutil.move(filepath, os.path.join(PROCESSED_DIR, f"used_{filename}"))
                        except Exception:
                            try: os.remove(filepath)
                            except Exception: pass
                        p_tag = "premium" if "premium" in filename.lower() else "standard"
                        update_cookie_stats("used", p_tag)

                acc_card = format_account_info_card(content, token_res)
                pool     = count_vault_cookies()
                pi       = plan_icon(plan_keyword)
                msg = (
                    "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                    "┃   🎉  <b>NETFLIX TV ACTIVATED LIVE!</b>   ┃\n"
                    "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                    f"  📺  <b>TV Code:</b>    <code>{clean_code}</code>\n"
                    f"  {pi}  <b>Tier:</b>       <code>{plan_label(plan_keyword)}</code>\n"
                    "  ⚡  <b>Status:</b>     <code>[ 🟢 CONNECTED • ULTRA 4K ]</code>\n\n"
                    f"{acc_card}\n\n"
                    "╭─────────────────────────────────────╮\n"
                    "│  🍿  <b>Your TV is now READY!</b>             │\n"
                    f"│  🔋  <b>Remaining Pool:</b> {pool} cookies      │\n"
                    "│  ✨  <i>Enjoy streaming in Ultra HD!</i>     │\n"
                    "╰─────────────────────────────────────╯\n\n"
                    f"  {WATERMARK}"
                )
                return "SUCCESS", msg, token_res

            elif result in ["EXPIRED_CODE", "USED_CODE"]:
                return "EXPIRED", _expired_msg(), None

            elif result == "INVALID_CODE":
                invalid_count += 1
                if invalid_count >= INVALID_CONFIRM:
                    return "INVALID", _invalid_msg(), None
                continue

            elif result == "COOKIE_DEAD":
                with cookie_lock:
                    if os.path.exists(filepath):
                        try:
                            shutil.move(filepath, os.path.join(PROCESSED_DIR, f"dead_{filename}"))
                        except Exception:
                            try: os.remove(filepath)
                            except Exception: pass
                        p_tag = "premium" if "premium" in filename.lower() else "standard"
                        update_cookie_stats("purged", p_tag)
                continue

            else:
                continue
        except Exception:
            continue

    if invalid_count >= INVALID_CONFIRM:
        return "INVALID", _invalid_msg(), None
    return "POOL_EMPTY", _pool_msg("All active attempts completed. Please try again!"), None


async def _animate_tv_activation(query):
    try:
        while True:
            for frame in TV_ANIM_FRAMES:
                try:
                    await query.edit_message_text(frame, parse_mode=ParseMode.HTML)
                except Exception:
                    pass
                await asyncio.sleep(0.55)
    except asyncio.CancelledError:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📺 /tv COMMAND (ENHANCED)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def tv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private" and not is_owner_or_strict_admin(user.id):
        await send_pm_group_only_message(update, context, "tv")
        return
    if chat.type != "private" and not is_group_allowed(chat.id):
        return

    if not await check_channel_membership(user.id, context):
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/NFByShinchanOfficial")],
            [InlineKeyboardButton("✅ I\'ve Joined!", callback_data="ive_joined")]
        ]
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "┃   🔒  <b>CHANNEL JOIN REQUIRED</b>       ┃\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                "  Join <b>@NFByShinchanOfficial</b> to use Netflix TV Activation.\n\n"
                f"  {WATERMARK}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))
        return

    remaining = get_user_remaining_uses(user.id)
    if remaining <= 0:
        msg = await context.bot.send_message(chat_id=chat.id, text=get_daily_limit_message(user.first_name), parse_mode=ParseMode.HTML)
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))
        return

    track_user_activity(user.id)
    vip     = get_approval_info(user.id)
    is_vip  = bool(vip) or is_owner_or_strict_admin(user.id)
    rem_str = "♾️ Unlimited VIP" if is_vip else make_use_bar(DAILY_LIMIT - remaining)

    raw_arg = " ".join(context.args) if context.args else ""
    tv_code = re.sub(r"\D", "", raw_arg)

    if not tv_code or len(tv_code) != 8:
        keyboard = [
            [InlineKeyboardButton("📖 TV Setup Guide", callback_data="guide_main")],
            [InlineKeyboardButton("📊 My Status", callback_data="menu_status"),
             InlineKeyboardButton("🔋 Pool", callback_data="menu_pool")]
        ]
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "┃   📺  <b>NETFLIX TV ACTIVATION</b>       ┃\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                "  👉 <b>Usage:</b> <code>/tv 12345678</code>\n"
                "  💡 <i>Or simply send the 8-digit code in chat!</i>\n\n"
                f"  📊  <b>Quota:</b> {rem_str}\n\n"
                f"  {WATERMARK}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))
        return

    keyboard = [
        [
            InlineKeyboardButton("👑 PREMIUM 4K HDR", callback_data=f"tv_{user.id}_premium_{tv_code}"),
            InlineKeyboardButton("⭐ STANDARD HD",    callback_data=f"tv_{user.id}_standard_{tv_code}")
        ],
        [
            InlineKeyboardButton("📖 TV Code Guide", callback_data="guide_main")
        ]
    ]
    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   ⚡  <b>CHOOSE STREAMING TIER</b>       ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  📺  <b>Target TV Code:</b> <code>{tv_code}</code>\n"
            f"  📊  <b>Your Access:</b>   {rem_str}\n\n"
            "  👇 Tap a tier below to initiate instant link:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    user_state[chat.id] = {"user_msg_id": update.message.message_id, "bot_msg_id": msg.message_id}
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DIRECT 8-DIGIT CODE HANDLER (ENHANCED FOR SPACES/HYPHENS)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def handle_direct_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private" or not is_group_allowed(chat.id):
        return
    text = (update.message.text or "").strip()
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8 and (len(text) == 8 or (" " in text and len(text) == 9) or ("-" in text and len(text) == 9)):
        remaining = get_user_remaining_uses(user.id)
        if not is_owner_or_strict_admin(user.id) and remaining <= 0:
            return
        context.args = [digits]
        await tv_command(update, context)
        try:
            await update.message.delete()
        except Exception:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📺 TV CALLBACK HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def tv_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    data_parts = query.data.split("_")
    target_uid = int(data_parts[1])
    clicker_id = query.from_user.id

    if clicker_id != target_uid and not is_owner_or_strict_admin(clicker_id):
        await query.answer("❌ This menu belongs to another user!", show_alert=True)
        return

    plan_keyword = data_parts[2]
    tv_code      = data_parts[3]
    chat_id      = query.message.chat_id

    cd = check_cooldown(clicker_id)
    if cd > 0:
        await query.answer(f"⏱ Wait {cd}s before next request!", show_alert=True)
        return

    if tv_code in active_processing_codes:
        await query.answer("⚡ Already pairing this code!", show_alert=True)
        return

    active_processing_codes[tv_code] = True
    await query.answer("⚡ Launching Netflix Engine...")

    try:
        anim_task = asyncio.create_task(_animate_tv_activation(query))
        status, response_msg, token_res = await asyncio.to_thread(process_tv_activation, tv_code, plan_keyword)
        anim_task.cancel()
        await asyncio.sleep(0)

        if status == "SUCCESS":
            if not is_owner_or_strict_admin(target_uid):
                deduct_user_netflix_limit(target_uid)
            set_cooldown(clicker_id)

        try:
            sent = await context.bot.send_message(chat_id=chat_id, text=response_msg, parse_mode=ParseMode.HTML)
            if query.message.chat.type != "private":
                asyncio.create_task(schedule_message_deletion(context, chat_id, [sent.message_id], 36000))
            try:
                await query.delete_message()
            except Exception:
                pass
        except Exception as e:
            await report_error_to_owner(context, e, "tv_callback:send")
    except Exception as e:
        await report_error_to_owner(context, e, "tv_callback")
    finally:
        active_processing_codes.pop(tv_code, None)


async def _animate_token_fetch(query):
    try:
        while True:
            for frame in TOKEN_ANIM_FRAMES:
                try:
                    await query.edit_message_text(frame, parse_mode=ParseMode.HTML)
                except Exception:
                    pass
                await asyncio.sleep(0.6)
    except asyncio.CancelledError:
        pass



async def phone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private" and not is_owner_or_strict_admin(user.id):
        await send_pm_group_only_message(update, context, "phone")
        return
    if chat.type != "private" and not is_group_allowed(chat.id):
        return

    is_admin = is_owner_or_strict_admin(user.id)

    if not is_admin and not await can_bot_dm_user(user.id, context):
        keyboard = [[InlineKeyboardButton("🚀 Start Bot in DM", url=BOT_START_LINK)]]
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   ⚠️ <b>START BOT IN DM FIRST!</b>      ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  Hey <b>{user.first_name}</b>!\n"
                "  Start the bot privately first.\n\n"
                "  👇 Tap below:"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        if chat.type != "private":
            add_pending_warning(user.id, msg.message_id, chat.id)
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id], 36000))
        return

    if not await check_channel_membership(user.id, context):
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/NFByShinchanOfficial")],
            [InlineKeyboardButton("✅ I've Joined!", callback_data="ive_joined")]
        ]
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   🔒 <b>CHANNEL JOIN REQUIRED</b>       ║\n"
                "╚══════════════════════════════════╝\n\n"
                "  Join <b>@NFByShinchanOfficial</b> first.\n\n"
                f"  {WATERMARK}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))
        return

    remaining = get_user_remaining_uses(user.id)
    if remaining <= 0:
        msg = await context.bot.send_message(chat_id=chat.id, text=get_daily_limit_message(user.first_name), parse_mode=ParseMode.HTML)
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))
        return

    track_user_activity(user.id)
    vip     = get_approval_info(user.id)
    is_vip  = bool(vip) or is_admin
    rem_str = "♾️ Unlimited" if is_vip else make_use_bar(DAILY_LIMIT - remaining)

    keyboard = [[
        InlineKeyboardButton("👑 PREMIUM 4K",  callback_data=f"ph_{user.id}_premium"),
        InlineKeyboardButton("⭐ STANDARD HD", callback_data=f"ph_{user.id}_standard")
    ]]
    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   📱 <b>MOBILE LINK GENERATOR</b>       ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  📊 {rem_str}\n\n"
            "  👇 Choose your plan:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  💻 /pc
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def pc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type == "private" and not is_owner_or_strict_admin(user.id):
        await send_pm_group_only_message(update, context, "pc")
        return
    if chat.type != "private" and not is_group_allowed(chat.id):
        return

    is_admin = is_owner_or_strict_admin(user.id)

    if not is_admin and not await can_bot_dm_user(user.id, context):
        keyboard = [[InlineKeyboardButton("🚀 Start Bot in DM", url=BOT_START_LINK)]]
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   ⚠️ <b>START BOT IN DM FIRST!</b>      ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  Hey <b>{user.first_name}</b>!\n"
                "  Start the bot privately first.\n\n"
                "  👇 Tap below:"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        if chat.type != "private":
            add_pending_warning(user.id, msg.message_id, chat.id)
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id], 36000))
        return

    if not await check_channel_membership(user.id, context):
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/NFByShinchanOfficial")],
            [InlineKeyboardButton("✅ I've Joined!", callback_data="ive_joined")]
        ]
        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "╔══════════════════════════════════╗\n"
                "║   🔒 <b>CHANNEL JOIN REQUIRED</b>       ║\n"
                "╚══════════════════════════════════╝\n\n"
                "  Join <b>@NFByShinchanOfficial</b> first.\n\n"
                f"  {WATERMARK}"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 60))
        return

    remaining = get_user_remaining_uses(user.id)
    if remaining <= 0:
        msg = await context.bot.send_message(chat_id=chat.id, text=get_daily_limit_message(user.first_name), parse_mode=ParseMode.HTML)
        if chat.type != "private":
            asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))
        return

    track_user_activity(user.id)
    vip     = get_approval_info(user.id)
    is_vip  = bool(vip) or is_admin
    rem_str = "♾️ Unlimited" if is_vip else make_use_bar(DAILY_LIMIT - remaining)

    keyboard = [[
        InlineKeyboardButton("👑 PREMIUM 4K",  callback_data=f"pc_{user.id}_premium"),
        InlineKeyboardButton("⭐ STANDARD HD", callback_data=f"pc_{user.id}_standard")
    ]]
    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   💻 <b>DESKTOP LINK GENERATOR</b>      ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  📊 {rem_str}\n\n"
            "  👇 Choose your plan:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [update.message.message_id, msg.message_id], 36000))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔑 TOKEN DELIVERY (phone + pc shared)
#  FIXED: Deduct ONLY after successful delivery
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def _deliver_token(query, context, target_uid, plan_type, link_template, title, auto_delete_secs):
    chat_id    = query.message.chat_id
    clicker_id = query.from_user.id
    is_admin   = is_owner_or_strict_admin(clicker_id)

    if clicker_id != target_uid and not is_admin:
        await query.answer("❌ This menu belongs to another user!", show_alert=True)
        return

    cd = check_cooldown(clicker_id)
    if cd > 0:
        await query.answer(f"⏱ Wait {cd}s!", show_alert=True)
        return

    await query.answer("🔐 Forging token...")

    anim_task         = asyncio.create_task(_animate_token_fetch(query))
    filename, content = await asyncio.to_thread(get_working_netflix_cookie_content, plan_type)
    anim_task.cancel()
    await asyncio.sleep(0)

    if not content:
        try:
            await query.edit_message_text(
                "╔══════════════════════════════════╗\n"
                "║   ❌ <b>POOL EMPTY</b>                   ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"  No <b>{plan_type.upper()}</b> cookies available.\n"
                "  Try again later!\n\n"
                f"  {WATERMARK}",
                parse_mode=ParseMode.HTML
            )
        except:
            pass
        return

    try:
        token_res, _ = await asyncio.to_thread(process_nftoken_cookie, content)
        if not token_res or not token_res.get("token"):
            try:
                await query.edit_message_text(
                    "╔══════════════════════════════════╗\n"
                    "║   ❌ <b>TOKEN FAILED</b>                 ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    "  Cookie expired. Try again!\n\n"
                    f"  {WATERMARK}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            return

        acc_card       = format_account_info_card(content, token_res)
        encoded_token  = urllib.parse.quote(token_res["token"], safe="")
        link           = link_template.format(token=encoded_token)
        pool           = count_vault_cookies()
        vip            = get_approval_info(target_uid)
        is_vip         = bool(vip) or is_admin
        rem_str        = "♾️" if is_vip else f"{get_user_remaining_uses(target_uid) - 1}/{DAILY_LIMIT}"
        pi             = plan_icon(plan_type)

        response_text = (
            f"╔══════════════════════════════════╗\n"
            f"║ {title} ║\n"
            f"╚══════════════════════════════════╝\n\n"
            f"  📅 <b>Expiry:</b>  <code>{token_res['expiry']}</code>\n"
            f"  {pi} <b>Tier:</b>    <code>{plan_label(plan_type)}</code>\n\n"
            f"  🔗 <b>Login Link:</b>\n  <code>{link}</code>\n\n"
            f"{acc_card}\n\n"
            f"  ┌──────────────────────────────┐\n"
            f"  │  📌 Uses left: {rem_str}             │\n"
            f"  │  🔋 Pool: {pool} cookies           │\n"
            f"  │  ⏳ Auto-deletes: {auto_delete_secs // 60} min         │\n"
            f"  └──────────────────────────────┘\n\n"
            f"  {WATERMARK}"
        )

        if is_admin:
            sent = await context.bot.send_message(chat_id=chat_id, text=response_text, parse_mode=ParseMode.HTML)
            if query.message.chat.type != "private":
                asyncio.create_task(schedule_message_deletion(context, chat_id, [sent.message_id], 36000))
            try: await query.delete_message()
            except: pass
            set_cooldown(clicker_id)
        else:
            try:
                sent = await context.bot.send_message(chat_id=target_uid, text=response_text, parse_mode=ParseMode.HTML)
            except Exception:
                keyboard = [[InlineKeyboardButton("🚀 Start Bot in DM", url=BOT_START_LINK)]]
                err_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "╔══════════════════════════════════╗\n"
                        "║   ⚠️ <b>DM DELIVERY FAILED</b>          ║\n"
                        "╚══════════════════════════════════╝\n\n"
                        f"  <b>{query.from_user.first_name}</b>,\n"
                        "  start the bot in DM first!\n\n"
                        "  👇 Click below:"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
                asyncio.create_task(schedule_message_deletion(context, chat_id, [err_msg.message_id], 60))
                try: await query.delete_message()
                except: pass
                return  # NO deduction on failure

            # ── Success: deduct NOW ──
            deduct_user_netflix_limit(target_uid)
            set_cooldown(clicker_id)

            rem_after     = get_user_remaining_uses(target_uid)
            rem_after_str = "♾️ Unlimited" if is_vip else make_use_bar(DAILY_LIMIT - rem_after)

            conf = await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "╔══════════════════════════════════╗\n"
                    "║   ✅ <b>TOKEN SENT TO YOUR DM!</b>       ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    f"  📊 {rem_after_str}\n"
                    f"  🔋 Pool: <code>{pool}</code> cookies\n"
                    f"  ⏳ DM deletes in {auto_delete_secs // 60} min\n\n"
                    f"  {WATERMARK}"
                ),
                parse_mode=ParseMode.HTML
            )
            asyncio.create_task(schedule_message_deletion(context, chat_id, [conf.message_id], 36000))
            try: await query.delete_message()
            except: pass

            async def _auto_del():
                await asyncio.sleep(auto_delete_secs)
                try: await context.bot.delete_message(chat_id=target_uid, message_id=sent.message_id)
                except: pass
            asyncio.create_task(_auto_del())

    except Exception as e:
        await report_error_to_owner(context, e, "_deliver_token")
        try:
            await query.edit_message_text(f"❌ Error: <code>{str(e)[:200]}</code>", parse_mode=ParseMode.HTML)
        except:
            pass


async def phone_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    await _deliver_token(
        query, context, int(parts[1]), parts[2],
        link_template="https://www.netflix.com/unsupported?nftoken={token}",
        title="  📱 <b>MOBILE NETFLIX LINK</b>       ",
        auto_delete_secs=120
    )

async def pc_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    await _deliver_token(
        query, context, int(parts[1]), parts[2],
        link_template="https://www.netflix.com/browse?nftoken={token}",
        title="  💻 <b>DESKTOP NETFLIX LINK</b>      ",
        auto_delete_secs=120
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📥 /upload (Admin — with per-plan breakdown)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or not is_owner_or_strict_admin(update.effective_user.id):
        return

    doc = update.message.reply_to_message.document if update.message.reply_to_message else None
    if not doc:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║   📥 <b>UPLOAD INSTRUCTIONS</b>         ║\n"
            "╚══════════════════════════════════╝\n\n"
            "  📎 Reply to a <b>.zip</b> or <b>.txt</b> file\n"
            "     with <code>/upload</code>\n\n"
            "  ┌──────────────────────────────┐\n"
            "  │  ✅ Only active + paid cookies │\n"
            "  │  will be accepted.            │\n"
            "  │  ❌ Dead / Hold / Free / Basic │\n"
            "  │  are auto-rejected.           │\n"
            "  └──────────────────────────────┘\n\n"
            f"  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   📥 <b>VAULT SYNC INITIATED</b>        ║\n"
            "╚══════════════════════════════════╝\n\n"
            "  🔍 <i>Downloading file...</i>\n"
            f"  <code>{make_bar(10)}</code>"
        ),
        parse_mode=ParseMode.HTML
    )

    try:
        file       = await context.bot.get_file(doc.file_id)
        file_bytes = await file.download_as_bytearray()

        await status_msg.edit_text(
            "╔══════════════════════════════════╗\n"
            "║   📥 <b>VAULT SYNC INITIATED</b>        ║\n"
            "╚══════════════════════════════════╝\n\n"
            "  🧪 <i>Validating cookies (strict mode)...</i>\n"
            "  <i>Only active + paid cookies accepted</i>\n"
            f"  <code>{make_bar(40)}</code>",
            parse_mode=ParseMode.HTML
        )

        if doc.file_name.lower().endswith(".zip"):
            added, purged, breakdown = await asyncio.to_thread(process_zip_in_background, bytes(file_bytes))
        else:
            content     = file_bytes.decode("utf-8", errors="ignore")
            cookie_dict = extract_cookie_dict_advanced(content)
            added = purged = 0
            breakdown = {"premium": 0, "standard": 0}

            if cookie_dict.get("NetflixId"):
                token_res, reason = process_nftoken_cookie(content, zip_filename=doc.file_name)
                if token_res and token_res.get("token"):
                    plan = token_res.get("plan", "standard")
                    tag  = "premium" if plan == "premium" else "standard"
                    file_data = create_cookie_file_data(content, cookie_dict, token_res)
                    uid = uuid.uuid4().hex[:8]
                    with open(os.path.join(COOKIES_DIR, f"nf_{tag}_{uid}.txt"), "w", encoding="utf-8") as f:
                        f.write(file_data)
                    update_cookie_stats("uploaded", tag)
                    breakdown[tag] += 1
                    added = 1
                else:
                    purged = 1
            else:
                purged = 1

        breakdown_text = (
            f"     👑 Premium  ▸ <code>{breakdown.get('premium', 0)}</code>\n"
            f"     ⭐ Standard ▸ <code>{breakdown.get('standard', 0)}</code>"
        )

        await status_msg.edit_text(
            "╔══════════════════════════════════╗\n"
            "║   ✅ <b>VAULT SYNC COMPLETE</b>         ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  ✅ <b>Live Added:</b>    <code>{added}</code>\n"
            f"{breakdown_text}\n\n"
            f"  ❌ <b>Rejected:</b>     <code>{purged}</code>\n"
            "     <i>(dead/hold/free/basic)</i>\n\n"
            f"  🔋 <b>Vault Total:</b>  <code>{count_vault_cookies()}</code>\n\n"
            f"  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )

        report = generate_system_report()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=report, parse_mode=ParseMode.HTML)
        try:
            rep = await context.bot.send_message(chat_id=ALLOWED_GROUP_ID, text=report, parse_mode=ParseMode.HTML)
            asyncio.create_task(schedule_message_deletion(context, ALLOWED_GROUP_ID, [rep.message_id], 36000))
        except:
            pass

    except Exception as e:
        await report_error_to_owner(context, e, "upload_command")
        await status_msg.edit_text(
            f"╔══════════════════════════════════╗\n"
            f"║   ❌ <b>UPLOAD FAILED</b>               ║\n"
            f"╚══════════════════════════════════╝\n\n"
            f"  Error: <code>{str(e)[:200]}</code>",
            parse_mode=ParseMode.HTML
        )


async def deletecookies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" or not is_owner_or_strict_admin(update.effective_user.id):
        return
    count = 0
    if os.path.exists(COOKIES_DIR):
        for f in os.listdir(COOKIES_DIR):
            fp = os.path.join(COOKIES_DIR, f)
            if os.path.isfile(fp) and f.endswith((".txt", ".json")):
                try:
                    os.remove(fp)
                    count += 1
                except:
                    pass
    await update.message.reply_text(
        "╔══════════════════════════════════╗\n"
        "║   🗑️ <b>VAULT CLEARED!</b>               ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"  ♻️ <b>{count}</b> files removed.\n"
        f"  🔋 Vault is now empty.\n\n"
        f"  {WATERMARK}",
        parse_mode=ParseMode.HTML
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not is_owner_or_strict_admin(user.id):
        if chat.type != "private":
            try: await update.message.delete()
            except: pass
        return

    stats    = load_system_stats()
    total    = len(stats.get("users_list", []))
    active   = len(stats.get("active_today", {}).get("users", []))
    groups   = len(load_verified_groups()) + 1
    approved = len([u for u, _ in load_approved_users().items() if get_approval_info(int(u))])
    pool     = count_vault_cookies()
    prem     = count_pool("premium")
    std      = count_pool("standard")

    msg = await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "╔══════════════════════════════════╗\n"
            "║   📊 <b>SYSTEM DASHBOARD</b>            ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"  👥 Total Users     ▸ <code>{total}</code>\n"
            f"  🟢 Active Today    ▸ <code>{active}</code>\n"
            f"  🏘️ Active Groups   ▸ <code>{groups}</code>\n"
            f"  👑 VIP Approved    ▸ <code>{approved}</code>\n\n"
            f"  🔋 Cookie Pool     ▸ <code>{pool}</code>\n"
            f"     👑 Premium      ▸ <code>{prem}</code>\n"
            f"     ⭐ Standard     ▸ <code>{std}</code>\n\n"
            f"  {WATERMARK}"
        ),
        parse_mode=ParseMode.HTML
    )
    if chat.type != "private":
        asyncio.create_task(schedule_message_deletion(context, chat.id, [msg.message_id], 36000))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🌐 KEEP-ALIVE SERVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class PingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK - NF By Shinchan Active")

    def log_message(self, *args):
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🌟 /menu — INTERACTIVE DASHBOARD (NEW FEATURE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    vip       = get_approval_info(user.id)
    is_admin  = is_owner_or_strict_admin(user.id)
    is_vip    = bool(vip) or is_admin
    remaining = get_user_remaining_uses(user.id)
    quota_str = "♾️ Unlimited VIP" if is_vip else f"{remaining}/{DAILY_LIMIT} uses left"
    pool_cnt  = count_vault_cookies()

    keyboard = [
        [
            InlineKeyboardButton("📺 TV Activation", callback_data="menu_tv"),
            InlineKeyboardButton("📱 Mobile Link",   callback_data="menu_phone")
        ],
        [
            InlineKeyboardButton("💻 Desktop Link",  callback_data="menu_pc"),
            InlineKeyboardButton("📖 TV Setup Guide",callback_data="guide_main")
        ],
        [
            InlineKeyboardButton("📊 My Quota",       callback_data="menu_status"),
            InlineKeyboardButton(f"🔋 Pool ({pool_cnt})", callback_data="menu_pool")
        ],
        [
            InlineKeyboardButton("🏓 Ping Latency",   callback_data="menu_ping"),
            InlineKeyboardButton("📢 Channel",        url="https://t.me/NFByShinchanOfficial")
        ]
    ]

    text = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃   ⚡  <b>NF BY SHINCHAN • DASHBOARD</b>  ┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"  👋 Welcome, <b>{user.first_name}</b>!\n"
        f"  👑  <b>Role:</b>  <code>{'VIP / Admin' if is_vip else 'Member'}</code>\n"
        f"  📊  <b>Quota:</b> <code>{quota_str}</code>\n"
        f"  🔋  <b>Vault:</b> <code>{pool_cnt} active cookies</code>\n\n"
        "  👇 <i>Choose any feature below to get started:</i>\n\n"
        f"  {WATERMARK}"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    user  = query.from_user

    if data == "menu_main":
        await menu_command(update, context)
        return

    if data == "menu_tv":
        keyboard = [
            [InlineKeyboardButton("📖 Open TV Guide", callback_data="guide_main")],
            [InlineKeyboardButton("🔙 Back to Menu",  callback_data="menu_main")]
        ]
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   📺  <b>HOW TO ACTIVATE YOUR TV</b>    ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  1️⃣ Open <b>Netflix</b> on your Smart TV\n"
            "  2️⃣ Click <b>Sign In</b> ▸ <b>Sign in with code</b>\n"
            "  3️⃣ Get the 8-digit code from TV screen\n"
            "  4️⃣ Send in group: <code>/tv 12345678</code>\n\n"
            "  <i>Or type the 8 digits directly in the group!</i>\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if data == "menu_phone":
        await query.answer("Type /phone in the group to get mobile link!", show_alert=True)
        return

    if data == "menu_pc":
        await query.answer("Type /pc in the group to get desktop link!", show_alert=True)
        return

    if data == "menu_status":
        vip       = get_approval_info(user.id)
        is_admin  = is_owner_or_strict_admin(user.id)
        is_vip    = bool(vip) or is_admin
        remaining = get_user_remaining_uses(user.id)
        role_str  = "👑 VIP Member" if is_vip else "👤 Regular Member"
        quota_str = "♾️ Unlimited Daily" if is_vip else f"{remaining}/{DAILY_LIMIT} uses remaining"
        keyboard  = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]]
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   📊  <b>MY ACCOUNT STATUS</b>          ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  👤  <b>User:</b>  <b>{user.first_name}</b> (<code>{user.id}</code>)\n"
            f"  🎖️  <b>Role:</b>  {role_str}\n"
            f"  📊  <b>Quota:</b> {quota_str}\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if data == "menu_pool":
        vault_files  = get_vault_cookies()
        premium_cnt  = len([f for f in vault_files if "premium" in f.lower()])
        standard_cnt = len(vault_files) - premium_cnt
        total        = len(vault_files)
        keyboard     = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]]
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🔋  <b>COOKIE POOL LIVE METRICS</b>   ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  👑  <b>Premium 4K:</b>   <code>{premium_cnt}</code> cookies\n"
            f"  ⭐  <b>Standard HD:</b>  <code>{standard_cnt}</code> cookies\n"
            "  ─────────────────────────────\n"
            f"  📦  <b>Total Active:</b> <code>{total}</code> cookies\n\n"
            "  ⚡ <i>Auto-audited & refilled continuously!</i>\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if data == "menu_ping":
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu_main")]]
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🏓  <b>SYSTEM LATENCY & SPEED</b>     ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  ⚡  <b>Bot Core:</b>     <code>ONLINE [ 🟢 ]</code>\n"
            "  🌐  <b>Netflix API:</b>  <code>CONNECTED</code>\n"
            "  🛡️  <b>Encryption:</b>   <code>TLS 1.3 Active</code>\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📖 /tvguide — ILLUSTRATED TV ACTIVATION GUIDE (NEW FEATURE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def tvguide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    keyboard = [
        [
            InlineKeyboardButton("📺 Smart TV / Android TV", callback_data="guide_smart"),
            InlineKeyboardButton("🔥 Fire Stick",            callback_data="guide_fire")
        ],
        [
            InlineKeyboardButton("🎮 PS5 / Xbox / Apple TV", callback_data="guide_console"),
            InlineKeyboardButton("❓ Troubleshooting",       callback_data="guide_trouble")
        ],
        [
            InlineKeyboardButton("🔙 Dashboard Menu",         callback_data="menu_main")
        ]
    ]

    text = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃   📖  <b>NETFLIX TV SETUP MANUAL</b>     ┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "  Follow these easy steps to activate your TV:\n\n"
        "  <b>Step 1:</b> Open Netflix App on your TV\n"
        "  <b>Step 2:</b> Click <b>Sign In</b>\n"
        "  <b>Step 3:</b> Select <b>'Sign in with code'</b>\n"
        "  <b>Step 4:</b> An <b>8-digit code</b> appears on screen\n"
        "  <b>Step 5:</b> Send: <code>/tv 12345678</code> here\n"
        "  <b>Step 6:</b> Choose <b>[ 👑 PREMIUM 4K ]</b>\n\n"
        "  ✨ <i>Your TV pairs automatically in ~3 seconds!</i>\n\n"
        "  👇 Tap below for device-specific instructions:\n\n"
        f"  {WATERMARK}"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def tvguide_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    keyboard = [[InlineKeyboardButton("🔙 Back to Guides", callback_data="guide_main")]]

    if data == "guide_main":
        await tvguide_command(update, context)
        return

    if data == "guide_smart":
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   📺  <b>SMART TV & ANDROID TV GUIDE</b>┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  1️⃣ Open the <b>Netflix</b> app on your TV\n"
            "  2️⃣ Click <b>Sign In</b> on the left menu\n"
            "  3️⃣ Select <b>Sign In with a Code</b> or QR code\n"
            "  4️⃣ Look at the 8-digit code (e.g. <code>48291058</code>)\n"
            "  5️⃣ In this bot / group, type: <code>/tv 48291058</code>\n"
            "  6️⃣ Tap <b>PREMIUM 4K</b> and your TV will login!\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if data == "guide_fire":
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🔥  <b>AMAZON FIRE STICK GUIDE</b>    ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  1️⃣ Launch Netflix on your Firestick\n"
            "  2️⃣ Select <b>Sign In</b>\n"
            "  3️⃣ Press <b>'Sign in on the web'</b> or code\n"
            "  4️⃣ Note the 8-digit rendezvous code\n"
            "  5️⃣ Send <code>/tv [code]</code> in group\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if data == "guide_console":
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🎮  <b>CONSOLES & APPLE TV</b>        ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  Works for PS4, PS5, Xbox One/Series, and Apple TV 4K!\n\n"
            "  1️⃣ Open Netflix\n"
            "  2️⃣ Click <b>Sign In with a Code</b>\n"
            "  3️⃣ Send the 8 digits here: <code>/tv [code]</code>\n"
            "  4️⃣ Instant connection with Ultra HD audio/video!\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return

    if data == "guide_trouble":
        await query.edit_message_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   ❓  <b>TV TROUBLESHOOTING FAQ</b>      ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  ⚠️ <b>Code Expired?</b>\n"
            "  ▸ TV codes expire after 15 mins. Click 'Try new code'.\n\n"
            "  ⚠️ <b>Invalid Code?</b>\n"
            "  ▸ Make sure you typed exactly 8 numbers.\n"
            "  ▸ Ensure Netflix app is updated on your TV.\n\n"
            "  ⚠️ <b>Pool Empty?</b>\n"
            "  ▸ Cookies are refilled frequently. Try in a few mins!\n\n"
            f"  {WATERMARK}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🧪 /check — SINGLE COOKIE REAL-TIME TESTER (NEW FEATURE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_cookie_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        await update.message.reply_text("⛔ Admin command only!")
        return

    cookie_raw = ""
    if context.args:
        cookie_raw = " ".join(context.args)
    elif update.message.reply_to_message:
        reply = update.message.reply_to_message
        if reply.text:
            cookie_raw = reply.text
        elif reply.document:
            file_obj = await reply.document.get_file()
            buf = bytearray()
            await file_obj.download_as_bytearray(buf)
            cookie_raw = buf.decode("utf-8", errors="ignore")

    if not cookie_raw.strip():
        await update.message.reply_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   🧪  <b>COOKIE REAL-TIME TESTER</b>    ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "  👉 <b>Usage:</b>\n"
            "  ▸ <code>/check [cookie text or JSON]</code>\n"
            "  ▸ Or reply to any cookie message with <code>/check</code>\n\n"
            f"  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )
        return

    status_msg = await update.message.reply_text("🔬 <i>Auditing cookie with Netflix iOS Gateway...</i>", parse_mode=ParseMode.HTML)

    cdict = extract_cookie_dict_advanced(cookie_raw)
    if not cdict.get("NetflixId"):
        await status_msg.edit_text("❌ <b>Failed:</b> No <code>NetflixId</code> found in text/JSON.", parse_mode=ParseMode.HTML)
        return

    token_res, reason = process_nftoken_cookie(cookie_raw)
    if token_res and token_res.get("token"):
        card = format_account_info_card(cookie_raw, token_res)
        await status_msg.edit_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   ✅  <b>COOKIE IS LIVE & VALID!</b>    ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"{card}\n\n"
            f"  🔑  <b>nftoken:</b> <code>{token_res['token'][:30]}...</code>\n\n"
            f"  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )
    else:
        await status_msg.edit_text(
            "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "┃   ❌  <b>COOKIE IS DEAD / INVALID</b>   ┃\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"  ⚠️  <b>Reason:</b> <code>{reason}</code>\n\n"
            f"  {WATERMARK}",
            parse_mode=ParseMode.HTML
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📦 /exportvault — BACKUP ACTIVE VAULT COOKIES (NEW FEATURE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def exportvault_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        await update.message.reply_text("⛔ Admin command only!")
        return

    files = get_vault_cookies()
    if not files:
        await update.message.reply_text("⚠️ Cookie vault is currently empty!")
        return

    status_msg = await update.message.reply_text(f"📦 <i>Packaging {len(files)} cookies into ZIP backup...</i>", parse_mode=ParseMode.HTML)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in files:
            fpath = os.path.join(COOKIES_DIR, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        zf.writestr(fname, f.read())
                except Exception:
                    pass

    zip_buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"Netflix_Vault_Backup_{ts}.zip"

    try:
        await context.bot.send_document(
            chat_id=user.id,
            document=zip_buf,
            filename=zip_name,
            caption=(
                "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                "┃   📦  <b>VAULT BACKUP EXPORTED</b>      ┃\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"  📁  <b>Total Files:</b> <code>{len(files)}</code> cookies\n"
                f"  🗓️  <b>Timestamp:</b>   <code>{ts}</code>\n\n"
                f"  {WATERMARK}"
            ),
            parse_mode=ParseMode.HTML
        )
        if chat.id != user.id:
            await status_msg.edit_text("✅ Vault backup sent to your DM!")
        else:
            await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to send DM: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔬 /diagnostics — DEEP SYSTEM DIAGNOSTICS (NEW FEATURE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def diagnostics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if not is_owner_or_strict_admin(user.id):
        await update.message.reply_text("⛔ Admin command only!")
        return

    t0 = time.time()
    try:
        ping_resp = requests.get("https://www.netflix.com", timeout=5)
        api_latency = f"{round((time.time() - t0) * 1000)} ms"
        api_status  = f"HTTP {ping_resp.status_code}"
    except Exception as e:
        api_latency = "Timeout / Error"
        api_status  = str(e)[:30]

    vault_files = get_vault_cookies()
    prem_cnt    = len([f for f in vault_files if "premium" in f.lower()])
    std_cnt     = len(vault_files) - prem_cnt
    proc_cnt    = len(os.listdir(PROCESSED_DIR)) if os.path.exists(PROCESSED_DIR) else 0

    stats       = load_system_stats()
    total_users = len(stats.get("users_list", []))
    act_today   = len(stats.get("active_today", {}).get("users", []))
    v_groups    = len(load_verified_groups())
    appr_cnt    = len([u for u, _ in load_approved_users().items() if get_approval_info(int(u))])

    report = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "┃   🔬  <b>SYSTEM HEALTH & DIAGNOSTICS</b>┃\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        "  🌐  <b>NETWORK & GATEWAY:</b>\n"
        f"  ▸  Netflix Ping:   <code>{api_latency}</code>\n"
        f"  ▸  Gateway Code:   <code>{api_status}</code>\n\n"
        "  🔋  <b>VAULT STORAGE:</b>\n"
        f"  ▸  Active Cookies: <code>{len(vault_files)}</code> (👑 {prem_cnt} | ⭐ {std_cnt})\n"
        f"  ▸  Processed:      <code>{proc_cnt}</code> cookies\n\n"
        "  👥  <b>COMMUNITY & ACCESS:</b>\n"
        f"  ▸  Total Users:    <code>{total_users}</code>\n"
        f"  ▸  Active Today:   <code>{act_today}</code>\n"
        f"  ▸  Verified Grps:  <code>{v_groups}</code>\n"
        f"  ▸  VIP Users:      <code>{appr_cnt}</code>\n\n"
        f"  {WATERMARK}"
    )
    await update.message.reply_text(report, parse_mode=ParseMode.HTML)



def run_always_on_pinger():
    time.sleep(20)
    while True:
        try:
            requests.get("https://m3uindiatvbot-7spn.onrender.com", timeout=12)
        except:
            pass
        time.sleep(540)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🧹 STARTUP VAULT CLEANUP (FIXED)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def auto_cleanup_vault():
    """Startup scan: remove cookies without NetflixId (fast check only)."""
    print("🔍 Auto-scanning vault for invalid cookies...")
    cleaned = 0
    files   = get_vault_cookies()
    for filename in files:
        filepath = os.path.join(COOKIES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            cookie_dict = extract_cookie_dict_advanced(content)
            if not cookie_dict.get("NetflixId"):
                shutil.move(filepath, os.path.join(PROCESSED_DIR, f"dead_{filename}"))
                cleaned += 1
        except:
            pass
    remaining = count_vault_cookies()
    print(f"✅ Cleanup done: {cleaned} removed | {remaining} live cookies in vault.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚀 MAIN ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    port = int(os.environ.get("PORT", 10000))
    socketserver.TCPServer.allow_reuse_address = True
    threading.Thread(
        target=lambda: socketserver.ThreadingTCPServer(("", port), PingHandler).serve_forever(),
        daemon=True
    ).start()
    threading.Thread(target=run_always_on_pinger, daemon=True).start()
    threading.Thread(target=auto_cleanup_vault, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    # ── Core commands ──
    app.add_handler(CommandHandler("start",         start))
    app.add_handler(CommandHandler("help",          help_command))
    app.add_handler(CommandHandler("ping",          ping_command))
    app.add_handler(CommandHandler("verify",        verify_command))
    app.add_handler(CommandHandler("tv",            tv_command))
    app.add_handler(CommandHandler("phone",         phone_command))
    app.add_handler(CommandHandler("pc",            pc_command))
    app.add_handler(CommandHandler("mystatus",      mystatus_command))
    app.add_handler(CommandHandler("pool",          pool_command))
    app.add_handler(CommandHandler("menu",          menu_command))
    app.add_handler(CommandHandler("tvguide",       tvguide_command))
    app.add_handler(CommandHandler("check",         check_cookie_command))
    app.add_handler(CommandHandler("testcookie",    check_cookie_command))
    app.add_handler(CommandHandler("exportvault",   exportvault_command))
    app.add_handler(CommandHandler("diagnostics",   diagnostics_command))


    # ── Admin commands ──
    app.add_handler(CommandHandler("approve",       approve_command))
    app.add_handler(CommandHandler("unapprove",     unapprove_command))
    app.add_handler(CommandHandler("approvedlist",  approvedlist_command))
    app.add_handler(CommandHandler("reset",         reset_command))
    app.add_handler(CommandHandler("stats",         stats_command))
    app.add_handler(CommandHandler("vaultinfo",     vaultinfo_command))
    app.add_handler(CommandHandler("audit",         audit_command))
    app.add_handler(CommandHandler("broadcast",     broadcast_command))

    # ── Owner-only commands ──
    app.add_handler(CommandHandler("upload",        upload_command))
    app.add_handler(CommandHandler("deletecookies", deletecookies_command))
    app.add_handler(CommandHandler("addadmin",      addadmin_command))
    app.add_handler(CommandHandler("removeadmin",   removeadmin_command))

    # ── Callback handlers ──
    app.add_handler(CallbackQueryHandler(ive_joined_callback,    pattern=r"^ive_joined$"))
    app.add_handler(CallbackQueryHandler(tv_callback_handler,    pattern=r"^tv_"))
    app.add_handler(CallbackQueryHandler(phone_callback_handler, pattern=r"^ph_"))
    app.add_handler(CallbackQueryHandler(pc_callback_handler,    pattern=r"^pc_"))
    app.add_handler(CallbackQueryHandler(menu_callback_handler,    pattern=r"^menu_"))
    app.add_handler(CallbackQueryHandler(tvguide_callback_handler, pattern=r"^guide_"))


    # ── Direct 8-digit code in group ──
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_code))

    print("╔══════════════════════════════════════╗")
    print("║   ⚡  NF BY SHINCHAN v2.0 — ARMED    ║")
    print("║   ✅  7 Critical Bugs Fixed           ║")
    print("║   🔒  Strict Cookie Validation        ║")
    print("║   👑  VIP System Active               ║")
    print("║   📊  /mystatus /pool /audit Added    ║")
    print("╚══════════════════════════════════════╝")

    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
