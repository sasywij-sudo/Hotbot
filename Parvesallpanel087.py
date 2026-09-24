id                import requests
import logging
import json
import os
import re
import time
import tempfile
import shutil
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.error import TimedOut, RetryAfter, TelegramError
import asyncio

os.system('clear')


# =====================================================
# === CUSTOM EXCEPTIONS ===
# =====================================================
class SessionExpiredError(Exception):
    pass


class ServerDownError(Exception):
    pass


# =====================================================
# === MULTI-BOT SYSTEM ===
# =====================================================
BOT_TOKENS = [
    "7043806851:AAG8_PlGLikGu_XpNDe8GJx59WkVZhNwvks",
]
BOT_TOKENS = [t for t in BOT_TOKENS if t and t.strip()]

CHAT_IDS = [
    '--1003839684911',
]
CHAT_IDS = [c for c in CHAT_IDS if c and c.strip()]

# =====================================================
# === LOGIN-BASED PORTALS ===
# =====================================================
PORTALS = [
    # এখানে নতুন panel add করো
]

# =====================================================
# === API-BASED PORTALS ===
# =====================================================
API_PORTALS = [
    # এখানে নতুন API panel add করো
]

# =====================================================

MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Infinix X6882 Build/UP1A.231005.007) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.159 Mobile Safari/537.36"
)

ALREADY_SENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "already_sent.json")
MAX_ALREADY_SENT = 20000
SAVE_INTERVAL = 30
POLL_INTERVAL = 16         # প্রতি ১৬ সেকেন্ডে refresh (server min 15s required)
RELOGIN_EVERY = 112        # ১১২ × ১৬s = ~৩০ মিনিটে proactive re-login

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')


# =====================================================
# === MULTI-BOT MANAGER ===
# =====================================================
class MultiBotManager:
    def __init__(self, tokens):
        if not tokens:
            raise ValueError("কমপক্ষে একটি BOT_TOKEN দিতে হবে!")
        self.bots = [Bot(token=t) for t in tokens]
        self.current_index = 0
        self.retry_after_times = [0.0] * len(self.bots)
        logging.info(f"🤖 Multi-bot: {len(self.bots)}টি bot লোড হয়েছে")

    def _get_available_bot_index(self):
        now = time.time()
        total = len(self.bots)
        for i in range(total):
            idx = (self.current_index + i) % total
            if now >= self.retry_after_times[idx]:
                return idx
        return min(range(total), key=lambda i: self.retry_after_times[i])

    async def send_message(self, **kwargs):
        total = len(self.bots)
        last_error = None

        for _ in range(total * 3):
            idx = self._get_available_bot_index()
            bot = self.bots[idx]
            now = time.time()

            if now < self.retry_after_times[idx]:
                wait_time = self.retry_after_times[idx] - now
                if total > 1:
                    self.current_index = (idx + 1) % total
                    continue
                else:
                    await asyncio.sleep(wait_time + 0.5)

            try:
                result = await bot.send_message(**kwargs)
                self.current_index = idx
                return result

            except RetryAfter as e:
                wait = e.retry_after + 1
                self.retry_after_times[idx] = time.time() + wait
                logging.warning(f"🚫 Bot #{idx+1} rate limited {wait}s — পরের bot-এ যাচ্ছি...")
                self.current_index = (idx + 1) % total
                last_error = e
                await asyncio.sleep(0.3)

            except TimedOut:
                logging.warning(f"⌛ Bot #{idx+1} timeout — retry...")
                last_error = TimedOut("timed out")
                await asyncio.sleep(2)

            except TelegramError as e:
                logging.error(f"❌ Bot #{idx+1} error: {e}")
                last_error = e
                await asyncio.sleep(3)
                self.current_index = (idx + 1) % total

        raise last_error or TelegramError("সব bot দিয়ে চেষ্টা করেও পাঠানো গেলো না")


bot_manager = MultiBotManager(BOT_TOKENS)

# === Country Code Map ===
COUNTRY_MAP = {
    '880': '🇧🇩 Bangladesh',
    '971': '🇦🇪 UAE',
    '966': '🇸🇦 Saudi Arabia',
    '977': '🇳🇵 Nepal',
    '975': '🇧🇹 Bhutan',
    '976': '🇲🇳 Mongolia',
    '974': '🇶🇦 Qatar',
    '973': '🇧🇭 Bahrain',
    '972': '🇮🇱 Israel',
    '970': '🇵🇸 Palestine',
    '968': '🇴🇲 Oman',
    '967': '🇾🇪 Yemen',
    '965': '🇰🇼 Kuwait',
    '964': '🇮🇶 Iraq',
    '963': '🇸🇾 Syria',
    '962': '🇯🇴 Jordan',
    '961': '🇱🇧 Lebanon',
    '960': '🇲🇻 Maldives',
    '886': '🇹🇼 Taiwan',
    '856': '🇱🇦 Laos',
    '855': '🇰🇭 Cambodia',
    '267': '🇧🇼 Botswana',
    '268': '🇸🇿 Eswatini',
    '263': '🇿🇼 Zimbabwe',
    '260': '🇿🇲 Zambia',
    '258': '🇲🇿 Mozambique',
    '256': '🇺🇬 Uganda',
    '255': '🇹🇿 Tanzania',
    '254': '🇰🇪 Kenya',
    '251': '🇪🇹 Ethiopia',
    '250': '🇷🇼 Rwanda',
    '244': '🇦🇴 Angola',
    '243': '🇨🇩 DR Congo',
    '237': '🇨🇲 Cameroon',
    '234': '🇳🇬 Nigeria',
    '233': '🇬🇭 Ghana',
    '230': '🇲🇺 Mauritius',
    '225': "🇨🇮 Côte d'Ivoire",
    '221': '🇸🇳 Senegal',
    '218': '🇱🇾 Libya',
    '216': '🇹🇳 Tunisia',
    '213': '🇩🇿 Algeria',
    '212': '🇲🇦 Morocco',
    '261': '🇲🇬 Madagascar',
    '98': '🇮🇷 Iran',
    '95': '🇲🇲 Myanmar',
    '94': '🇱🇰 Sri Lanka',
    '93': '🇦🇫 Afghanistan',
    '92': '🇵🇰 Pakistan',
    '91': '🇮🇳 India',
    '90': '🇹🇷 Turkey',
    '86': '🇨🇳 China',
    '84': '🇻🇳 Vietnam',
    '82': '🇰🇷 South Korea',
    '81': '🇯🇵 Japan',
    '66': '🇹🇭 Thailand',
    '65': '🇸🇬 Singapore',
    '64': '🇳🇿 New Zealand',
    '63': '🇵🇭 Philippines',
    '62': '🇮🇩 Indonesia',
    '61': '🇦🇺 Australia',
    '60': '🇲🇾 Malaysia',
    '58': '🇻🇪 Venezuela',
    '57': '🇨🇴 Colombia',
    '56': '🇨🇱 Chile',
    '55': '🇧🇷 Brazil',
    '54': '🇦🇷 Argentina',
    '53': '🇨🇺 Cuba',
    '52': '🇲🇽 Mexico',
    '51': '🇵🇪 Peru',
    '49': '🇩🇪 Germany',
    '48': '🇵🇱 Poland',
    '47': '🇳🇴 Norway',
    '46': '🇸🇪 Sweden',
    '45': '🇩🇰 Denmark',
    '44': '🇬🇧 United Kingdom',
    '43': '🇦🇹 Austria',
    '41': '🇨🇭 Switzerland',
    '40': '🇷🇴 Romania',
    '39': '🇮🇹 Italy',
    '36': '🇭🇺 Hungary',
    '34': '🇪🇸 Spain',
    '33': '🇫🇷 France',
    '32': '🇧🇪 Belgium',
    '31': '🇳🇱 Netherlands',
    '30': '🇬🇷 Greece',
    '27': '🇿🇦 South Africa',
    '20': '🇪🇬 Egypt',
    '7': '🇷🇺 Russia / Kazakhstan',
    '1': '🇺🇸 USA / Canada',
}


def mask_number(number: str) -> str:
    digits = re.sub(r'\D', '', number)
    if len(digits) <= 7:
        return number
    return digits[:3] + '•••••' + digits[-4:]


def get_country_info(number: str):
    raw = str(number).strip()
    # Remove leading +, 00, or spaces
    if raw.startswith('+'):
        raw = raw[1:]
    elif raw.startswith('00'):
        raw = raw[2:]
    # Remove any non-digit characters
    digits = re.sub(r'\D', '', raw)
    # Remove leading 0 if number is likely local format
    if len(digits) > 10 and digits.startswith('0'):
        digits = digits[1:]
    for code in sorted(COUNTRY_MAP.keys(), key=lambda x: -len(x)):
        if digits.startswith(code):
            val = COUNTRY_MAP[code]
            parts = val.split(' ', 1)
            flag = parts[0]
            name = parts[1] if len(parts) > 1 else val
            return flag, name
    return '🌍', f'Unknown ({digits[:6]})'


def escape_html(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def save_already_sent(already_sent: set):
    data = list(already_sent)
    if len(data) > MAX_ALREADY_SENT:
        data = data[-MAX_ALREADY_SENT:]
        already_sent.clear()
        already_sent.update(data)
    try:
        dir_name = os.path.dirname(ALREADY_SENT_FILE)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, suffix='.tmp') as tf:
            json.dump(data, tf)
            tmp_path = tf.name
        shutil.move(tmp_path, ALREADY_SENT_FILE)
    except Exception as e:
        logging.warning(f"already_sent save error: {e}")


def load_already_sent() -> set:
    if os.path.exists(ALREADY_SENT_FILE):
        try:
            with open(ALREADY_SENT_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            logging.warning(f"already_sent load error (fresh start): {e}")
    return set()


# =====================================================
# === ACTIVE NUMBER → USER MAPPING (varson3 shared file) ===
# =====================================================
# varson3 saves active number assignments to data/active_numbers.json
# relative to its own folder. Since both scripts live in the same dir,
# we read the same file to route OTP directly to the correct Telegram user.

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVE_NUMBERS_FILE = os.path.join(_SCRIPT_DIR, "data", "active_numbers.json")

# varson3's bot token — used to deliver OTP to the specific user
VARSON3_BOT_TOKEN = "7908883848:AAE-_Hs8l9QEQoXlEr7eeDpal2acck7DHt4"


def normalize_phone(number: str) -> str:
    digits = re.sub(r"\D", "", str(number or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("01") and len(digits) == 11:
        digits = "880" + digits[1:]
    return digits


def find_user_for_number(number: str):
    """
    data/active_numbers.json পড়ে number-এর জন্য user_id ফেরত দেয়।
    15 মিনিটের বেশি পুরানো assignment ignore করে।
    Returns: (user_id: int, meta: dict) or (None, None)
    """
    try:
        if not os.path.exists(ACTIVE_NUMBERS_FILE):
            return None, None
        with open(ACTIVE_NUMBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None, None

    key = normalize_phone(number)
    if not key:
        return None, None

    now = int(time.time())
    meta = data.get(key)
    if not meta:
        return None, None

    # 15 মিনিট expiry check
    assigned_at = int(meta.get("assigned_at", 0))
    if now - assigned_at > 15 * 60:
        return None, None

    try:
        return int(meta["user_id"]), meta
    except (KeyError, ValueError, TypeError):
        return None, None


def extract_sesskey(html: str) -> str:
    import urllib.parse

    # ১. sAjaxSource URL থেকে sesskey বের করি
    ajax_m = re.search(r'sAjaxSource\s*["\']?\s*[:\s]+["\']([^"\']+)["\']', html)
    if ajax_m:
        ajax_url = ajax_m.group(1)
        if 'sesskey=' in ajax_url:
            qs = ajax_url.split('?', 1)[-1] if '?' in ajax_url else ajax_url
            parsed = urllib.parse.parse_qs(qs)
            if 'sesskey' in parsed:
                return urllib.parse.unquote(parsed['sesskey'][0])

    # ২. সরাসরি URL query string থেকে
    qs_m = re.search(r'[?&]sesskey=([A-Za-z0-9+/=%]{8,})(?:[&"\'\s<]|$)', html)
    if qs_m:
        return urllib.parse.unquote(qs_m.group(1))

    # ৩. JS variable / JSON key থেকে
    for pat in [
        r'"sesskey"\s*:\s*"([A-Za-z0-9+/=]{8,})"',
        r"'sesskey'\s*:\s*'([A-Za-z0-9+/=]{8,})'",
        r'sesskey\s*[=:]\s*["\']([A-Za-z0-9+/=]{8,})["\']',
    ]:
        m = re.search(pat, html)
        if m:
            return urllib.parse.unquote(m.group(1))

    return ""


def solve_captcha(html: str):
    patterns = [
        r'[Ww]hat\s+is\s+(\d+)\s*(\+|\-)\s*(\d+)',
        r'(\d+)\s*(\+|\-)\s*(\d+)\s*[=?]',
        r'[Cc]aptcha[^0-9]*(\d+)\s*(\+|\-)\s*(\d+)',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            a = int(m.group(1))
            op = m.group(2)
            b = int(m.group(3))
            result = a + b if op == '+' else a - b
            logging.info(f"    Captcha: {a} {op} {b} = {result}")
            return result
    return None


def extract_otp(message: str) -> str | None:
    text = str(message)

    m = re.search(
        r'(?:otp|code|pin|password|passcode|verification|verify|token)'
        r'[\s:is#\-]*(\d{3,4})[\s\-–](\d{3,4})',
        text, re.IGNORECASE
    )
    if m:
        return m.group(1) + m.group(2)

    m = re.search(
        r'(?:otp|code|pin|password|passcode|verification|verify|token)'
        r'[\s:is#\-]*(\d{4,8})(?!\d)',
        text, re.IGNORECASE
    )
    if m:
        return m.group(1)

    m = re.search(r'(?<!\d)(\d{3,4})[\s\-–](\d{3,4})(?!\d)', text)
    if m:
        return m.group(1) + m.group(2)

    m = re.search(r'(?<!\d)(\d{4,8})(?!\d)', text)
    if m:
        return m.group(1)

    return None


# =====================================================
# === LOGIN-BASED PORTAL CLASS ===
# =====================================================
class Portal:
    def __init__(self, config):
        self.name = config["name"]
        self.base_url = config["url"].rstrip('/')
        self.username = config["username"]
        self.password = config["password"]
        self.login_page = self.base_url + "/ints/login"
        self.login_post = self.base_url + "/ints/signin"
        self.data_url = self.base_url + "/ints/agent/res/data_smscdr.php"
        self.dashboard_url = self.base_url + "/ints/agent/SMSDashboard"
        self.reports_url = self.base_url + "/ints/agent/SMSCDRReports"
        self.sesskey = ""
        self._logged_in = False
        self.session = self._new_session()
        self.col_date    = config.get("col_date",    0)
        self.col_number  = config.get("col_number",  2)
        self.col_service = config.get("col_service", 3)
        self.col_message = config.get("col_message", 5)

    def _new_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": MOBILE_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        return s

    def _reset_session(self):
        self.session.close()
        self.session = self._new_session()
        self.sesskey = ""
        self._logged_in = False

    def login(self) -> bool:
        self._reset_session()
        try:
            try:
                resp = self.session.get(self.login_page, timeout=20, allow_redirects=True)
            except requests.exceptions.ConnectionError:
                logging.error(f"[{self.name}] Connection refused — server may be down.")
                return False
            except requests.exceptions.Timeout:
                logging.error(f"[{self.name}] Login page timeout.")
                return False

            if resp.status_code in (502, 503, 504):
                logging.warning(f"[{self.name}] Server unavailable ({resp.status_code}).")
                return False

            captcha_answer = solve_captcha(resp.text)
            if captcha_answer is None:
                logging.warning(f"[{self.name}] Captcha not found — trying without.")
                captcha_answer = ""

            crlf_token = ""
            crlf_m = re.search(r"name=['\"]crlf['\"]\s+value=['\"]([a-f0-9]{20,})['\"]", resp.text)
            if crlf_m:
                crlf_token = crlf_m.group(1)

            payload = {
                "username": self.username,
                "password": self.password,
                "capt": captcha_answer,
            }
            if crlf_token:
                payload["crlf"] = crlf_token

            try:
                login_resp = self.session.post(
                    self.login_post,
                    data=payload,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": self.login_page,
                        "Origin": self.base_url,
                    },
                    timeout=20,
                    allow_redirects=True,
                )
            except requests.exceptions.Timeout:
                logging.error(f"[{self.name}] Login POST timeout.")
                return False

            if login_resp.status_code in (502, 503, 504):
                logging.warning(f"[{self.name}] Server unavailable after POST.")
                return False

            final_url = login_resp.url.lower()
            resp_text_lower = login_resp.text.lower()

            success_signals = [
                "dashboard" in final_url,
                "/agent/" in final_url,
                "smsdashboard" in final_url,
                "logout" in resp_text_lower,
                "sign out" in resp_text_lower,
                "signout" in resp_text_lower,
                "welcome" in resp_text_lower,
                "sms dashboard" in resp_text_lower,
            ]
            fail_signals = [
                "/ints/login" in final_url,
                "/ints/signin" in final_url,
                "invalid username" in resp_text_lower,
                "invalid password" in resp_text_lower,
                "incorrect password" in resp_text_lower,
                "wrong password" in resp_text_lower,
                "authentication failed" in resp_text_lower,
            ]

            if any(success_signals) and not any(fail_signals):
                logging.info(f"[{self.name}] ✅ Login successful")
                self._logged_in = True
                self._capture_sesskey(login_resp.text)
                return True
            else:
                snippet = login_resp.text[:300].replace('\n', ' ').strip()
                logging.error(f"[{self.name}] ❌ Login failed | {snippet}")
                return False

        except Exception as e:
            logging.error(f"[{self.name}] Login error: {e}")
            return False

    def _capture_sesskey(self, login_html: str):
        key = extract_sesskey(login_html)
        try:
            # সবসময় Dashboard + Reports page চেক করি (sAjaxSource-এ sesskey থাকে)
            if not key:
                dash = self.session.get(self.dashboard_url, timeout=15, allow_redirects=True)
                key = extract_sesskey(dash.text)

            rep = self.session.get(
                self.reports_url,
                headers={"Referer": self.dashboard_url},
                timeout=15,
                allow_redirects=True,
            )
            rep_key = extract_sesskey(rep.text)
            if rep_key:
                key = rep_key  # Reports page থেকে পাওয়া sesskey সবচেয়ে নির্ভরযোগ্য
        except Exception as e:
            logging.warning(f"[{self.name}] sesskey capture error: {e}")

        if key:
            self.sesskey = key
            logging.info(f"[{self.name}] sesskey ✅ ({key[:12]}...)")
        else:
            logging.warning(f"[{self.name}] sesskey not found.")

    def _is_session_expired(self, resp) -> bool:
        final_url = resp.url.lower()
        text_lower = resp.text.lower()
        return (
            "/ints/login" in final_url
            or "/ints/signin" in final_url
            or resp.status_code in (401, 403)
            or (resp.text.strip().startswith('<') and 'login' in text_lower and 'logout' not in text_lower)
        )

    def fetch_data(self, _retry: bool = False):
        today = datetime.now().strftime("%Y-%m-%d")
        params = {
            'fdate1': f"{today} 00:00:00",
            'fdate2': f"{today} 23:59:59",
            'frange': "", 'fclient': "", 'fnum': "", 'fcli': "",
            'fgdate': "", 'fgmonth': "", 'fgrange': "", 'fgclient': "",
            'fgnumber': "", 'fgcli': "", 'fg': "0",
            'sEcho': "1", 'iColumns': "9", 'sColumns': ",,,,,,,,",
            'iDisplayStart': "0", 'iDisplayLength': "100",
            'mDataProp_0': "0", 'sSearch_0': "", 'bRegex_0': "false", 'bSearchable_0': "true", 'bSortable_0': "true",
            'mDataProp_1': "1", 'sSearch_1': "", 'bRegex_1': "false", 'bSearchable_1': "true", 'bSortable_1': "true",
            'mDataProp_2': "2", 'sSearch_2': "", 'bRegex_2': "false", 'bSearchable_2': "true", 'bSortable_2': "true",
            'mDataProp_3': "3", 'sSearch_3': "", 'bRegex_3': "false", 'bSearchable_3': "true", 'bSortable_3': "true",
            'mDataProp_4': "4", 'sSearch_4': "", 'bRegex_4': "false", 'bSearchable_4': "true", 'bSortable_4': "true",
            'mDataProp_5': "5", 'sSearch_5': "", 'bRegex_5': "false", 'bSearchable_5': "true", 'bSortable_5': "true",
            'mDataProp_6': "6", 'sSearch_6': "", 'bRegex_6': "false", 'bSearchable_6': "true", 'bSortable_6': "true",
            'mDataProp_7': "7", 'sSearch_7': "", 'bRegex_7': "false", 'bSearchable_7': "true", 'bSortable_7': "true",
            'mDataProp_8': "8", 'sSearch_8': "", 'bRegex_8': "false", 'bSearchable_8': "true", 'bSortable_8': "false",
            'sSearch': "", 'bRegex': "false",
            'iSortCol_0': "0", 'sSortDir_0': "desc", 'iSortingCols': "1",
            '_': str(int(time.time() * 1000)),
        }
        if self.sesskey:
            params['sesskey'] = self.sesskey

        try:
            resp = self.session.get(
                self.data_url, params=params,
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": self.reports_url,
                },
                timeout=20,
                allow_redirects=True,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logging.warning(f"[{self.name}] Network error: {type(e).__name__}")
            return None
        except Exception as e:
            logging.error(f"[{self.name}] Fetch error: {e}")
            return None

        if resp.status_code in (502, 503, 504):
            raise ServerDownError(f"HTTP {resp.status_code}")

        if self._is_session_expired(resp):
            if _retry:
                raise SessionExpiredError("Session expired even after re-login")
            logging.warning(f"[{self.name}] 🔄 Session expired — re-logging...")
            if self.login():
                return self.fetch_data(_retry=True)
            else:
                raise SessionExpiredError("Re-login failed")

        if resp.status_code != 200:
            logging.error(f"[{self.name}] HTTP {resp.status_code}")
            return None

        try:
            return resp.json()
        except Exception:
            snippet = resp.text[:300].replace('\n', ' ')
            logging.error(f"[{self.name}] JSON error | {snippet}")
            return None


# =====================================================
# === API-BASED PORTAL CLASS ===
# =====================================================
class ApiPortal:
    def __init__(self, config):
        self.name = config["name"]
        self.base_url = config["url"]
        self.token = config["token"]
        self.api_type = config.get("type", "viewstats")
        self.records = config.get("records", 50)
        self.col_date = config.get("col_date", 0)
        self.col_number = config.get("col_number", 2)
        self.col_service = config.get("col_service", 3)
        self.col_message = config.get("col_message", 5)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": MOBILE_UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "X-Requested-With": "XMLHttpRequest",
        })

    def login(self) -> bool:
        logging.info(f"[{self.name}] Token-based API — no login needed ✅")
        return True

    def fetch_data(self, _retry: bool = False):
        today = datetime.now().strftime("%Y-%m-%d")
        date_start = f"{today} 00:00:00"
        date_end   = f"{today} 23:59:59"

        if self.api_type == "pscall":
            params = {
                "key": self.token,
                "start": 0,
                "length": self.records,
            }
        elif self.api_type == "mdr":
            params = {
                "token": self.token,
                "fromdate": date_start,
                "todate": date_end,
                "searchnumber": "",
                "searchcli": "",
                "records": self.records,
            }
        else:
            params = {
                "token": self.token,
                "dt1": date_start,
                "dt2": date_end,
                "records": self.records,
            }

        try:
            resp = self.session.get(self.base_url, params=params, timeout=20)
        except requests.exceptions.ConnectionError:
            logging.error(f"[{self.name}] Connection error.")
            return None
        except requests.exceptions.Timeout:
            logging.error(f"[{self.name}] Timeout.")
            return None
        except Exception as e:
            logging.error(f"[{self.name}] Error: {e}")
            return None

        if resp.status_code in (502, 503, 504):
            logging.warning(f"[{self.name}] Server unavailable ({resp.status_code}).")
            return None

        if resp.status_code != 200:
            logging.error(f"[{self.name}] HTTP {resp.status_code}")
            return None

        try:
            data = resp.json()
        except Exception:
            logging.error(f"[{self.name}] JSON parse error")
            return None

        if isinstance(data, dict):
            # pscall API: {"result": "success", "total": N, "data": [...]}
            if self.api_type == "pscall":
                result_status = str(data.get('result', '')).lower()
                if result_status != 'success':
                    logging.warning(f"[{self.name}] pscall API error: {data}")
                    return {"aaData": []}
                if 'data' in data and isinstance(data['data'], list):
                    return {"aaData": data['data']}
                return {"aaData": []}

            status = str(data.get('status', '')).lower()
            msg = str(data.get('msg', data.get('description', ''))).lower()
            if 'no record' in msg or 'no data' in status or status == 'error':
                return {"aaData": []}
            if 'aaData' in data:
                return data
            if 'data' in data and isinstance(data['data'], list):
                return {"aaData": data['data']}
            if 'records' in data and isinstance(data['records'], list):
                return {"aaData": data['records']}
            logging.warning(f"[{self.name}] Unknown JSON format — keys: {list(data.keys())}")
            return None
        elif isinstance(data, list):
            return {"aaData": data}
        else:
            return None


# =====================================================
already_sent: set = load_already_sent()
_last_save_time: float = time.time()
# asyncio.Queue() cannot be created at module level (no event loop yet in Python 3.10+).
# Initialized inside main() below.
message_queue: asyncio.Queue | None = None


def build_otp_message(portal_name, date, number, service, message, otp):
    masked = mask_number(number)
    flag, country_name = get_country_info(number)
    text = (
        "✨ <b>PREMIUM OTP RECEIVED</b> ✨\n"
        "💎\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📡 <b>PORTAL:</b> {escape_html(portal_name)}\n"
        f"📱 <b>NUMBER:</b> <code>{escape_html(masked)}</code>\n"
        f"🌍 <b>COUNTRY:</b> {flag} {escape_html(country_name)}\n"
        f"📡 <b>SERVICE:</b> {escape_html(service)}\n\n"
        f"🔑 <b>OTP CODE:</b> <code>{escape_html(otp)}</code>\n\n"
        f"📝 <b>MESSAGE:</b>\n"
        f"❝ {escape_html(message)} ❞\n\n"
        f"🕐 <b>TIME:</b> {escape_html(date)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text=f"🔑 Copy OTP: {otp}",
            copy_text=CopyTextButton(text=otp)
        )]
    ])
    return text, keyboard


async def periodic_save():
    while True:
        await asyncio.sleep(SAVE_INTERVAL)
        save_already_sent(already_sent)
        logging.info(f"💾 Saved ({len(already_sent)} entries)")


def build_user_otp_message(portal_name, date, number, service, message, otp):
    """varson3-style message — সরাসরি user-এর কাছে যাবে"""
    masked = mask_number(number)
    flag, country_name = get_country_info(number)
    text = (
        f"🟢 <b>OTP প্রাপ্ত</b> 🟢\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>{flag} {escape_html(country_name)}</b>\n"
        f"📡 সার্ভিস: <b>{escape_html(str(service or portal_name))}</b>\n"
        f"📱 নম্বর: <code>{escape_html(masked)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔽 <b>OTP কপি করুন</b> 🔽"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            text=f"📋 {otp}",
            copy_text=CopyTextButton(text=str(otp))
        )]
    ])
    return text, keyboard


async def _send_to_user(user_id: int, portal_name: str,
                        date, number, service, message, otp: str):
    """varson3 bot token দিয়ে সঠিক user-এ OTP পাঠায়"""
    from telegram import Bot as _Bot
    text, keyboard = build_user_otp_message(
        portal_name, date, number, service, message, otp
    )
    try:
        user_bot = _Bot(token=VARSON3_BOT_TOKEN)
        await user_bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        logging.info(f"[{portal_name}] ✅ OTP → user {user_id}: {otp}")
    except Exception as e:
        logging.error(f"[{portal_name}] ❌ User {user_id} send failed: {e}")


async def telegram_sender():
    global message_queue
    logging.info(f"📨 Telegram sender চালু ({len(BOT_TOKENS)}টি bot, {len(CHAT_IDS)}টি chat).")
    while True:
        try:
            item = await message_queue.get()
            portal_name, msg_date, number, service, message, otp = item
            text, keyboard = build_otp_message(portal_name, msg_date, number, service, message, otp)

            # ── ১. Group/Channel-এ পাঠাও ──────────────────────────
            for chat_id in CHAT_IDS:
                sent = False
                for attempt in range(3):
                    try:
                        await bot_manager.send_message(
                            chat_id=chat_id,
                            text=text,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                            reply_markup=keyboard,
                        )
                        logging.info(f"[{portal_name}] ✅ OTP sent: {otp} | {number} → chat {chat_id}")
                        sent = True
                        break
                    except Exception as e:
                        logging.error(f"[{portal_name}] Send attempt {attempt+1}/3 to {chat_id} failed: {e}")
                        await asyncio.sleep(3)

                if not sent:
                    logging.error(f"[{portal_name}] ❌ Failed to send to {chat_id}: {otp}")

                await asyncio.sleep(0.3)

            # ── ২. Correct user-এ সরাসরি পাঠাও ──────────────────────
            loop = asyncio.get_running_loop()
            user_id, _ = await loop.run_in_executor(
                None, find_user_for_number, number
            )
            if user_id:
                await _send_to_user(
                    user_id, portal_name, msg_date, number, service, message, otp
                )
            else:
                logging.info(f"[{portal_name}] ℹ️ No active user for {number} — group only")

            message_queue.task_done()

        except asyncio.CancelledError:
            return
        except Exception as e:
            logging.error(f"Sender error: {e}")
            await asyncio.sleep(2)


async def check_portal(portal):
    global message_queue
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, portal.fetch_data)

    if data is None:
        return

    rows = data.get('aaData', [])
    new_count = 0

    for row in rows:
        try:
            if isinstance(row, dict):
                msg_date = str(row.get(portal.col_date, '')).strip()
                number   = str(row.get(portal.col_number, '')).strip()
                service  = str(row.get(portal.col_service, '')).strip()
                message  = str(row.get(portal.col_message, '')).strip()
            else:
                msg_date = str(row[portal.col_date]).strip()
                number   = str(row[portal.col_number]).strip()
                service  = str(row[portal.col_service]).strip()
                message  = str(row[portal.col_message]).strip()

            if not number or not message:
                continue

            otp = extract_otp(message)
            if not otp:
                continue

            unique_key = f"{number}|{otp}"
            if unique_key in already_sent:
                continue

            already_sent.add(unique_key)
            await message_queue.put((portal.name, msg_date, number, service, message, otp))
            new_count += 1

        except (IndexError, KeyError, TypeError):
            continue

    if new_count:
        logging.info(f"[{portal.name}] 🆕 {new_count} নতুন OTP পাওয়া গেছে।")


# =====================================================
# === CRASH-RESISTANT PORTAL RUNNER ===
# =====================================================
async def run_portal(portal):
    LOGIN_RETRY_DELAYS = [5, 10, 30, 60, 120, 300]
    SERVER_DOWN_WAIT   = 30
    login_fail_count   = 0
    loop = asyncio.get_running_loop()

    while True:
        try:
            # ===== একবার LOGIN =====
            logged_in = await loop.run_in_executor(None, portal.login)
            if not logged_in:
                wait = LOGIN_RETRY_DELAYS[min(login_fail_count, len(LOGIN_RETRY_DELAYS) - 1)]
                login_fail_count += 1
                logging.warning(f"[{portal.name}] Login failed (#{login_fail_count}) — retry in {wait}s...")
                await asyncio.sleep(wait)
                continue

            login_fail_count = 0
            logging.info(f"[{portal.name}] 🚀 Polling every {POLL_INTERVAL}s...")

            # ===== ৮ সেকেন্ড পর পর POLLING =====
            poll_count = 0
            while True:
                try:
                    await check_portal(portal)
                    poll_count += 1

                    # প্রতি ~৩০ মিনিটে proactive re-login
                    if poll_count >= RELOGIN_EVERY:
                        logging.info(f"[{portal.name}] 🔁 Proactive re-login ({poll_count} polls)...")
                        break

                    await asyncio.sleep(POLL_INTERVAL)

                except asyncio.CancelledError:
                    raise
                except SessionExpiredError as e:
                    logging.warning(f"[{portal.name}] 🔑 Session expired: {e} — re-login...")
                    break
                except ServerDownError:
                    logging.warning(f"[{portal.name}] 🔴 Server down — {SERVER_DOWN_WAIT}s অপেক্ষা...")
                    await asyncio.sleep(SERVER_DOWN_WAIT)
                except Exception as e:
                    logging.error(f"[{portal.name}] Check error: {e}")
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logging.info(f"[{portal.name}] Stopped.")
            return
        except Exception as e:
            wait = LOGIN_RETRY_DELAYS[min(login_fail_count, len(LOGIN_RETRY_DELAYS) - 1)]
            login_fail_count += 1
            logging.error(f"[{portal.name}] Crashed: {e} — restart in {wait}s...")
            await asyncio.sleep(wait)


async def main():
    global message_queue
    # Queue এখানে create করা হচ্ছে -- event loop চালু আছে এই পয়েন্টে
    message_queue = asyncio.Queue()

    login_portals = [Portal(p) for p in PORTALS]
    api_portals   = [ApiPortal(p) for p in API_PORTALS]
    all_portals   = login_portals + api_portals

    logging.info("=" * 50)
    logging.info(f"  🤖 ALL PANEL OTP BOT STARTING")
    logging.info(f"  📡 {len(login_portals)} Login Panel + {len(api_portals)} API Panel")
    logging.info(f"  🤖 {len(BOT_TOKENS)} Telegram Bot")
    logging.info(f"  💬 {len(CHAT_IDS)} Chat ID")
    logging.info(f"  ⏱️  Polling interval: {POLL_INTERVAL} seconds")
    logging.info("=" * 50)

    tasks = [
        asyncio.create_task(telegram_sender(), name="telegram_sender"),
        asyncio.create_task(periodic_save(), name="periodic_save"),
        *[asyncio.create_task(run_portal(p), name=p.name) for p in all_portals],
    ]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        save_already_sent(already_sent)
        logging.info("✅ Final save done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Bot stopped.")
