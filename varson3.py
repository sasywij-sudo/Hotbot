# ===================== PANEL OTP BOT (FULLY FIXED - 100% BUTTONS WORKING) =====================
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
import os, re, time, json, logging, threading, requests, random, shutil, html
from datetime import datetime

# ===================== কনফিগারেশন =====================
TOKEN = "8455313450:AAFZ0DN6jrJoNZLS1F578m9njXSQUn4qbTE"
ADMIN_IDS = [2062838711]

os.makedirs("data", exist_ok=True)
os.makedirs("numbers", exist_ok=True)

# ===================== JSON হ্যান্ডলার =====================
def load_json(fname, default):
    path = f"data/{fname}"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(fname, data):
    path = f"data/{fname}"
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        logging.error(f"Save error: {e}")

# ===================== লাস্ট অ্যাকটিভ ট্র্যাকার =====================
def get_last_active_service():
    return load_json("last_active_service.json", None)

def set_last_active_service(service):
    save_json("last_active_service.json", service)

def get_last_active_country(service):
    data = load_json("last_active_country.json", {})
    return data.get(service)

def set_last_active_country(service, country):
    data = load_json("last_active_country.json", {})
    data[service] = country
    save_json("last_active_country.json", data)

# ===================== ডেটা লোড =====================
user_balance = load_json("balances.json", {})
user_numbers_count = load_json("user_numbers_count.json", {})
user_numbers_log = load_json("user_numbers_log.json", {})
all_users_list = load_json("all_users.json", [])
otp_rewards = load_json("otp_rewards.json", {"default": 0.05})
otp_reward_log = load_json("otp_reward_log.json", {})
panels_config = load_json("panels.json", [])
withdraw_requests = load_json("withdraw_requests.json", {})
settings = load_json("settings.json", {"number_count": 5, "bot_username": ""})
force_channels = load_json("force_channels.json", [])
banned_users = load_json("banned_users.json", [])
tickets = load_json("tickets.json", [])
PAYMENT_GROUP_ID = int(settings.get("payment_group_id", 0) or 0)

all_users = set(all_users_list)
user_country = {}
user_platform = {}
user_used_numbers = {}
number_to_user = {}
number_to_meta = {}
admin_state = {}
user_last_message = {}

bot = telebot.TeleBot(TOKEN, threaded=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')

# ===================== PAYMENT GROUP =====================
def notify_payment_group(text):
    if not PAYMENT_GROUP_ID:
        logging.warning("Payment group is not configured")
        return False
    try:
        bot.send_message(PAYMENT_GROUP_ID, text, parse_mode="HTML")
        return True
    except Exception as e:
        logging.error(f"Payment group notification failed: {e}")
        return False

def normalize_phone(number: str) -> str:
    """Normalize common +/00/space/dash phone formats for exact matching."""
    digits = re.sub(r"\D", "", str(number or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    # Bangladesh local -> international form.
    if digits.startswith("01") and len(digits) == 11:
        digits = "880" + digits[1:]
    return digits

# Restore active number assignments after restart (15-minute expiry).
_saved_active = load_json("active_numbers.json", {})
_now = int(time.time())
for _n, _meta in list(_saved_active.items()):
    try:
        if _now - int(_meta.get("assigned_at", 0)) <= 15 * 60:
            _key = normalize_phone(_n)
            if _key and int(_meta.get("user_id")):
                number_to_meta[_key] = _meta
                number_to_user[_key] = int(_meta["user_id"])
    except Exception:
        pass

def save_active_number_map():
    payload = {}
    now = int(time.time())
    for n, meta in number_to_meta.items():
        if now - int(meta.get("assigned_at", now)) <= 15 * 60:
            payload[n] = meta
    save_json("active_numbers.json", payload)

def cleanup_active_number_map():
    now = int(time.time())
    changed = False
    for n, meta in list(number_to_meta.items()):
        if now - int(meta.get("assigned_at", now)) > 15 * 60:
            number_to_meta.pop(n, None)
            number_to_user.pop(n, None)
            changed = True
    if changed:
        save_active_number_map()

def register_active_number(number, user, service, country):
    key = normalize_phone(number)
    if not key:
        return
    meta = {"user_id": int(user), "service": str(service or ""), "country": str(country or ""), "assigned_at": int(time.time())}
    number_to_meta[key] = meta
    number_to_user[key] = int(user)
    save_active_number_map()

# ===================== COUNTRY FLAGS & MAP =====================
COUNTRY_FLAGS = {
    "Bangladesh": "🇧🇩", "India": "🇮🇳", "Pakistan": "🇵🇰", "USA": "🇺🇸",
    "UK": "🇬🇧", "UAE": "🇦🇪", "Saudi Arabia": "🇸🇦", "Kuwait": "🇰🇼",
    "Oman": "🇴🇲", "Qatar": "🇶🇦", "Bahrain": "🇧🇭", "Egypt": "🇪🇬",
    "Turkey": "🇹🇷", "Russia": "🇷🇺", "China": "🇨🇳", "Japan": "🇯🇵",
    "South Korea": "🇰🇷", "Malaysia": "🇲🇾", "Singapore": "🇸🇬",
    "Philippines": "🇵🇭", "Indonesia": "🇮🇩", "Australia": "🇦🇺",
    "Canada": "🇨🇦", "Germany": "🇩🇪", "France": "🇫🇷", "Italy": "🇮🇹",
    "Spain": "🇪🇸", "Netherlands": "🇳🇱", "Belgium": "🇧🇪",
    "Cambodia": "🇰🇭", "Nepal": "🇳🇵", "Bhutan": "🇧🇹", "Mongolia": "🇲🇳",
}
COUNTRY_MAP = {
    '880': '🇧🇩 Bangladesh', '971': '🇦🇪 UAE', '966': '🇸🇦 Saudi Arabia',
    '977': '🇳🇵 Nepal', '975': '🇧🇹 Bhutan', '976': '🇲🇳 Mongolia',
    '974': '🇶🇦 Qatar', '973': '🇧🇭 Bahrain', '972': '🇮🇱 Israel',
    '968': '🇴🇲 Oman', '967': '🇾🇪 Yemen', '965': '🇰🇼 Kuwait',
    '964': '🇮🇶 Iraq', '963': '🇸🇾 Syria', '962': '🇯🇴 Jordan',
    '961': '🇱🇧 Lebanon', '960': '🇲🇻 Maldives', '91': '🇮🇳 India',
    '92': '🇵🇰 Pakistan', '93': '🇦🇫 Afghanistan', '94': '🇱🇰 Sri Lanka',
    '95': '🇲🇲 Myanmar', '98': '🇮🇷 Iran', '1': '🇺🇸 USA / Canada',
    '44': '🇬🇧 UK', '49': '🇩🇪 Germany', '33': '🇫🇷 France',
    '39': '🇮🇹 Italy', '34': '🇪🇸 Spain', '31': '🇳🇱 Netherlands',
    '32': '🇧🇪 Belgium', '41': '🇨🇭 Switzerland', '43': '🇦🇹 Austria',
    '46': '🇸🇪 Sweden', '47': '🇳🇴 Norway', '45': '🇩🇰 Denmark',
    '48': '🇵🇱 Poland', '40': '🇷🇴 Romania', '36': '🇭🇺 Hungary',
    '30': '🇬🇷 Greece', '27': '🇿🇦 South Africa', '20': '🇪🇬 Egypt',
    '90': '🇹🇷 Turkey', '7': '🇷🇺 Russia', '86': '🇨🇳 China',
    '81': '🇯🇵 Japan', '82': '🇰🇷 South Korea', '60': '🇲🇾 Malaysia',
    '65': '🇸🇬 Singapore', '63': '🇵🇭 Philippines', '62': '🇮🇩 Indonesia',
    '61': '🇦🇺 Australia', '66': '🇹🇭 Thailand', '64': '🇳🇿 New Zealand',
    '52': '🇲🇽 Mexico', '55': '🇧🇷 Brazil', '54': '🇦🇷 Argentina',
    '56': '🇨🇱 Chile', '57': '🇨🇴 Colombia', '51': '🇵🇪 Peru',
    '855': '🇰🇭 Cambodia',
}

COUNTRY_ALIASES = {
    "bd": "Bangladesh", "bangladesh": "Bangladesh",
    "in": "India", "india": "India",
    "pk": "Pakistan", "pakistan": "Pakistan",
    "us": "USA", "usa": "USA", "america": "USA",
    "uk": "UK", "united kingdom": "UK", "england": "UK",
    "ae": "UAE", "uae": "UAE", "dubai": "UAE",
    "sa": "Saudi Arabia", "saudi": "Saudi Arabia", "saudi arabia": "Saudi Arabia",
    "de": "Germany", "germany": "Germany",
    "fr": "France", "france": "France",
    "it": "Italy", "italy": "Italy",
    "es": "Spain", "spain": "Spain",
    "nl": "Netherlands", "netherlands": "Netherlands",
    "be": "Belgium", "belgium": "Belgium",
    "tr": "Turkey", "turkey": "Turkey",
    "ru": "Russia", "russia": "Russia",
    "cn": "China", "china": "China",
    "jp": "Japan", "japan": "Japan",
    "kr": "South Korea", "korea": "South Korea", "south korea": "South Korea",
    "my": "Malaysia", "malaysia": "Malaysia",
    "sg": "Singapore", "singapore": "Singapore",
    "ph": "Philippines", "philippines": "Philippines",
    "id": "Indonesia", "indonesia": "Indonesia",
    "au": "Australia", "australia": "Australia",
    "ca": "Canada", "canada": "Canada",
    "kh": "Cambodia", "cambodia": "Cambodia",
    "np": "Nepal", "nepal": "Nepal",
    "bh": "Bhutan", "bhutan": "Bhutan",
    "mn": "Mongolia", "mongolia": "Mongolia",
}

def format_price(value):
    try:
        v = float(value)
        return f"{v:.10f}".rstrip("0").rstrip(".")
    except Exception:
        return str(value)

def normalize_country_name(value):
    value = str(value or "").strip()
    if not value:
        return "Unknown"
    key = re.sub(r"\s+", " ", value).strip().lower()
    return COUNTRY_ALIASES.get(key, value)


def normalize_phone_for_routing(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("01") and len(digits) == 11:
        digits = "88" + digits
    return digits

CALLING_CODE_COUNTRIES = {'1': 'USA/Canada', '7': 'Russia/Kazakhstan', '20': 'Egypt', '27': 'South Africa', '30': 'Greece', '31': 'Netherlands', '32': 'Belgium', '33': 'France', '34': 'Spain', '36': 'Hungary', '39': 'Italy', '40': 'Romania', '41': 'Switzerland', '43': 'Austria', '44': 'United Kingdom', '45': 'Denmark', '46': 'Sweden', '47': 'Norway', '48': 'Poland', '49': 'Germany', '51': 'Peru', '52': 'Mexico', '53': 'Cuba', '54': 'Argentina', '55': 'Brazil', '56': 'Chile', '57': 'Colombia', '58': 'Venezuela', '60': 'Malaysia', '61': 'Australia', '62': 'Indonesia', '63': 'Philippines', '64': 'New Zealand', '65': 'Singapore', '66': 'Thailand', '81': 'Japan', '82': 'South Korea', '84': 'Vietnam', '86': 'China', '90': 'Turkey', '91': 'India', '92': 'Pakistan', '93': 'Afghanistan', '94': 'Sri Lanka', '95': 'Myanmar', '98': 'Iran', '211': 'South Sudan', '212': 'Morocco', '213': 'Algeria', '216': 'Tunisia', '218': 'Libya', '220': 'Gambia', '221': 'Senegal', '222': 'Mauritania', '223': 'Mali', '224': 'Guinea', '225': 'Ivory Coast', '226': 'Burkina Faso', '227': 'Niger', '228': 'Togo', '229': 'Benin', '230': 'Mauritius', '231': 'Liberia', '232': 'Sierra Leone', '233': 'Ghana', '234': 'Nigeria', '235': 'Chad', '236': 'Central African Republic', '237': 'Cameroon', '238': 'Cape Verde', '239': 'Sao Tome and Principe', '240': 'Equatorial Guinea', '241': 'Gabon', '242': 'Republic of the Congo', '243': 'DR Congo', '244': 'Angola', '245': 'Guinea-Bissau', '248': 'Seychelles', '249': 'Sudan', '250': 'Rwanda', '251': 'Ethiopia', '252': 'Somalia', '253': 'Djibouti', '254': 'Kenya', '255': 'Tanzania', '256': 'Uganda', '257': 'Burundi', '258': 'Mozambique', '260': 'Zambia', '261': 'Madagascar', '263': 'Zimbabwe', '264': 'Namibia', '265': 'Malawi', '266': 'Lesotho', '267': 'Botswana', '268': 'Eswatini', '269': 'Comoros', '290': 'Saint Helena', '291': 'Eritrea', '297': 'Aruba', '298': 'Faroe Islands', '299': 'Greenland', '350': 'Gibraltar', '351': 'Portugal', '352': 'Luxembourg', '353': 'Ireland', '354': 'Iceland', '355': 'Albania', '356': 'Malta', '357': 'Cyprus', '358': 'Finland', '359': 'Bulgaria', '370': 'Lithuania', '371': 'Latvia', '372': 'Estonia', '373': 'Moldova', '374': 'Armenia', '375': 'Belarus', '376': 'Andorra', '377': 'Monaco', '378': 'San Marino', '380': 'Ukraine', '381': 'Serbia', '382': 'Montenegro', '385': 'Croatia', '386': 'Slovenia', '387': 'Bosnia and Herzegovina', '389': 'North Macedonia', '420': 'Czech Republic', '421': 'Slovakia', '423': 'Liechtenstein', '500': 'Falkland Islands', '501': 'Belize', '502': 'Guatemala', '503': 'El Salvador', '504': 'Honduras', '505': 'Nicaragua', '506': 'Costa Rica', '507': 'Panama', '509': 'Haiti', '591': 'Bolivia', '592': 'Guyana', '593': 'Ecuador', '594': 'French Guiana', '595': 'Paraguay', '596': 'Martinique', '597': 'Suriname', '598': 'Uruguay', '670': 'Timor-Leste', '673': 'Brunei', '674': 'Nauru', '675': 'Papua New Guinea', '676': 'Tonga', '677': 'Solomon Islands', '678': 'Vanuatu', '679': 'Fiji', '680': 'Palau', '681': 'Wallis and Futuna', '682': 'Cook Islands', '683': 'Niue', '685': 'Samoa', '686': 'Kiribati', '687': 'New Caledonia', '688': 'Tuvalu', '689': 'French Polynesia', '690': 'Tokelau', '691': 'Micronesia', '692': 'Marshall Islands', '850': 'North Korea', '852': 'Hong Kong', '853': 'Macau', '855': 'Cambodia', '856': 'Laos', '880': 'Bangladesh', '886': 'Taiwan', '960': 'Maldives', '961': 'Lebanon', '962': 'Jordan', '963': 'Syria', '964': 'Iraq', '965': 'Kuwait', '966': 'Saudi Arabia', '967': 'Yemen', '968': 'Oman', '970': 'Palestine', '971': 'United Arab Emirates', '972': 'Israel', '973': 'Bahrain', '974': 'Qatar', '975': 'Bhutan', '976': 'Mongolia', '977': 'Nepal', '992': 'Tajikistan', '993': 'Turkmenistan', '994': 'Azerbaijan', '995': 'Georgia', '996': 'Kyrgyzstan', '998': 'Uzbekistan'}

def detect_country_from_number(number):
    digits = normalize_phone_for_routing(number)
    if not digits:
        return "Unknown"
    for code in sorted(CALLING_CODE_COUNTRIES, key=len, reverse=True):
        if digits.startswith(code):
            return CALLING_CODE_COUNTRIES[code]
    return "Unknown"


def clean_uploaded_numbers(raw_lines):
    out, seen = [], set()
    for raw in raw_lines:
        s = str(raw).strip()
        if not s:
            continue
        candidates = re.findall(
            r"(?<!\d)(?:\+|00)?\d(?:[\d\s().-]{5,}\d)(?!\d)", s
        )
        if not candidates:
            candidates = re.findall(r"(?<!\d)\d{7,15}(?!\d)", s)
        for candidate in candidates:
            number = normalize_phone_for_routing(candidate)
            if 7 <= len(number) <= 15 and number not in seen:
                seen.add(number)
                out.append(number)
    return out

def mask_number(number: str) -> str:
    digits = re.sub(r'\D', '', number)
    if len(digits) <= 7:
        return number
    return digits[:3] + '•••••' + digits[-4:]

def get_country_info(number: str):
    raw = str(number).strip()
    if raw.startswith('+'):
        raw = raw[1:]
    elif raw.startswith('00'):
        raw = raw[2:]
    digits = re.sub(r'\D', '', raw)
    if len(digits) > 10 and digits.startswith('0'):
        digits = digits[1:]
    for code in sorted(COUNTRY_MAP.keys(), key=lambda x: -len(x)):
        if digits.startswith(code):
            val = COUNTRY_MAP[code]
            parts = val.split(' ', 1)
            flag = parts[0]
            name = parts[1] if len(parts) > 1 else val
            return flag, name
    return '🌍', 'Unknown'

def extract_otp(message: str) -> str | None:
    text = str(message or "").strip()
    # Prefer explicit authentication-code wording.
    patterns = [
        r'(?:otp|one[- ]?time password|verification|verify|security|auth(?:entication)?|login|confirmation)\D{0,20}(\d{3,4}[\s\-–]\d{3,4})\b',
        r'(?:otp|one[- ]?time password|verification|verify|security|auth(?:entication)?|login|confirmation|code|pin|passcode|token)\D{0,20}(\d{4,8})\b',
        r'\b(?:code|otp|pin)\s*(?:is|:|-)\s*(\d{4,8})\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return re.sub(r'\D', '', m.group(1))

    # Some panels send short messages such as "Code: 123456".
    nums = re.findall(r'(?<!\d)(\d{4,8})(?!\d)', text)
    if len(nums) == 1 and len(text) <= 80:
        # Do not treat long phone/date/account numbers as OTPs.
        if not re.search(r'(?:\+?\d[\d\s().-]{8,}\d)', text):
            return nums[0]
    return None

def get_reward_amount(country):
    off_key = f"{country}_off"
    if otp_rewards.get(off_key, False):
        return 0.0
    return float(otp_rewards.get(country, otp_rewards.get("default", 0.05)))

# ===================== ফোর্স চ্যানেল =====================
def get_force_channels():
    return load_json("force_channels.json", [])

def save_force_channels(channels):
    save_json("force_channels.json", channels)

def check_force_join(uid):
    channels = get_force_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = bot.get_chat_member(ch["id"], uid)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def force_join_keyboard():
    kb = types.InlineKeyboardMarkup()
    for ch in get_force_channels():
        kb.add(types.InlineKeyboardButton(f"📢 {ch['name']}", url=ch["link"], style="primary"))
    kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="force_verify", style="success"))
    return kb

def get_banned_users():
    return load_json("banned_users.json", [])

def save_banned_users(banned_list):
    save_json("banned_users.json", banned_list)

def is_user_banned(uid):
    return str(uid) in get_banned_users()

def get_tickets():
    return load_json("tickets.json", [])

def save_tickets(tickets_data):
    save_json("tickets.json", tickets_data)

# ===================== রিফ্রেশ ফাংশন =====================
def refresh(chat_id, uid, text, reply_markup=None, parse_mode="HTML"):
    last_msg_id = user_last_message.get(uid)
    try:
        if last_msg_id:
            bot.edit_message_text(text, chat_id, last_msg_id, parse_mode=parse_mode, reply_markup=reply_markup)
        else:
            msg = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            user_last_message[uid] = msg.message_id
    except ApiTelegramException as e:
        if "message is not modified" in str(e).lower():
            return
        try:
            msg = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            user_last_message[uid] = msg.message_id
        except:
            pass
    except Exception:
        try:
            msg = bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            user_last_message[uid] = msg.message_id
        except:
            pass

# ===================== রঙিন রিপ্লাই কিবোর্ড =====================
def main_reply_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("📱 Get Number", style="primary"),
        types.KeyboardButton("📊 Traffic", style="primary"),
        types.KeyboardButton("💳 Wallet", style="primary"),
        types.KeyboardButton("📈 Statistics", style="primary"),
        types.KeyboardButton("🏆 Top Users", style="primary"),
        types.KeyboardButton("🔗 Refer & Earn", style="success"),
        types.KeyboardButton("🛡 Support", style="primary"),
        types.KeyboardButton("💰 Withdraw", style="danger")
    )
    return kb

def send_welcome(chat_id, uid):
    uid_str = str(uid)
    balance = float(user_balance.get(uid_str, 0.0))
    text = (
        f"👋 <b>Welcome to Premium Bazar OTP Bot!</b>\n\n"
        f"🪪 Your ID: <code>{uid}</code>\n"
        f"💰 Balance: ${balance:.2f}\n\n"
        "Select an option from below:"
    )
    kb = main_reply_keyboard()
    refresh(chat_id, uid, text, kb)

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    uid_str = str(uid)

    if is_user_banned(uid):
        bot.send_message(msg.chat.id, "🚫 You are banned.")
        return

    if not check_force_join(uid):
        bot.send_message(msg.chat.id, "🚫 Please join required channel(s) first.", reply_markup=force_join_keyboard())
        return

    all_users.add(uid)
    save_json("all_users.json", list(all_users))
    user_last_active = load_json("user_last_active.json", {})
    user_last_active[uid_str] = int(time.time())
    save_json("user_last_active.json", user_last_active)

    if msg.text and "ref_" in msg.text:
        try:
            ref_id = int(msg.text.split("ref_")[1])
            if ref_id != uid and str(uid) not in load_json("referred_by.json", {}):
                ref_data = load_json("referred_by.json", {})
                ref_data[str(uid)] = ref_id
                save_json("referred_by.json", ref_data)
                ref_bal = float(user_balance.get(str(ref_id), 0.0)) + 0.10
                user_balance[str(ref_id)] = round(ref_bal, 2)
                save_json("balances.json", user_balance)
                try:
                    bot.send_message(ref_id, "🎉 New referral! +$0.10 added.")
                except:
                    pass
        except:
            pass

    send_welcome(msg.chat.id, uid)

# ===================== রিপ্লাই কিবোর্ড হ্যান্ডলার =====================
@bot.message_handler(commands=["scripts"])
def cmd_scripts(msg):
    """Admin only: running script status দেখো"""
    if msg.from_user.id not in ADMIN_IDS:
        return
    statuses = script_manager.status()
    if not statuses:
        bot.send_message(msg.chat.id, "📂 কোনো OTP script পাওয়া যায়নি।")
        return
    lines = ["📂 <b>OTP Scripts Status</b>\n"]
    for s in statuses:
        icon = "🟢" if s["running"] else "🔴"
        lines.append(f"{icon} <code>{html.escape(s['name'])}</code>  (pid: {s['pid']})")
    bot.send_message(msg.chat.id, "\n".join(lines), parse_mode="HTML")


@bot.message_handler(func=lambda m: m.text in ["📱 Get Number", "📊 Traffic", "💳 Wallet", "📈 Statistics", "🏆 Top Users", "🔗 Refer & Earn", "🛡 Support", "💰 Withdraw"])
def handle_menu_buttons(msg):
    uid = msg.from_user.id
    uid_str = str(uid)

    try:
        bot.delete_message(msg.chat.id, msg.message_id)
    except:
        pass

    if is_user_banned(uid):
        bot.send_message(msg.chat.id, "🚫 Banned")
        return
    if not check_force_join(uid):
        bot.send_message(msg.chat.id, "🚫 Please join required channel(s) first.", reply_markup=force_join_keyboard())
        return

    user_last_active = load_json("user_last_active.json", {})
    user_last_active[uid_str] = int(time.time())
    save_json("user_last_active.json", user_last_active)

    if msg.text == "📱 Get Number":
        show_get_number(uid, msg.chat.id)
    elif msg.text == "📊 Traffic":
        show_traffic(uid, msg.chat.id)
    elif msg.text == "💳 Wallet":
        show_wallet(uid, msg.chat.id)
    elif msg.text == "📈 Statistics":
        show_statistics(uid, msg.chat.id)
    elif msg.text == "🏆 Top Users":
        show_top_users(uid, msg.chat.id)
    elif msg.text == "🔗 Refer & Earn":
        show_referral(uid, msg.chat.id)
    elif msg.text == "🛡 Support":
        show_support(uid, msg.chat.id)
    elif msg.text == "💰 Withdraw":
        show_withdraw(uid, msg.chat.id)

# ===================== ইউজার ফাংশন =====================
def show_get_number(uid, chat_id):
    text = "📱 <b>Select a service:</b>"
    kb = types.InlineKeyboardMarkup()
    if os.path.exists("numbers"):
        services = sorted([s for s in os.listdir("numbers") if os.path.isdir(f"numbers/{s}")])
        last_service = get_last_active_service()
        if last_service in services:
            services.remove(last_service)
            services.insert(0, last_service)
        for s in services:
            style = "success" if s == last_service else "primary"
            kb.add(types.InlineKeyboardButton(f"📦 {s}", callback_data=f"srv|{s}", style=style))
    if not kb.keyboard:
        kb.add(types.InlineKeyboardButton("😔 No service", callback_data="noop", style="secondary"))
    refresh(chat_id, uid, text, kb)

def show_traffic(uid, chat_id):
    now = int(time.time())
    day = 86400
    week = 7*day
    user_last_active = load_json("user_last_active.json", {})
    user_join_time = load_json("user_join_time.json", {})
    active_today = sum(1 for u in all_users if now - user_last_active.get(str(u), 0) <= day)
    active_week = sum(1 for u in all_users if now - user_last_active.get(str(u), 0) <= week)
    new_today = sum(1 for t in user_join_time.values() if now - t <= day)
    new_week = sum(1 for t in user_join_time.values() if now - t <= week)
    total_nums = sum(user_numbers_count.values())
    total_refs = sum(len(v) for v in load_json("referrals.json", {}).values())
    pending_w = sum(1 for r in load_json("withdraw_requests.json", {}).values() if r.get("status") == "pending")
    total_bal = sum(float(v) for v in user_balance.values())
    text = (
        f"📊 <b>Traffic</b>\n\n"
        f"👥 Total Users: {len(all_users)}\n"
        f"🟢 Active Today: {active_today}\n"
        f"🟡 Active Week: {active_week}\n"
        f"🆕 New Today: {new_today}\n"
        f"📅 New Week: {new_week}\n\n"
        f"📱 Numbers Used: {total_nums}\n"
        f"🔗 Referrals: {total_refs}\n"
        f"💰 Total Balance: ${total_bal:.2f}\n"
        f"💸 Pending Withdraw: {pending_w}"
    )
    refresh(chat_id, uid, text)

def show_wallet(uid, chat_id):
    uid_str = str(uid)
    balance = float(user_balance.get(uid_str, 0.0))
    otp_info = otp_reward_log.get(uid_str, {"count": 0, "earned": 0.0})
    text = (
        f"💳 <b>Wallet</b>\n\n"
        f"💰 Balance: ${balance:.2f}\n"
        f"📩 OTP Received: {otp_info.get('count', 0)}\n"
        f"🎁 OTP Earned: ${float(otp_info.get('earned', 0.0)):.2f}\n"
    )
    refresh(chat_id, uid, text)

def show_statistics(uid, chat_id):
    uid_str = str(uid)
    balance = float(user_balance.get(uid_str, 0.0))
    otp_info = otp_reward_log.get(uid_str, {"count": 0, "earned": 0.0})
    nums_used = user_numbers_count.get(uid_str, 0)
    text = (
        f"📈 <b>Statistics</b>\n\n"
        f"💰 Balance: ${balance:.2f}\n"
        f"📩 OTP Received: {otp_info.get('count', 0)}\n"
        f"🎁 OTP Earned: ${float(otp_info.get('earned', 0.0)):.2f}\n"
        f"📱 Numbers Used: {nums_used}\n"
    )
    refresh(chat_id, uid, text)

def show_top_users(uid, chat_id):
    items = sorted([(u, float(b)) for u, b in user_balance.items() if float(b) > 0], key=lambda x: x[1], reverse=True)[:10]
    if not items:
        text = "🏆 No users with balance yet."
    else:
        lines = ["🏆 <b>Top 10 Users</b>\n"]
        for i, (u, b) in enumerate(items, 1):
            lines.append(f"{i}. <code>{u}</code> → ${b:.2f}")
        text = "\n".join(lines)
    refresh(chat_id, uid, text)

def show_referral(uid, chat_id):
    bot_username = settings.get("bot_username") or bot.get_me().username
    link = f"https://t.me/{bot_username}?start=ref_{uid}"
    text = (
        f"🔗 <b>Refer & Earn</b>\n\n"
        f"Share this link:\n<code>{link}</code>\n\n"
        f"Each referral earns you $0.10!"
    )
    refresh(chat_id, uid, text)

def show_support(uid, chat_id):
    text = "🛡 <b>Support</b>\n\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 Open Ticket", callback_data="ticket_open", style="success"))
    kb.add(types.InlineKeyboardButton("📋 My Tickets", callback_data="ticket_my_list", style="primary"))
    refresh(chat_id, uid, text, kb)

def show_withdraw(uid, chat_id):
    uid_str = str(uid)
    balance = float(user_balance.get(uid_str, 0.0))
    existing = load_json("withdraw_requests.json", {})
    if any(int(r.get("user_id", -1)) == uid and r.get("status") in ("pending", "approved") for r in existing.values()):
        refresh(chat_id, uid, "⏳ You already have a pending/approved withdrawal. Please wait until it is paid or rejected.")
        admin_state.pop(uid, None)
        return
    if balance < 1.0:
        text = f"💰 <b>Withdraw</b>\n\n❌ Minimum $1.00 required.\nYour balance: ${balance:.2f}"
        refresh(chat_id, uid, text)
        return

    admin_state[uid] = {"step": "withdraw_method"}
    text = f"💰 <b>Withdraw</b>\n\n💵 Balance: <b>${balance:.2f}</b>\n\nSelect your withdrawal method:"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📱 bKash", callback_data="withdraw_method|bkash", style="primary"))
    kb.add(types.InlineKeyboardButton("🟠 Nagad", callback_data="withdraw_method|nagad", style="primary"))
    kb.add(types.InlineKeyboardButton("🟡 Binance", callback_data="withdraw_method|binance", style="primary"))
    refresh(chat_id, uid, text, kb)

# ===================== প্যানেল মনিটর =====================
MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Infinix X6882 Build/UP1A.231005.007) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.7632.159 Mobile Safari/537.36"
)

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
            return a + b if op == '+' else a - b
    return None

def extract_sesskey(html: str) -> str:
    patterns = [
        r'sesskey["\s]*[:=]["\s]*([A-Za-z0-9+/=]{8,})',
        r'[?&]sesskey=([A-Za-z0-9+/=%]{8,})',
        r'"sesskey"\s*:\s*"([A-Za-z0-9+/=]{8,})"',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return ""

class Portal:
    def __init__(self, config):
        self.name = config.get("name", "Unnamed")
        self.base_url = config["url"].rstrip('/')
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.login_page = self.base_url + "/ints/login"
        self.login_post = self.base_url + "/ints/signin"
        self.data_url = self.base_url + "/ints/agent/res/data_smscdr.php"
        self.dashboard_url = self.base_url + "/ints/agent/SMSDashboard"
        self.reports_url = self.base_url + "/ints/agent/SMSCDRReports"
        self.sesskey = ""
        self._logged_in = False
        self.session = self._new_session()
        self.col_date    = config.get("col_date", 0)
        self.col_number  = config.get("col_number", 2)
        self.col_service = config.get("col_service", 3)
        self.col_message = config.get("col_message", 5)
        self.enabled = config.get("enabled", True)
        self.type = "login"

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
            resp = self.session.get(self.login_page, timeout=20, allow_redirects=True)
            if resp.status_code in (502, 503, 504):
                return False
            captcha_answer = solve_captcha(resp.text) or ""
            crlf_token = ""
            m = re.search(r"name=['\"]crlf['\"]\s+value=['\"]([a-f0-9]{20,})['\"]", resp.text)
            if m:
                crlf_token = m.group(1)
            payload = {"username": self.username, "password": self.password, "capt": captcha_answer}
            if crlf_token:
                payload["crlf"] = crlf_token
            login_resp = self.session.post(
                self.login_post,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": self.login_page, "Origin": self.base_url},
                timeout=20,
                allow_redirects=True,
            )
            if login_resp.status_code in (502, 503, 504):
                return False
            final_url = login_resp.url.lower()
            text_lower = login_resp.text.lower()
            success_signals = ["dashboard" in final_url, "/agent/" in final_url, "smsdashboard" in final_url,
                               "logout" in text_lower, "sign out" in text_lower, "welcome" in text_lower]
            fail_signals = ["/ints/login" in final_url, "/ints/signin" in final_url,
                            "invalid username" in text_lower, "invalid password" in text_lower]
            if any(success_signals) and not any(fail_signals):
                self._logged_in = True
                self._capture_sesskey(login_resp.text)
                return True
            return False
        except Exception:
            return False

    def _capture_sesskey(self, login_html: str):
        key = extract_sesskey(login_html)
        if not key:
            try:
                dash = self.session.get(self.dashboard_url, timeout=15, allow_redirects=True)
                key = extract_sesskey(dash.text)
                if not key:
                    rep = self.session.get(self.reports_url, headers={"Referer": self.dashboard_url}, timeout=15, allow_redirects=True)
                    key = extract_sesskey(rep.text)
            except:
                pass
        if key:
            self.sesskey = key

    def fetch_data(self):
        if not self._logged_in:
            if not self.login():
                time.sleep(1)
                if not self.login():
                    return None
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
            resp = self.session.get(self.data_url, params=params,
                                    headers={"Accept": "application/json, text/javascript, */*; q=0.01",
                                             "X-Requested-With": "XMLHttpRequest",
                                             "Referer": self.reports_url},
                                    timeout=20, allow_redirects=True)
            if resp.status_code != 200:
                return None
            if "/ints/login" in resp.url.lower():
                self._logged_in = False
                return None
            return resp.json()
        except:
            return None

class ApiPortal:
    def __init__(self, config):
        self.name = config.get("name", "Unnamed")
        self.base_url = config["url"]
        self.token = config.get("token", "")
        self.api_type = config.get("type", "viewstats")
        self.records = config.get("records", 50)
        self.col_date = config.get("col_date", 0)
        self.col_number = config.get("col_number", 2)
        self.col_service = config.get("col_service", 3)
        self.col_message = config.get("col_message", 5)
        self.enabled = config.get("enabled", True)
        self.type = "api"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": MOBILE_UA,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "X-Requested-With": "XMLHttpRequest",
        })

    def login(self) -> bool:
        return True

    def fetch_data(self):
        today = datetime.now().strftime("%Y-%m-%d")
        date_start = f"{today} 00:00:00"
        date_end   = f"{today} 23:59:59"
        if self.api_type == "pscall":
            params = {"key": self.token, "start": 0, "length": self.records}
        elif self.api_type == "mdr":
            params = {"token": self.token, "fromdate": date_start, "todate": date_end,
                      "searchnumber": "", "searchcli": "", "records": self.records}
        else:
            params = {"token": self.token, "dt1": date_start, "dt2": date_end, "records": self.records}
        try:
            resp = self.session.get(self.base_url, params=params, timeout=20)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, dict):
                if self.api_type == "pscall" and str(data.get('result', '')).lower() != 'success':
                    return {"aaData": []}
                if 'aaData' in data:
                    return data
                if 'data' in data and isinstance(data['data'], list):
                    return {"aaData": data['data']}
                return None
            elif isinstance(data, list):
                return {"aaData": data}
        except:
            return None

class PanelManager:
    def __init__(self):
        self.panels = []
        self.already_sent = set()
        self.running = False
        self.thread = None
        self._load_panels()

    def _load_panels(self):
        configs = load_json("panels.json", [])
        self.panels = []
        for cfg in configs:
            if cfg.get("type") == "api":
                self.panels.append(ApiPortal(cfg))
            else:
                self.panels.append(Portal(cfg))
        logging.info(f"প্যানেল লোড: {len(self.panels)} টি")

    def save_panels(self):
        configs = []
        for p in self.panels:
            cfg = {
                "name": p.name,
                "url": p.base_url,
                "type": p.type,
                "enabled": p.enabled,
                "username": getattr(p, "username", ""),
                "password": getattr(p, "password", ""),
                "token": getattr(p, "token", ""),
                "records": getattr(p, "records", 50),
                "col_date": p.col_date,
                "col_number": p.col_number,
                "col_service": p.col_service,
                "col_message": p.col_message,
            }
            configs.append(cfg)
        save_json("panels.json", configs)

    def add_panel(self, config):
        if config.get("type") == "api":
            p = ApiPortal(config)
        else:
            p = Portal(config)
        self.panels.append(p)
        self.save_panels()
        return p

    def remove_panel(self, name):
        self.panels = [p for p in self.panels if p.name != name]
        self.save_panels()

    def toggle_panel(self, name):
        for p in self.panels:
            if p.name == name:
                p.enabled = not p.enabled
                self.save_panels()
                return p.enabled
        return None

    def list_panels(self):
        return [{"name": p.name, "type": p.type, "enabled": p.enabled} for p in self.panels]

    def handle_otp(self, portal_name, date, number, service, message, otp):
        cleanup_active_number_map()
        digits = normalize_phone(number)
        if not digits:
            return

        # Security/correctness: deliver only when the number has an active exact mapping.
        user_id = number_to_user.get(digits)
        meta = number_to_meta.get(digits, {})
        if not user_id:
            for admin in ADMIN_IDS:
                try:
                    bot.send_message(admin, f"⚠️ Unmatched OTP ignored\nPanel: {html.escape(str(portal_name))}\nNumber: <code>{html.escape(str(number))}</code>\nOTP: <code>{html.escape(str(otp))}</code>", parse_mode="HTML")
                except Exception:
                    pass
            return

        country = meta.get("country") or user_country.get(user_id, "Unknown")
        reward = get_reward_amount(country)
        uid_str = str(user_id)
        if reward > 0:
            new_bal = float(user_balance.get(uid_str, 0.0)) + reward
            user_balance[uid_str] = round(new_bal, 8)
            save_json("balances.json", user_balance)
            log = otp_reward_log.get(uid_str, {"count": 0, "earned": 0.0})
            log["count"] += 1
            log["earned"] = round(float(log.get("earned", 0.0)) + reward, 8)
            otp_reward_log[uid_str] = log
            save_json("otp_reward_log.json", otp_reward_log)

        flag, country_name = get_country_info(number)
        masked = mask_number(number)
        balance = float(user_balance.get(uid_str, 0.0))
        text = (
            f"🟢 <b>সক্রিয় OTP প্রাপ্ত</b> 🟢\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌍 <b>{flag} {country_name}</b>\n"
            f"📡 সার্ভিস: <b>{html.escape(str(service or portal_name))}</b>\n"
            f"📱 নম্বর: <code>{html.escape(masked)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
        )
        if reward > 0:
            text += f"🎁 রিওয়ার্ড: +${reward:.2f}  |  💰 ব্যালেন্স: ${balance:.2f}\n"
        else:
            text += f"💰 ব্যালেন্স: ${balance:.2f}\n"
        text += "🔽 <b>ওটিপি কপি করুন</b> 🔽"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text=f"📋 {otp}", copy_text=types.CopyTextButton(text=str(otp)), style="success"))
        try:
            bot.send_message(user_id, text, parse_mode="HTML", reply_markup=kb)
            logging.info(f"OTP delivered to mapped user {user_id} for {digits}")
            set_last_active_service(service or portal_name)
            set_last_active_country(service or portal_name, country)
        except Exception as e:
            logging.error(f"Send OTP failed: {e}")
            return

        admin_text = (
            f"📩 <b>OTP Delivered</b>\n"
            f"📡 Panel: <b>{html.escape(str(portal_name))}</b>\n"
            f"📱 Number: <code>{html.escape(masked)}</code>\n"
            f"🌍 {flag} {country_name}\n"
            f"🔑 OTP: <code>{html.escape(str(otp))}</code>\n"
            f"👤 User: <code>{user_id}</code>"
        )
        for admin in ADMIN_IDS:
            try:
                bot.send_message(admin, admin_text, parse_mode="HTML")
            except Exception:
                pass

    @staticmethod
    def _row_value(row, index):
        if isinstance(row, dict):
            for key in (index, str(index), f"{index}"):
                if key in row:
                    return row[key]
            return ""
        try:
            return row[index]
        except (IndexError, KeyError, TypeError):
            return ""

    def _monitor_loop(self):
        while self.running:
            cleanup_active_number_map()
            for panel in self.panels:
                if not panel.enabled:
                    continue
                try:
                    data = panel.fetch_data()
                    if data is None:
                        continue
                    rows = data.get('aaData', [])
                    for row in rows:
                        try:
                            msg_date = str(self._row_value(row, panel.col_date)).strip()
                            number   = str(self._row_value(row, panel.col_number)).strip()
                            service  = str(self._row_value(row, panel.col_service)).strip()
                            message  = str(self._row_value(row, panel.col_message)).strip()
                            if not number or not message:
                                continue
                            otp = extract_otp(message)
                            if not otp:
                                continue
                            key = f"{number}|{otp}"
                            if key in self.already_sent:
                                continue
                            self.already_sent.add(key)
                            self.handle_otp(panel.name, msg_date, number, service, message, otp)
                        except:
                            continue
                except Exception as e:
                    logging.error(f"Panel {panel.name} error: {e}")
            save_json("already_sent_panels.json", list(self.already_sent)[-5000:])
            time.sleep(8)

    def start(self):
        if self.running:
            return
        self.running = True
        self.already_sent = set(load_json("already_sent_panels.json", []))
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logging.info("প্যানেল মনিটরিং শুরু হয়েছে")

    def stop(self):
        self.running = False
        save_json("already_sent_panels.json", list(self.already_sent))
        logging.info("প্যানেল মনিটরিং বন্ধ")

panel_manager = PanelManager()

# ===================== স্ক্রিপ্ট ম্যানেজার =====================
import subprocess
import sys

class ScriptManager:
    """
    Same folder-এর সব .py script (varson3.py বাদে) auto-launch করে।
    Crash হলে 5 সেকেন্ড পর restart করে।
    """

    EXCLUDE = {os.path.basename(__file__), "varson3.py"}

    def __init__(self):
        self._procs: dict[str, subprocess.Popen] = {}   # filename -> Popen
        self._running = False
        self._thread: threading.Thread | None = None

    def _find_scripts(self) -> list[str]:
        base = os.path.dirname(os.path.abspath(__file__))
        scripts = []
        for f in sorted(os.listdir(base)):
            if f.endswith(".py") and f not in self.EXCLUDE:
                scripts.append(os.path.join(base, f))
        return scripts

    def _launch(self, path: str):
        try:
            proc = subprocess.Popen(
                [sys.executable, path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._procs[path] = proc
            logging.info(f"[ScriptManager] চালু: {os.path.basename(path)} (pid={proc.pid})")
        except Exception as e:
            logging.error(f"[ScriptManager] চালু করতে ব্যর্থ {os.path.basename(path)}: {e}")

    def _watch_loop(self):
        # প্রথমবার সব script launch করো
        for path in self._find_scripts():
            self._launch(path)

        while self._running:
            time.sleep(5)
            # Crash detect করে restart
            for path, proc in list(self._procs.items()):
                if proc.poll() is not None:          # process মরে গেছে
                    logging.warning(
                        f"[ScriptManager] {os.path.basename(path)} বন্ধ হয়ে গেছে "
                        f"(exit={proc.returncode}), restart করছি..."
                    )
                    self._launch(path)
            # নতুন script যোগ হলে সেটাও detect করো
            for path in self._find_scripts():
                if path not in self._procs:
                    logging.info(f"[ScriptManager] নতুন script পাওয়া গেছে: {os.path.basename(path)}")
                    self._launch(path)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logging.info("[ScriptManager] স্ক্রিপ্ট ম্যানেজার চালু হয়েছে")

    def stop(self):
        self._running = False
        for path, proc in self._procs.items():
            try:
                proc.terminate()
                logging.info(f"[ScriptManager] বন্ধ করা হয়েছে: {os.path.basename(path)}")
            except Exception:
                pass
        self._procs.clear()
        logging.info("[ScriptManager] সব script বন্ধ")

    def status(self) -> list[dict]:
        result = []
        for path, proc in self._procs.items():
            alive = proc.poll() is None
            result.append({
                "name": os.path.basename(path),
                "pid": proc.pid,
                "running": alive,
            })
        return result

script_manager = ScriptManager()

# ===================== অ্যাডমিন মেনু ও ফাংশন =====================
def admin_main_menu():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("📡 Panel Management", callback_data="admin_panels", style="primary"),
        types.InlineKeyboardButton("👥 User Management", callback_data="admin_users", style="primary"),
        types.InlineKeyboardButton("💰 Balance Management", callback_data="admin_balance", style="primary"),
        types.InlineKeyboardButton("📦 Service Management", callback_data="admin_services", style="primary"),
        types.InlineKeyboardButton("⚙️ OTP Rewards", callback_data="admin_rewards", style="primary"),
        types.InlineKeyboardButton("🔢 Set Number Count", callback_data="admin_set_count", style="primary"),
        types.InlineKeyboardButton("✏️ Set Bot Username", callback_data="admin_set_username", style="primary"),
        types.InlineKeyboardButton("🔒 Force Channels", callback_data="admin_force_channels", style="primary"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast", style="success"),
        types.InlineKeyboardButton("🚫 Ban/Unban", callback_data="admin_ban", style="danger"),
        types.InlineKeyboardButton("📩 Tickets", callback_data="admin_tickets", style="primary"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="admin_stats", style="primary"),
        types.InlineKeyboardButton("💸 Withdrawals", callback_data="admin_withdrawals", style="danger"),
        types.InlineKeyboardButton("📋 Help", callback_data="admin_help", style="primary")
    )
    return kb

def panels_menu(page=0):
    panels = panel_manager.list_panels()
    total = len(panels)
    per_page = 5
    start = page * per_page
    end = min(start + per_page, total)
    chunk = panels[start:end]
    kb = types.InlineKeyboardMarkup(row_width=2)
    for p in chunk:
        status = "🟢 ON" if p['enabled'] else "🔴 OFF"
        kb.add(
            types.InlineKeyboardButton(f"{p['name']} ({p['type']}) {status}", callback_data=f"adm_panel_toggle|{p['name']}", style="primary"),
            types.InlineKeyboardButton("❌ Remove", callback_data=f"adm_panel_remove|{p['name']}", style="danger")
        )
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅ Prev", callback_data=f"adm_panels_page|{page-1}", style="primary"))
    if end < total:
        nav.append(types.InlineKeyboardButton("Next ➡", callback_data=f"adm_panels_page|{page+1}", style="primary"))
    if nav:
        kb.add(*nav)
    kb.add(
        types.InlineKeyboardButton("➕ Add Panel", callback_data="adm_panel_add", style="success"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data="adm_panels_refresh", style="primary")
    )
    kb.add(
        types.InlineKeyboardButton("▶️ Start All", callback_data="adm_panels_start", style="success"),
        types.InlineKeyboardButton("⏹ Stop All", callback_data="adm_panels_stop", style="danger")
    )
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    return kb, total

def admin_services(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "📦 Loading services", show_alert=False)
    services = []
    if os.path.exists("numbers"):
        services = sorted([s for s in os.listdir("numbers") if os.path.isdir(f"numbers/{s}")])
    text = "📦 <b>Service Management</b>\n\n"
    if services:
        text += "Services:\n" + "\n".join([f"• {s}" for s in services])
    else:
        text += "No services."
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ Add", callback_data="adm_service_add", style="success"),
        types.InlineKeyboardButton("❌ Remove", callback_data="adm_service_remove", style="danger"),
        types.InlineKeyboardButton("📱 Upload Numbers", callback_data="adm_number_upload", style="primary"),
        types.InlineKeyboardButton("🗑 Remove Numbers", callback_data="adm_number_remove", style="danger")
    )
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    refresh(call.message.chat.id, call.from_user.id, text, kb)

def admin_ban_menu(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "🚫 Ban menu", show_alert=False)
    banned = get_banned_users()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔍 Search", callback_data="admin_ban_search", style="primary"))
    kb.add(types.InlineKeyboardButton("📋 Banned List", callback_data="admin_ban_list", style="danger"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    text = f"🚫 <b>Ban Management</b>\n\nTotal Banned: {len(banned)}"
    refresh(call.message.chat.id, call.from_user.id, text, kb)

def admin_force_channels(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "🔒 Channels", show_alert=False)
    channels = get_force_channels()
    text = "🔒 <b>Force Channels</b>\n\n"
    if channels:
        for ch in channels:
            text += f"• {ch['name']} ({ch['id']})\n"
    else:
        text += "No channels."
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Add", callback_data="adm_force_add", style="success"))
    kb.add(types.InlineKeyboardButton("❌ Remove", callback_data="adm_force_remove", style="danger"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="primary"))
    refresh(call.message.chat.id, call.from_user.id, text, kb)

def admin_set_count(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "🔢 Count", show_alert=False)
    kb = types.InlineKeyboardMarkup(row_width=4)
    for cnt in [2, 3, 5, 10, 15, 20]:
        kb.add(types.InlineKeyboardButton(f"{cnt}", callback_data=f"adm_set_count|{cnt}", style="primary"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    current = settings.get("number_count", 5)
    text = f"🔢 <b>Number Count</b>\n\nCurrent: {current}"
    refresh(call.message.chat.id, call.from_user.id, text, kb)

def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "💸 Withdrawals", show_alert=False)
    pending = [(k, v) for k, v in load_json("withdraw_requests.json", {}).items() if v.get("status") in ("pending", "approved")]
    if not pending:
        text = "💸 No pending/approved withdrawals."
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
        refresh(call.message.chat.id, call.from_user.id, text, kb)
        return
    text = "💸 <b>Pending / Approved Withdrawals</b>\n\n"
    for req_id, req in pending[:5]:
        text += f"👤 <code>{req['user_id']}</code> | 💰 ${req['amount']:.2f}\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 View All", callback_data="adm_withdrawals_all", style="primary"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    refresh(call.message.chat.id, call.from_user.id, text, kb)

def admin_back(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "⬅ Back", show_alert=False)
    text = "⚙️ <b>Admin Dashboard</b>\n\nSelect an option:"
    refresh(call.message.chat.id, call.from_user.id, text, admin_main_menu())

def adm_number_remove(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "🗑 Loading", show_alert=False)
    countries = set()
    if os.path.exists("numbers"):
        for service in os.listdir("numbers"):
            path = f"numbers/{service}"
            if os.path.isdir(path):
                for f in os.listdir(path):
                    if "_" in f:
                        countries.add(f.split("_")[0])
    if not countries:
        bot.answer_callback_query(call.id, "❌ No files", show_alert=True)
        return
    kb = types.InlineKeyboardMarkup(row_width=3)
    for c in sorted(countries):
        kb.add(types.InlineKeyboardButton(f"🗑 {c}", callback_data=f"adm_number_remove_country|{c}", style="danger"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_services", style="primary"))
    refresh(call.message.chat.id, call.from_user.id, "Select country:", kb)

def build_number_ui(country, service):
    flag = COUNTRY_FLAGS.get(country, "🌍")
    current_time = datetime.now().strftime("%I:%M %p")
    text = f"<b>{service}</b>\n"
    text += f"Country: {flag} {country}\n"
    text += f"Waiting for OTP... (Auto-expiry: 15m)\n"
    text += f"{current_time}\n\n"
    return text

def get_numbers_for_user(user, service, country, count=5):
    nums = load_numbers(service, country)
    if not nums:
        return []
    used = user_used_numbers.setdefault(user, [])
    available = [n for n in nums if n not in used]
    if len(available) < count:
        used.clear()
        available = load_numbers(service, country)
    selected = random.sample(available, min(count, len(available)))
    uid_str = str(user)
    log = user_numbers_log.get(uid_str, [])
    for n in selected:
        entry = f"{n} [{service}/{country}]"
        if entry not in log:
            log.append(entry)
    user_numbers_log[uid_str] = log[-50:]
    save_json("user_numbers_log.json", user_numbers_log)
    used.extend(selected)
    for n in selected:
        register_active_number(n, user, service, country)
        remove_number_from_file(service, country, n)
    return selected

def load_numbers(service, country):
    nums = []
    path = f"numbers/{service}"
    if not os.path.exists(path):
        return nums
    wanted = normalize_country_name(country)
    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if not os.path.isfile(fpath) or not fname.lower().endswith(".txt"):
            continue
        # File country can be in the filename, but the contents are also
        # accepted regardless of filename formatting.
        file_country = normalize_country_name(fname.rsplit("_", 1)[0].split("_")[0])
        if file_country != wanted and wanted.lower() not in fname.lower():
            continue
        try:
            with open(fpath, encoding="utf-8", errors="ignore") as file:
                nums.extend(clean_uploaded_numbers(file.readlines()))
        except Exception:
            pass
    return list(dict.fromkeys(nums))

def remove_number_from_file(service, country, number):
    path = f"numbers/{service}"
    if not os.path.exists(path):
        return
    for fname in os.listdir(path):
        if fname.startswith(country):
            fpath = f"{path}/{fname}"
            try:
                with open(fpath, "r", errors="ignore") as f:
                    lines = [x.strip() for x in f.readlines()]
                new_lines = [x for x in lines if x != number]
                if len(new_lines) != len(lines):
                    with open(fpath, "w") as f:
                        f.write("\n".join(new_lines) + ("\n" if new_lines else ""))
            except:
                pass

# ===================== টিকেট হ্যান্ডলার =====================
@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ticket_subject")
def ticket_subject(msg):
    uid = msg.from_user.id
    if is_user_banned(uid):
        return
    admin_state[uid]["subject"] = msg.text.strip()
    admin_state[uid]["step"] = "ticket_body"
    bot.send_message(msg.chat.id, "📝 Describe your issue:")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ticket_body")
def ticket_body(msg):
    uid = msg.from_user.id
    if is_user_banned(uid):
        return
    body = msg.text.strip()
    subject = admin_state[uid].get("subject", "No subject")
    tickets_data = get_tickets()
    ticket_id = len(tickets_data) + 1
    tickets_data.append({
        "id": ticket_id,
        "user_id": uid,
        "subject": subject,
        "body": body,
        "status": "open",
        "created": int(time.time()),
        "reply": None
    })
    save_tickets(tickets_data)
    admin_state.pop(uid, None)
    bot.send_message(msg.chat.id, f"✅ Ticket #{ticket_id} created!")
    for admin in ADMIN_IDS:
        try:
            bot.send_message(admin, f"📩 New Ticket #{ticket_id}\nUser: <code>{uid}</code>", parse_mode="HTML")
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_method|"))
def handle_withdraw_method(call):
    uid = call.from_user.id
    if is_user_banned(uid):
        return
    method = call.data.split("|", 1)[1]
    if method not in ("bkash", "nagad", "binance"):
        bot.answer_callback_query(call.id, "❌ Invalid method", show_alert=True)
        return

    admin_state[uid] = {"step": f"withdraw_{method}", "method": method}
    bot.answer_callback_query(call.id, "Selected", show_alert=False)
    if method == "bkash":
        text = "📱 <b>bKash Withdraw</b>\n\nSend your bKash number (e.g. 01XXXXXXXXX):"
    elif method == "nagad":
        text = "🟠 <b>Nagad Withdraw</b>\n\nSend your Nagad number (e.g. 01XXXXXXXXX):"
    else:
        text = "🟡 <b>Binance Withdraw</b>\n\nSend your Binance ID / Email / Pay ID:"
    refresh(call.message.chat.id, uid, text)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") in ("withdraw_bkash", "withdraw_nagad", "withdraw_binance"))
def handle_withdraw_input(msg):
    uid = msg.from_user.id
    if is_user_banned(uid):
        return
    uid_str = str(uid)
    state = admin_state.get(uid, {})
    method = state.get("method") or ({"withdraw_bkash":"bkash", "withdraw_nagad":"nagad", "withdraw_binance":"binance"}.get(state.get("step"), ""))
    account = msg.text.strip()

    if not account:
        refresh(msg.chat.id, uid, "❌ Please send valid account information.")
        return

    if method in ("bkash", "nagad"):
        digits = re.sub(r"\D", "", account)
        if len(digits) != 11 or not digits.startswith("01"):
            refresh(msg.chat.id, uid, f"❌ Invalid {'bKash' if method == 'bkash' else 'Nagad'} number. Please send an 11-digit number starting with 01.")
            return
        account = digits

    balance = float(user_balance.get(uid_str, 0.0))
    existing = load_json("withdraw_requests.json", {})
    if any(int(r.get("user_id", -1)) == uid and r.get("status") in ("pending", "approved") for r in existing.values()):
        admin_state.pop(uid, None)
        refresh(chat_id, uid, "⏳ You already have a pending/approved withdrawal. Please wait until it is paid or rejected.")
        return
    if balance < 1.0:
        admin_state.pop(uid, None)
        refresh(msg.chat.id, uid, "❌ Minimum $1.00 required.")
        return

    req_id = f"wr_{uid}_{int(time.time())}"
    reqs = load_json("withdraw_requests.json", {})
    reqs[req_id] = {
        "user_id": uid,
        "method": method,
        "account": account,
        "amount": balance,
        "status": "pending"
    }
    save_json("withdraw_requests.json", reqs)
    admin_state.pop(uid, None)

    method_name = {"bkash":"bKash", "nagad":"Nagad", "binance":"Binance"}.get(method, method)
    for admin in ADMIN_IDS:
        try:
            bot.send_message(
                admin,
                f"💸 <b>Withdraw Request</b>\n"
                f"👤 User: <code>{uid}</code>\n"
                f"💳 Method: <b>{method_name}</b>\n"
                f"📌 Account: <code>{account}</code>\n"
                f"💰 Amount: <b>${balance:.2f}</b>",
                parse_mode="HTML"
            )
        except:
            pass

    refresh(msg.chat.id, uid, f"✅ {method_name} withdrawal request sent.\n\n💰 Amount: ${balance:.2f}\n⏳ Wait for admin approval.")

@bot.message_handler(commands=["setpaymentgroup"])
def set_payment_group(msg):
    global PAYMENT_GROUP_ID
    if msg.from_user.id not in ADMIN_IDS:
        return
    if msg.chat.type not in ("group", "supergroup"):
        bot.send_message(msg.chat.id, "❌ Run /setpaymentgroup inside the payment group.")
        return
    PAYMENT_GROUP_ID = msg.chat.id
    settings["payment_group_id"] = PAYMENT_GROUP_ID
    save_json("settings.json", settings)
    bot.send_message(msg.chat.id, f"✅ Payment group configured. ID: <code>{PAYMENT_GROUP_ID}</code>", parse_mode="HTML")

@bot.message_handler(commands=["paymentgroup"])
def show_payment_group(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(msg.chat.id, f"💳 Payment Group ID: <code>{PAYMENT_GROUP_ID}</code>", parse_mode="HTML")

# ===================== অ্যাডমিন স্টেট মেশিন হ্যান্ডলার =====================
@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "addpanel_name")
def add_panel_name(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id]["name"] = msg.text.strip()
    admin_state[msg.from_user.id]["step"] = "addpanel_type"
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🔹 Login", callback_data="addpanel_type|login", style="primary"),
        types.InlineKeyboardButton("🔹 API", callback_data="addpanel_type|api", style="primary")
    )
    bot.send_message(msg.chat.id, "Select type:", reply_markup=kb)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "addpanel_url")
def add_panel_url(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id]["url"] = msg.text.strip()
    admin_state[msg.from_user.id]["step"] = "addpanel_username"
    bot.send_message(msg.chat.id, "Enter username:")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "addpanel_username")
def add_panel_username(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id]["username"] = msg.text.strip()
    admin_state[msg.from_user.id]["step"] = "addpanel_password"
    bot.send_message(msg.chat.id, "Enter password:")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "addpanel_password")
def add_panel_password(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    state = admin_state.pop(msg.from_user.id)
    config = {
        "name": state["name"],
        "url": state["url"],
        "type": "login",
        "username": state["username"],
        "password": msg.text.strip(),
        "enabled": True,
    }
    panel_manager.add_panel(config)
    kb, total = panels_menu(0)
    text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
    refresh(msg.chat.id, msg.from_user.id, text, kb)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "addpanel_api_url")
def add_panel_api_url(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id]["url"] = msg.text.strip()
    admin_state[msg.from_user.id]["step"] = "addpanel_api_token"
    bot.send_message(msg.chat.id, "Enter API token:")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "addpanel_api_token")
def add_panel_api_token(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    state = admin_state.pop(msg.from_user.id)
    config = {
        "name": state["name"],
        "url": state["url"],
        "type": "api",
        "token": msg.text.strip(),
        "enabled": True,
    }
    panel_manager.add_panel(config)
    kb, total = panels_menu(0)
    text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
    refresh(msg.chat.id, msg.from_user.id, text, kb)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "search_user")
def search_user_result(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(msg.text.strip())
        uid_str = str(uid)
        bal = float(user_balance.get(uid_str, 0.0))
        refs = len(load_json("referrals.json", {}).get(uid_str, []))
        nums = user_numbers_count.get(uid_str, 0)
        otp_info = otp_reward_log.get(uid_str, {"count": 0, "earned": 0.0})
        text = (
            f"👤 <b>User Details</b>\n\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"💰 Balance: ${bal:.2f}\n"
            f"🎁 OTP: {otp_info.get('count',0)}\n"
            f"🔗 Referrals: {refs}\n"
            f"📱 Numbers: {nums}\n"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔍 Another", callback_data="adm_user_search", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_users", style="danger"))
        bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=kb)
    except:
        bot.send_message(msg.chat.id, "❌ Invalid ID.")
    admin_state.pop(msg.from_user.id, None)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") in ["bal_add", "bal_remove"])
def handle_balance_change(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    step = admin_state[msg.from_user.id]["step"]
    try:
        parts = msg.text.strip().split()
        if len(parts) < 2:
            raise ValueError
        uid = int(parts[0])
        amount = float(parts[1])
        uid_str = str(uid)
        old = float(user_balance.get(uid_str, 0.0))
        if step == "bal_add":
            new = old + amount
            user_balance[uid_str] = round(new, 2)
            save_json("balances.json", user_balance)
            bot.send_message(msg.chat.id, f"✅ +${amount:.2f} to <code>{uid}</code>")
        else:
            new = max(0, old - amount)
            user_balance[uid_str] = round(new, 2)
            save_json("balances.json", user_balance)
            bot.send_message(msg.chat.id, f"✅ -${amount:.2f} from <code>{uid}</code>")
    except:
        bot.send_message(msg.chat.id, "❌ Invalid format.")
    admin_state.pop(msg.from_user.id, None)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "service_add")
def service_add(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    name = msg.text.strip().lower()
    os.makedirs(f"numbers/{name}", exist_ok=True)
    bot.send_message(msg.chat.id, f"✅ Service <b>{name}</b> added.", parse_mode="HTML")
    admin_state.pop(msg.from_user.id, None)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "upload_price")
def upload_price(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        price = float(msg.text.strip())
        admin_state[msg.from_user.id]["price"] = price
        admin_state[msg.from_user.id]["step"] = "upload_file"
        bot.send_message(
            msg.chat.id,
            f"💰 Price set: <b>${price:.2f}</b>\n"
            "📤 এখন TXT file পাঠান অথবা numbers copy-paste করুন।\n"
            "🌍 Country + flag automatic detect হবে।",
            parse_mode="HTML"
        )
    except:
        bot.send_message(msg.chat.id, "❌ Invalid price.")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "upload_label")
def upload_label_compat(msg):
    # Backward compatibility: label is no longer required.
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id]["step"] = "upload_file"
    raw_lines = re.split(r"[\n,;]+", msg.text or "")
    finish_number_upload(msg, raw_lines)


@bot.message_handler(content_types=["document"])
def handle_upload_file(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    state = admin_state.get(msg.from_user.id)
    if not isinstance(state, dict) or state.get("step") != "upload_file":
        return

    try:
        file_info = bot.get_file(msg.document.file_id)
        data = bot.download_file(file_info.file_path)
        raw_lines = data.decode("utf-8", errors="ignore").splitlines()
        finish_number_upload(msg, raw_lines)
    except Exception as e:
        logging.error(f"Upload error: {e}")
        bot.send_message(msg.chat.id, "❌ File read failed. Please send a TXT file or paste the numbers.")


def finish_number_upload(msg, raw_lines):
    uid = msg.from_user.id
    state = admin_state.get(uid, {})
    service = state.get("service")
    price = float(state.get("price", 0.05))

    lines = clean_uploaded_numbers(raw_lines)
    if not lines:
        bot.send_message(msg.chat.id, "❌ No valid phone numbers found.")
        return

    # Country is detected from each number's international calling code.
    grouped = {}
    unknown = []
    for number in lines:
        country = detect_country_from_number(number)
        if country == "Unknown":
            unknown.append(number)
        else:
            grouped.setdefault(country, []).append(number)

    # Never ask the admin to manually enter country.
    # Unknown numbers are reported so the admin can correct their source format.
    if unknown:
        preview = "\n".join(f"• {mask_number(n)}" for n in unknown[:10])
        bot.send_message(
            msg.chat.id,
            "⚠️ কিছু number-এর country code detect করা যায়নি।\n\n"
            f"{preview}\n\n"
            f"❌ Unknown: {len(unknown)}\n"
            "Country code সহ number দিন (যেমন +880..., +91..., +49...).\n"
            "কোনো manual country selection দরকার নেই।"
        )

    if not grouped:
        return

    os.makedirs(f"numbers/{service}", exist_ok=True)
    total_saved = 0
    summaries = []

    # The price entered by Admin is applied to EVERY uploaded number in this batch.
    for country, nums in grouped.items():
        safe_country = re.sub(r"[^A-Za-z0-9 -]", "", country).strip() or "Unknown"
        filename = f"{safe_country}_{int(time.time()*1000)}.txt"
        fpath = f"numbers/{service}/{filename}"

        # Merge into the existing country stock rather than replacing it.
        existing = []
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8", errors="ignore") as f:
                existing = clean_uploaded_numbers(f.readlines())
        merged = list(dict.fromkeys(existing + nums))

        with open(fpath, "w", encoding="utf-8") as f:
            f.write("\n".join(merged) + "\n")

        # Set the country reward to the exact price entered by Admin.
        otp_rewards[country] = price
        total_saved += len(nums)

        flag = COUNTRY_FLAGS.get(country, "🌍")
        summaries.append(f"{flag} <b>{country}</b> → {len(nums)} numbers → ${format_price(price)}")

    save_json("otp_rewards.json", otp_rewards)
    admin_state.pop(uid, None)

    text = (
        "✅ <b>NUMBER UPLOAD SUCCESSFUL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Service: <b>{service}</b>\n"
        f"💰 Admin Price: <b>${format_price(price)}</b>\n"
        f"📦 Added: <b>{total_saved}</b>\n\n"
        + "\n".join(summaries) +
        "\n━━━━━━━━━━━━━━━━━━━━━\n"
        "🌍 Country + flag: <b>Automatic</b>\n"
        "💵 Price: <b>Exactly the price you entered</b>"
    )
    bot.send_message(msg.chat.id, text, parse_mode="HTML")

    # Notify users about the newly available stock.
    try:
        bot_username = settings.get("bot_username") or bot.get_me().username
    except:
        bot_username = settings.get("bot_username", "bot")

    country_text = ", ".join(
        f"{COUNTRY_FLAGS.get(c, '🌍')} {c} • OTP ${format_price(float(otp_rewards.get(c, 0)))}" for c in grouped.keys()
    )
    broadcast_text = (
        "📢 <b>NEW NUMBER STOCK AVAILABLE</b>\n\n"
        f"📡 Service: <b>{service}</b>\n"
        f"🌍 {country_text}\n"
        f"💰 OTP Price: <b>${format_price(price)}</b>\n"
        f"📦 Added: <b>{total_saved}</b>\n"
        f"🤖 @{bot_username}"
    )
    for user_id in list(all_users):
        try:
            bot.send_message(user_id, broadcast_text, parse_mode="HTML")
            time.sleep(0.03)
        except:
            pass

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "upload_file", content_types=["text"])
def handle_upload_paste(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    # Accept one number per line, spaces, commas, or pasted blocks.
    raw_lines = re.split(r"[\n,;]+", msg.text or "")
    finish_number_upload(msg, raw_lines)


@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ban_search")
def ban_search_result(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(msg.text.strip())
        uid_str = str(uid)
        banned = get_banned_users()
        is_banned = uid_str in banned
        kb = types.InlineKeyboardMarkup()
        if is_banned:
            kb.add(types.InlineKeyboardButton("✅ Unban", callback_data=f"admin_unban|{uid_str}", style="success"))
        else:
            kb.add(types.InlineKeyboardButton("🚫 Ban", callback_data=f"admin_ban_user|{uid_str}", style="danger"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_ban", style="primary"))
        text = f"ID: <code>{uid}</code>\nStatus: {'🔴 Banned' if is_banned else '🟢 Active'}"
        bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=kb)
    except:
        bot.send_message(msg.chat.id, "❌ Invalid ID.")
    admin_state.pop(msg.from_user.id, None)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ticket_reply_id")
def ticket_reply_id(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        tid = int(msg.text.strip())
        tickets_data = get_tickets()
        ticket = next((t for t in tickets_data if t["id"] == tid and t["status"] == "open"), None)
        if not ticket:
            bot.send_message(msg.chat.id, "❌ Ticket not found.")
            admin_state.pop(msg.from_user.id, None)
            return
        admin_state[msg.from_user.id]["ticket_id"] = tid
        admin_state[msg.from_user.id]["step"] = "ticket_reply_body"
        bot.send_message(msg.chat.id, f"📝 Reply to Ticket #{tid}:")
    except:
        bot.send_message(msg.chat.id, "❌ Invalid ID.")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ticket_reply_body")
def ticket_reply_body(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    reply_text = msg.text.strip()
    tid = admin_state[msg.from_user.id]["ticket_id"]
    tickets_data = get_tickets()
    for t in tickets_data:
        if t["id"] == tid and t["status"] == "open":
            t["reply"] = reply_text
            t["status"] = "closed"
            break
    save_tickets(tickets_data)
    try:
        bot.send_message(t["user_id"], f"📩 Reply to Ticket #{tid}\n\n{reply_text}")
    except:
        pass
    bot.send_message(msg.chat.id, f"✅ Reply sent to Ticket #{tid}")
    admin_state.pop(msg.from_user.id, None)
    # রিফ্রেশ
    admin_tickets(msg)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "set_username")
def set_username(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    username = msg.text.strip().replace("@", "")
    settings["bot_username"] = username
    save_json("settings.json", settings)
    bot.send_message(msg.chat.id, f"✅ Set to @{username}")
    admin_state.pop(msg.from_user.id, None)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "force_add_channel")
def force_add_channel(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = [p.strip() for p in msg.text.split("|")]
        if len(parts) < 3:
            raise ValueError
        name, link, ch_id = parts[0], parts[1], int(parts[2])
        channels = get_force_channels()
        channels.append({"name": name, "link": link, "id": ch_id})
        save_force_channels(channels)
        bot.send_message(msg.chat.id, f"✅ {name} added!")
    except:
        bot.send_message(msg.chat.id, "❌ Invalid format.")
    admin_state.pop(msg.from_user.id, None)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "broadcast")
def send_broadcast(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    text = msg.text
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Send", callback_data="broadcast_send", style="success"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="admin_back", style="danger")
    )
    admin_state[msg.from_user.id]["broadcast_text"] = text
    bot.send_message(msg.chat.id, f"⚠️ Send to {len(all_users)} users?", reply_markup=kb)

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "reward_default")
def set_reward_default(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        amt = float(msg.text.strip())
        otp_rewards["default"] = amt
        save_json("otp_rewards.json", otp_rewards)
        bot.send_message(msg.chat.id, f"✅ Default set to ${amt:.2f}")
    except:
        bot.send_message(msg.chat.id, "❌ Invalid.")
    admin_state.pop(msg.from_user.id, None)

# ===================== হেল্পার ফাংশন =====================
def admin_tickets(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    tickets_data = get_tickets()
    open_tickets = [t for t in tickets_data if t["status"] == "open"]
    if not open_tickets:
        text = "📩 No open tickets."
    else:
        text = f"📩 <b>Open Tickets ({len(open_tickets)})</b>\n"
        for t in open_tickets[:5]:
            text += f"#{t['id']} | User: <code>{t['user_id']}</code>\n"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 View All", callback_data="admin_tickets_list|0", style="primary"))
    kb.add(types.InlineKeyboardButton("💬 Reply", callback_data="admin_ticket_reply", style="success"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    refresh(msg.chat.id, msg.from_user.id, text, kb)

def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    bot.answer_callback_query(call.id, "📊 Stats", show_alert=False)
    total = len(all_users)
    now = int(time.time())
    user_last_active = load_json("user_last_active.json", {})
    active = sum(1 for u in all_users if now - user_last_active.get(str(u), 0) <= 86400)
    total_nums = sum(user_numbers_count.values())
    total_bal = sum(float(v) for v in user_balance.values())
    pending = sum(1 for r in load_json("withdraw_requests.json", {}).values() if r.get("status") == "pending")
    text = (
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Users: {total}\n"
        f"🟢 Active: {active}\n"
        f"📱 Numbers: {total_nums}\n"
        f"💰 Balance: ${total_bal:.2f}\n"
        f"💸 Pending: {pending}\n"
        f"🚫 Banned: {len(get_banned_users())}"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats_refresh", style="primary"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
    refresh(call.message.chat.id, call.from_user.id, text, kb)

@bot.message_handler(commands=["cmd"])
def admin_cmd(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    text = "⚙️ <b>Admin Dashboard</b>\n\nSelect an option:"
    refresh(msg.chat.id, msg.from_user.id, text, admin_main_menu())

# ===================== 🎯 সিঙ্গেল কলব্যাক হ্যান্ডলার (সব বাটন ক্যাচ করে) =====================
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    uid = call.from_user.id
    data = call.data

    if is_user_banned(uid):
        bot.answer_callback_query(call.id, "🚫 Banned", show_alert=True)
        return

    # ----------------- ইউজার কলব্যাক -----------------
    if data == "force_verify":
        if check_force_join(uid):
            bot.answer_callback_query(call.id, "✅ Verified!")
            send_welcome(call.message.chat.id, uid)
        else:
            bot.answer_callback_query(call.id, "❌ Still not joined!", show_alert=True)
        return

    if data.startswith("srv|"):
        service = data.split("|")[1]
        bot.answer_callback_query(call.id, f"📦 {service} selected", show_alert=False)
        user_platform[uid] = service
        try:
            countries = sorted(set(normalize_country_name(f.rsplit("_", 2)[0]) for f in os.listdir(f"numbers/{service}") if "_" in f and f.lower().endswith(".txt")))
        except:
            countries = []
        kb = types.InlineKeyboardMarkup()
        last_country = get_last_active_country(service)
        if last_country in countries:
            countries.remove(last_country)
            countries.insert(0, last_country)
        for c in countries:
            flag = COUNTRY_FLAGS.get(c, "🌍")
            style = "success" if c == last_country else "primary"
            kb.add(types.InlineKeyboardButton(f"{flag} {c}", callback_data=f"cty|{c}", style=style))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_to_services", style="danger"))
        text = f"🌐 <b>{service}</b> — Select country:"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("cty|"):
        country = data.split("|")[1]
        bot.answer_callback_query(call.id, f"🌍 {country} loading", show_alert=False)
        uid_str = str(uid)
        service = user_platform.get(uid)
        user_country[uid] = country
        count = settings.get("number_count", 5)
        nums = get_numbers_for_user(uid, service, country, count)
        text = build_number_ui(country, service)
        user_numbers_count[uid_str] = user_numbers_count.get(uid_str, 0) + len(nums)
        save_json("user_numbers_count.json", user_numbers_count)
        kb = types.InlineKeyboardMarkup(row_width=1)
        for n in nums:
            kb.add(types.InlineKeyboardButton(text=f"📋 {n}", copy_text=types.CopyTextButton(text=n), style="primary"))
        kb.add(types.InlineKeyboardButton("🔄 Change", callback_data="change", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_to_country", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "change":
        bot.answer_callback_query(call.id, "🔄 Refreshing", show_alert=False)
        uid_str = str(uid)
        service = user_platform.get(uid)
        country = user_country.get(uid)
        if not service or not country:
            bot.answer_callback_query(call.id, "❌ Error!", show_alert=True)
            return
        count = settings.get("number_count", 5)
        nums = get_numbers_for_user(uid, service, country, count)
        text = build_number_ui(country, service)
        user_numbers_count[uid_str] = user_numbers_count.get(uid_str, 0) + len(nums)
        save_json("user_numbers_count.json", user_numbers_count)
        kb = types.InlineKeyboardMarkup(row_width=1)
        for n in nums:
            kb.add(types.InlineKeyboardButton(text=f"📋 {n}", copy_text=types.CopyTextButton(text=n), style="primary"))
        kb.add(types.InlineKeyboardButton("🔄 Change", callback_data="change", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_to_country", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "back_to_country":
        bot.answer_callback_query(call.id, "⬅ Back", show_alert=False)
        service = user_platform.get(uid)
        if not service:
            refresh(call.message.chat.id, uid, "❌ Error!")
            return
        try:
            countries = sorted(set(normalize_country_name(f.rsplit("_", 2)[0]) for f in os.listdir(f"numbers/{service}") if "_" in f and f.lower().endswith(".txt")))
        except:
            countries = []
        kb = types.InlineKeyboardMarkup()
        last_country = get_last_active_country(service)
        if last_country in countries:
            countries.remove(last_country)
            countries.insert(0, last_country)
        for c in countries:
            flag = COUNTRY_FLAGS.get(c, "🌍")
            style = "success" if c == last_country else "primary"
            kb.add(types.InlineKeyboardButton(f"{flag} {c}", callback_data=f"cty|{c}", style=style))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_to_services", style="danger"))
        text = f"🌐 <b>{service}</b> — Select country:"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "back_to_services":
        bot.answer_callback_query(call.id, "⬅ Back", show_alert=False)
        show_get_number(uid, call.message.chat.id)
        return

    if data == "ticket_open":
        bot.answer_callback_query(call.id, "📝 New ticket", show_alert=False)
        admin_state[uid] = {"step": "ticket_subject"}
        bot.send_message(call.message.chat.id, "📝 Enter ticket subject:")
        return

    if data == "ticket_my_list":
        bot.answer_callback_query(call.id, "📋 Your tickets", show_alert=False)
        tickets_data = get_tickets()
        my_tickets = [t for t in tickets_data if t["user_id"] == uid]
        if not my_tickets:
            text = "📋 No tickets found."
        else:
            text = "📋 <b>Your Tickets</b>\n\n"
            for t in my_tickets[-5:]:
                status = "🟢 Open" if t["status"] == "open" else "🔴 Closed"
                text += f"#{t['id']} | {t['subject']} — {status}\n"
                if t.get("reply"):
                    text += f"  💬 Reply: {t['reply'][:50]}...\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔄 Refresh", callback_data="ticket_my_list", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="support_back", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "support_back":
        bot.answer_callback_query(call.id, "⬅ Back", show_alert=False)
        show_support(uid, call.message.chat.id)
        return

    if data == "noop":
        bot.answer_callback_query(call.id)
        return

    # ----------------- অ্যাডমিন চেক -----------------
    if uid not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Unauthorized", show_alert=True)
        return

    # ----------------- অ্যাডমিন কলব্যাক -----------------
    if data == "admin_panels":
        bot.answer_callback_query(call.id, "📡 Loading panels", show_alert=False)
        kb, total = panels_menu(0)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("adm_panels_page|"):
        page = int(data.split("|")[1])
        bot.answer_callback_query(call.id, f"📄 Page {page+1}", show_alert=False)
        kb, total = panels_menu(page)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_panels_refresh":
        bot.answer_callback_query(call.id, "🔄 Refreshed", show_alert=False)
        kb, total = panels_menu(0)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_panels_start":
        panel_manager.start()
        bot.answer_callback_query(call.id, "✅ All started", show_alert=False)
        kb, total = panels_menu(0)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_panels_stop":
        panel_manager.stop()
        bot.answer_callback_query(call.id, "⏹ All stopped", show_alert=False)
        kb, total = panels_menu(0)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("adm_panel_toggle|"):
        name = data.split("|")[1]
        status = panel_manager.toggle_panel(name)
        if status is None:
            bot.answer_callback_query(call.id, "❌ Not found", show_alert=True)
            return
        bot.answer_callback_query(call.id, f"{name} → {'ON' if status else 'OFF'}", show_alert=False)
        kb, total = panels_menu(0)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("adm_panel_remove|"):
        name = data.split("|")[1]
        bot.answer_callback_query(call.id, f"🗑 {name}", show_alert=False)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ Yes", callback_data=f"adm_panel_remove_confirm|{name}", style="success"))
        kb.add(types.InlineKeyboardButton("❌ No", callback_data="adm_panels_refresh", style="danger"))
        refresh(call.message.chat.id, uid, f"⚠️ Remove <b>{name}</b>?", kb)
        return

    if data.startswith("adm_panel_remove_confirm|"):
        name = data.split("|")[1]
        panel_manager.remove_panel(name)
        bot.answer_callback_query(call.id, f"✅ {name} removed", show_alert=False)
        kb, total = panels_menu(0)
        text = f"📡 <b>Panel Management</b>\nTotal: {total} panels"
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_panel_add":
        bot.answer_callback_query(call.id, "📝 Add panel", show_alert=False)
        admin_state[uid] = {"step": "addpanel_name"}
        bot.send_message(call.message.chat.id, "📝 Enter panel name:")
        return

    if data.startswith("addpanel_type|"):
        typ = data.split("|")[1]
        admin_state[uid]["type"] = typ
        if typ == "login":
            admin_state[uid]["step"] = "addpanel_url"
            bot.send_message(call.message.chat.id, "Enter URL:")
        else:
            admin_state[uid]["step"] = "addpanel_api_url"
            bot.send_message(call.message.chat.id, "Enter API URL:")
        bot.answer_callback_query(call.id)
        return

    if data == "admin_users":
        bot.answer_callback_query(call.id, "👥 Loading users", show_alert=False)
        total = len(all_users)
        user_last_active = load_json("user_last_active.json", {})
        active = sum(1 for u in all_users if int(time.time()) - user_last_active.get(str(u), 0) <= 86400)
        text = f"👥 <b>User Management</b>\n\nTotal: {total}\nActive (24h): {active}"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📋 All Users", callback_data="adm_user_list|0", style="primary"),
            types.InlineKeyboardButton("🔍 Search User", callback_data="adm_user_search", style="primary"),
            types.InlineKeyboardButton("🏆 Top Balances", callback_data="adm_user_top", style="success"),
            types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats", style="primary")
        )
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("adm_user_list|"):
        page = int(data.split("|")[1])
        bot.answer_callback_query(call.id, f"📄 Page {page+1}", show_alert=False)
        per_page = 10
        uid_list = sorted(list(all_users))
        total = len(uid_list)
        start = page * per_page
        end = min(start + per_page, total)
        chunk = uid_list[start:end]
        lines = [f"📋 <b>User List</b> (Page {page+1})\n"]
        for u in chunk:
            u_str = str(u)
            bal = float(user_balance.get(u_str, 0.0))
            refs = len(load_json("referrals.json", {}).get(u_str, []))
            nums = user_numbers_count.get(u_str, 0)
            otp_cnt = otp_reward_log.get(u_str, {}).get("count", 0)
            lines.append(f"🆔 <code>{u}</code> | 💰${bal:.2f} | 🎁{otp_cnt} | 📱{nums}")
        text = "\n".join(lines)
        kb = types.InlineKeyboardMarkup()
        nav = []
        if page > 0:
            nav.append(types.InlineKeyboardButton("⬅ Prev", callback_data=f"adm_user_list|{page-1}", style="primary"))
        if end < total:
            nav.append(types.InlineKeyboardButton("Next ➡", callback_data=f"adm_user_list|{page+1}", style="primary"))
        if nav:
            kb.add(*nav)
        kb.add(types.InlineKeyboardButton("🔍 Search", callback_data="adm_user_search", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_users", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_user_search":
        bot.answer_callback_query(call.id, "🔍 Search", show_alert=False)
        admin_state[uid] = {"step": "search_user"}
        bot.send_message(call.message.chat.id, "🔍 Enter User ID:")
        return

    if data == "adm_user_top":
        bot.answer_callback_query(call.id, "🏆 Loading top", show_alert=False)
        sorted_bals = sorted([(u, float(b)) for u, b in user_balance.items() if float(b) > 0], key=lambda x: x[1], reverse=True)[:10]
        if not sorted_bals:
            text = "😔 No balance data."
        else:
            lines = ["🏆 <b>Top 10</b>\n"]
            for i, (u, b) in enumerate(sorted_bals, 1):
                lines.append(f"{i}. <code>{u}</code> — ${b:.2f}")
            text = "\n".join(lines)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_users", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "admin_balance":
        bot.answer_callback_query(call.id, "💰 Loading balance", show_alert=False)
        text = "💰 <b>Balance Management</b>"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("➕ Add", callback_data="adm_bal_add", style="success"),
            types.InlineKeyboardButton("➖ Remove", callback_data="adm_bal_remove", style="danger"),
            types.InlineKeyboardButton("📊 View All", callback_data="adm_bal_list|0", style="primary"),
            types.InlineKeyboardButton("⚙️ Rewards", callback_data="admin_rewards", style="primary")
        )
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("adm_bal_list|"):
        page = int(data.split("|")[1])
        bot.answer_callback_query(call.id, f"📄 Page {page+1}", show_alert=False)
        per_page = 10
        items = sorted([(u, float(b)) for u, b in user_balance.items()], key=lambda x: x[1], reverse=True)
        total = len(items)
        start = page * per_page
        end = min(start + per_page, total)
        chunk = items[start:end]
        lines = [f"📊 <b>Balance List</b> (Page {page+1})\n"]
        for u, b in chunk:
            lines.append(f"<code>{u}</code> → ${b:.2f}")
        text = "\n".join(lines)
        kb = types.InlineKeyboardMarkup()
        nav = []
        if page > 0:
            nav.append(types.InlineKeyboardButton("⬅ Prev", callback_data=f"adm_bal_list|{page-1}", style="primary"))
        if end < total:
            nav.append(types.InlineKeyboardButton("Next ➡", callback_data=f"adm_bal_list|{page+1}", style="primary"))
        if nav:
            kb.add(*nav)
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_balance", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_bal_add":
        bot.answer_callback_query(call.id, "➕ Add balance", show_alert=False)
        admin_state[uid] = {"step": "bal_add"}
        bot.send_message(call.message.chat.id, "📝 Send: <code>user_id amount</code>")
        return

    if data == "adm_bal_remove":
        bot.answer_callback_query(call.id, "➖ Remove balance", show_alert=False)
        admin_state[uid] = {"step": "bal_remove"}
        bot.send_message(call.message.chat.id, "📝 Send: <code>user_id amount</code>")
        return

    if data == "admin_services":
        admin_services(call)
        return

    if data == "adm_service_add":
        bot.answer_callback_query(call.id, "➕ Add service", show_alert=False)
        admin_state[uid] = {"step": "service_add"}
        bot.send_message(call.message.chat.id, "📝 Enter service name:")
        return

    if data == "adm_service_remove":
        bot.answer_callback_query(call.id, "🗑 Loading", show_alert=False)
        services = []
        if os.path.exists("numbers"):
            services = sorted([s for s in os.listdir("numbers") if os.path.isdir(f"numbers/{s}")])
        if not services:
            bot.answer_callback_query(call.id, "❌ No services", show_alert=True)
            return
        kb = types.InlineKeyboardMarkup()
        for s in services:
            kb.add(types.InlineKeyboardButton(f"🗑 {s}", callback_data=f"adm_service_remove_confirm|{s}", style="danger"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_services", style="primary"))
        refresh(call.message.chat.id, uid, "Select service to remove:", kb)
        return

    if data.startswith("adm_service_remove_confirm|"):
        name = data.split("|")[1]
        shutil.rmtree(f"numbers/{name}", ignore_errors=True)
        bot.answer_callback_query(call.id, f"✅ {name} removed", show_alert=False)
        admin_services(call)
        return

    if data == "adm_number_upload":
        bot.answer_callback_query(call.id, "📤 Upload", show_alert=False)
        services = []
        if os.path.exists("numbers"):
            services = sorted([s for s in os.listdir("numbers") if os.path.isdir(f"numbers/{s}")])
        if not services:
            bot.send_message(call.message.chat.id, "❌ No services.")
            return
        kb = types.InlineKeyboardMarkup(row_width=2)
        for s in services:
            kb.add(types.InlineKeyboardButton(f"📦 {s}", callback_data=f"upload_srv|{s}", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_services", style="danger"))
        refresh(call.message.chat.id, uid, "Select service:", kb)
        return

    if data.startswith("upload_srv|"):
        service = data.split("|")[1]
        bot.answer_callback_query(call.id, f"📦 {service}", show_alert=False)
        admin_state[uid] = {"service": service, "step": "upload_price"}
        bot.send_message(call.message.chat.id, f"📝 Enter OTP price (e.g. 0.10):")
        return

    if data == "adm_number_remove":
        adm_number_remove(call)
        return

    if data.startswith("adm_number_remove_country|"):
        country = data.split("|")[1]
        bot.answer_callback_query(call.id, f"🗑 {country}", show_alert=False)
        kb = types.InlineKeyboardMarkup()
        files = []
        if os.path.exists("numbers"):
            for service in os.listdir("numbers"):
                path = f"numbers/{service}"
                if os.path.isdir(path):
                    for f in os.listdir(path):
                        if f.startswith(country):
                            files.append((service, f))
                            kb.add(types.InlineKeyboardButton(f"🗑 {service}/{f}", callback_data=f"adm_number_del_file|{service}|{f}", style="danger"))
        if not files:
            bot.answer_callback_query(call.id, "No files", show_alert=True)
            return
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="adm_number_remove", style="primary"))
        refresh(call.message.chat.id, uid, f"Select file ({country}):", kb)
        return

    if data.startswith("adm_number_del_file|"):
        parts = data.split("|")
        service, filename = parts[1], parts[2]
        os.remove(f"numbers/{service}/{filename}")
        bot.answer_callback_query(call.id, "✅ Deleted", show_alert=False)
        adm_number_remove(call)
        return

    if data == "admin_rewards":
        bot.answer_callback_query(call.id, "⚙️ Rewards", show_alert=False)
        default = float(otp_rewards.get("default", 0.05))
        text = f"⚙️ <b>OTP Rewards</b>\n\nDefault: ${default:.2f}"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔧 Set Default", callback_data="adm_reward_default", style="primary"))
        kb.add(types.InlineKeyboardButton("📋 Countries", callback_data="adm_reward_list|0", style="primary"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "adm_reward_default":
        bot.answer_callback_query(call.id, "🔧 Set default", show_alert=False)
        admin_state[uid] = {"step": "reward_default"}
        bot.send_message(call.message.chat.id, "📝 Enter default amount:")
        return

    if data.startswith("adm_reward_list|"):
        page = int(data.split("|")[1])
        bot.answer_callback_query(call.id, f"📄 Page {page+1}", show_alert=False)
        countries = sorted([k for k in otp_rewards.keys() if k != "default" and not k.endswith("_off")])
        per_page = 10
        start = page * per_page
        end = min(start + per_page, len(countries))
        chunk = countries[start:end]
        lines = ["📋 <b>Country Rewards</b>\n"]
        for c in chunk:
            amt = float(otp_rewards.get(c, 0.05))
            off = otp_rewards.get(f"{c}_off", False)
            status = "🔴 OFF" if off else "🟢 ON"
            lines.append(f"{COUNTRY_FLAGS.get(c, '🌍')} {c} → ${format_price(amt)} {status}")
        if not lines[1:]:
            lines.append("No country rewards.")
        text = "\n".join(lines)
        kb = types.InlineKeyboardMarkup()
        nav = []
        if page > 0:
            nav.append(types.InlineKeyboardButton("⬅ Prev", callback_data=f"adm_reward_list|{page-1}", style="primary"))
        if end < len(countries):
            nav.append(types.InlineKeyboardButton("Next ➡", callback_data=f"adm_reward_list|{page+1}", style="primary"))
        if nav:
            kb.add(*nav)
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_rewards", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "admin_broadcast":
        bot.answer_callback_query(call.id, "📢 Broadcast", show_alert=False)
        admin_state[uid] = {"step": "broadcast"}
        bot.send_message(call.message.chat.id, "📝 Send broadcast message:")
        return

    if data == "broadcast_send":
        state = admin_state.get(uid, {})
        text = state.get("broadcast_text", "")
        if not text:
            bot.answer_callback_query(call.id, "No message", show_alert=True)
            return
        sent = 0
        for u in list(all_users):
            try:
                bot.send_message(u, text, parse_mode="HTML")
                sent += 1
                time.sleep(0.05)
            except:
                pass
        admin_state.pop(uid, None)
        bot.answer_callback_query(call.id, f"✅ Sent to {sent} users", show_alert=False)
        admin_back(call)
        return

    if data == "admin_set_count":
        admin_set_count(call)
        return

    if data.startswith("adm_set_count|"):
        count = int(data.split("|")[1])
        settings["number_count"] = count
        save_json("settings.json", settings)
        bot.answer_callback_query(call.id, f"✅ Set to {count}", show_alert=False)
        admin_set_count(call)
        return

    if data == "admin_set_username":
        bot.answer_callback_query(call.id, "✏️ Username", show_alert=False)
        admin_state[uid] = {"step": "set_username"}
        bot.send_message(call.message.chat.id, "📝 Enter bot username (without @):")
        return

    if data == "admin_force_channels":
        admin_force_channels(call)
        return

    if data == "adm_force_add":
        bot.answer_callback_query(call.id, "➕ Add channel", show_alert=False)
        admin_state[uid] = {"step": "force_add_channel"}
        bot.send_message(call.message.chat.id, "📝 Send: <code>Name | https://t.me/ch | -100123</code>", parse_mode="HTML")
        return

    if data == "adm_force_remove":
        bot.answer_callback_query(call.id, "🗑 Remove", show_alert=False)
        channels = get_force_channels()
        if not channels:
            bot.answer_callback_query(call.id, "❌ No channels", show_alert=True)
            return
        kb = types.InlineKeyboardMarkup()
        for i, ch in enumerate(channels):
            kb.add(types.InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"adm_force_del|{i}", style="danger"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_force_channels", style="primary"))
        refresh(call.message.chat.id, uid, "Select to remove:", kb)
        return

    if data.startswith("adm_force_del|"):
        idx = int(data.split("|")[1])
        channels = get_force_channels()
        if idx < len(channels):
            removed = channels.pop(idx)
            save_force_channels(channels)
            bot.answer_callback_query(call.id, f"✅ {removed['name']} removed", show_alert=False)
            admin_force_channels(call)
        else:
            bot.answer_callback_query(call.id, "❌ Not found", show_alert=True)
        return

    if data == "admin_ban":
        admin_ban_menu(call)
        return

    if data == "admin_ban_search":
        bot.answer_callback_query(call.id, "🔍 Search", show_alert=False)
        admin_state[uid] = {"step": "ban_search"}
        bot.send_message(call.message.chat.id, "🔍 Enter User ID:")
        return

    if data.startswith("admin_ban_user|"):
        uid_ban = data.split("|")[1]
        banned = get_banned_users()
        if uid_ban not in banned:
            banned.append(uid_ban)
            save_banned_users(banned)
            bot.answer_callback_query(call.id, f"✅ Banned", show_alert=False)
        admin_ban_menu(call)
        return

    if data.startswith("admin_unban|"):
        uid_ban = data.split("|")[1]
        banned = get_banned_users()
        if uid_ban in banned:
            banned.remove(uid_ban)
            save_banned_users(banned)
            bot.answer_callback_query(call.id, f"✅ Unbanned", show_alert=False)
        admin_ban_menu(call)
        return

    if data == "admin_ban_list":
        bot.answer_callback_query(call.id, "📋 List", show_alert=False)
        banned = get_banned_users()
        if not banned:
            text = "📋 No banned users."
        else:
            text = "📋 <b>Banned Users</b>\n\n" + "\n".join([f"• <code>{u}</code>" for u in banned])
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_ban", style="primary"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "admin_tickets":
        bot.answer_callback_query(call.id, "📩 Tickets", show_alert=False)
        tickets_data = get_tickets()
        open_tickets = [t for t in tickets_data if t["status"] == "open"]
        if not open_tickets:
            text = "📩 No open tickets."
        else:
            text = f"📩 <b>Open Tickets ({len(open_tickets)})</b>\n"
            for t in open_tickets[:5]:
                text += f"#{t['id']} | User: <code>{t['user_id']}</code>\n"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📋 View All", callback_data="admin_tickets_list|0", style="primary"))
        kb.add(types.InlineKeyboardButton("💬 Reply", callback_data="admin_ticket_reply", style="success"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data.startswith("admin_tickets_list|"):
        page = int(data.split("|")[1])
        bot.answer_callback_query(call.id, f"📄 Page {page+1}", show_alert=False)
        tickets_data = get_tickets()
        open_tickets = [t for t in tickets_data if t["status"] == "open"]
        per_page = 5
        start = page * per_page
        end = min(start + per_page, len(open_tickets))
        chunk = open_tickets[start:end]
        if not chunk:
            bot.answer_callback_query(call.id, "No more", show_alert=True)
            return
        text = f"📩 <b>Open Tickets</b> (Page {page+1})\n\n"
        for t in chunk:
            text += f"#{t['id']} | User: <code>{t['user_id']}</code>\nSubject: {t['subject']}\n\n"
        kb = types.InlineKeyboardMarkup()
        nav = []
        if page > 0:
            nav.append(types.InlineKeyboardButton("⬅ Prev", callback_data=f"admin_tickets_list|{page-1}", style="primary"))
        if end < len(open_tickets):
            nav.append(types.InlineKeyboardButton("Next ➡", callback_data=f"admin_tickets_list|{page+1}", style="primary"))
        if nav:
            kb.add(*nav)
        kb.add(types.InlineKeyboardButton("💬 Reply", callback_data="admin_ticket_reply", style="success"))
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_tickets", style="danger"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "admin_ticket_reply":
        bot.answer_callback_query(call.id, "💬 Reply", show_alert=False)
        admin_state[uid] = {"step": "ticket_reply_id"}
        bot.send_message(call.message.chat.id, "📝 Enter Ticket ID:")
        return

    if data == "admin_stats":
        admin_stats(call)
        return

    if data == "admin_stats_refresh":
        admin_stats(call)
        return

    if data == "admin_withdrawals":
        admin_withdrawals(call)
        return

    if data == "adm_withdrawals_all":
        pending = [(k, v) for k, v in load_json("withdraw_requests.json", {}).items() if v.get("status") in ("pending", "approved")]
        if not pending:
            bot.answer_callback_query(call.id, "No pending/approved", show_alert=True)
            return
        for req_id, req in pending[:10]:
            kb = types.InlineKeyboardMarkup()
            if req.get("status") == "pending":
                kb.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_wapprove|{req_id}", style="success"))
                kb.add(types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_wreject|{req_id}", style="danger"))
            else:
                kb.add(types.InlineKeyboardButton("💵 Mark Paid", callback_data=f"adm_wpaid|{req_id}", style="success"))
            method_name = {"bkash":"bKash", "nagad":"Nagad", "binance":"Binance"}.get(req.get("method"), req.get("method", "Unknown"))
            account = req.get("account", req.get("binance_id", "N/A"))
            bot.send_message(call.message.chat.id,
                f"💸 <b>Withdraw</b>\n"
                f"👤 User: <code>{req['user_id']}</code>\n"
                f"💳 Method: <b>{method_name}</b>\n"
                f"📌 Account: <code>{account}</code>\n"
                f"💰 ${req['amount']:.2f}\n"
                f"📌 Status: <b>{req.get('status','pending').upper()}</b>",
                parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("adm_wapprove|"):
        req_id = data.split("|")[1]
        reqs = load_json("withdraw_requests.json", {})
        if req_id not in reqs or reqs[req_id].get("status") != "pending":
            bot.answer_callback_query(call.id, "❌ Already processed", show_alert=True)
            return
        req = reqs[req_id]
        req["status"] = "approved"
        req["approved_at"] = int(time.time())
        req["approved_by"] = uid
        save_json("withdraw_requests.json", reqs)
        u = req["user_id"]
        method_name = {"bkash":"bKash", "nagad":"Nagad", "binance":"Binance"}.get(req.get("method"), req.get("method", "Unknown"))
        try:
            bot.send_message(u, f"✅ <b>Withdrawal approved</b>\n\n💳 Method: {method_name}\n💰 Amount: ${float(req['amount']):.2f}\n⏳ Payment is being processed.", parse_mode="HTML")
        except Exception:
            pass
        notify_payment_group(f"🟢 <b>Withdrawal Approved</b>\n👤 User: <code>{u}</code>\n💳 Method: <b>{method_name}</b>\n📌 Account: <code>{html.escape(str(req.get('account','N/A')))}</code>\n💰 Amount: <b>${float(req['amount']):.2f}</b>")
        notify_payment_group(
            f"✅ <b>Withdrawal Approved</b>\n"
            f"👤 User: <code>{u}</code>\n"
            f"💳 Method: {reqs[req_id].get('method', 'Unknown')}\n"
            f"📱 Account: <code>{reqs[req_id].get('account', 'N/A')}</code>\n"
            f"💰 Amount: <b>${format_price(reqs[req_id].get('amount', 0))}</b>"
        )
        bot.answer_callback_query(call.id, "✅ Approved", show_alert=False)
        admin_withdrawals(call)
        return

    if data.startswith("adm_wpaid|"):
        req_id = data.split("|", 1)[1]
        reqs = load_json("withdraw_requests.json", {})
        if req_id not in reqs or reqs[req_id].get("status") not in ("approved", "pending"):
            bot.answer_callback_query(call.id, "❌ Already processed", show_alert=True)
            return
        req = reqs[req_id]
        req["status"] = "paid"
        req["paid_at"] = int(time.time())
        req["paid_by"] = uid
        save_json("withdraw_requests.json", reqs)
        u = req["user_id"]
        # Deduct only when the payment is actually marked paid.
        current = float(user_balance.get(str(u), 0.0))
        amount = float(req.get("amount", 0.0))
        user_balance[str(u)] = round(max(0.0, current - amount), 8)
        save_json("balances.json", user_balance)
        method_name = {"bkash":"bKash", "nagad":"Nagad", "binance":"Binance"}.get(req.get("method"), req.get("method", "Unknown"))
        try:
            bot.send_message(u, f"🎉 <b>Withdrawal Paid</b>\n\n💳 Method: {method_name}\n💰 Amount: ${amount:.2f}\n✅ Payment marked as paid.", parse_mode="HTML")
        except Exception:
            pass
        notify_payment_group(f"💵 <b>Withdrawal Paid</b>\n👤 User: <code>{u}</code>\n💳 Method: <b>{method_name}</b>\n📌 Account: <code>{html.escape(str(req.get('account','N/A')))}</code>\n💰 Amount: <b>${amount:.2f}</b>")
        bot.answer_callback_query(call.id, "💵 Marked paid", show_alert=False)
        admin_withdrawals(call)
        return

    if data.startswith("adm_wreject|"):
        req_id = data.split("|")[1]
        reqs = load_json("withdraw_requests.json", {})
        if req_id not in reqs or reqs[req_id].get("status") != "pending":
            bot.answer_callback_query(call.id, "❌ Already processed", show_alert=True)
            return
        reqs[req_id]["status"] = "rejected"
        reqs[req_id]["rejected_at"] = int(time.time())
        reqs[req_id]["rejected_by"] = uid
        save_json("withdraw_requests.json", reqs)
        req = reqs[req_id]
        method_name = {"bkash":"bKash", "nagad":"Nagad", "binance":"Binance"}.get(req.get("method"), req.get("method", "Unknown"))
        try:
            bot.send_message(req["user_id"], f"❌ <b>Withdrawal rejected</b>\n\n💳 Method: {method_name}\n💰 Amount: ${float(req.get('amount',0)):.2f}", parse_mode="HTML")
        except Exception:
            pass
        notify_payment_group(f"🔴 <b>Withdrawal Rejected</b>\n👤 User: <code>{req['user_id']}</code>\n💳 Method: <b>{method_name}</b>\n📌 Account: <code>{html.escape(str(req.get('account','N/A')))}</code>\n💰 Amount: <b>${float(req.get('amount',0)):.2f}</b>")
        notify_payment_group(
            f"❌ <b>Withdrawal Rejected</b>\n"
            f"👤 User: <code>{reqs[req_id].get('user_id')}</code>\n"
            f"💳 Method: {reqs[req_id].get('method', 'Unknown')}\n"
            f"📱 Account: <code>{reqs[req_id].get('account', 'N/A')}</code>\n"
            f"💰 Amount: <b>${format_price(reqs[req_id].get('amount', 0))}</b>"
        )
        bot.answer_callback_query(call.id, "❌ Rejected", show_alert=False)
        admin_withdrawals(call)
        return

    if data == "admin_help":
        bot.answer_callback_query(call.id, "📋 Help", show_alert=False)
        text = (
            "📋 <b>Admin Help</b>\n\n"
            "• Panel Management – Add/remove/toggle\n"
            "• User Management – View/search\n"
            "• Balance – Add/remove/view\n"
            "• Services – Add/remove/upload\n"
            "• OTP Rewards – Set per country\n"
            "• Number Count – How many numbers\n"
            "• Bot Username – For referral link\n"
            "• Force Channels – Must join\n"
            "• Broadcast – Message all users\n"
            "• Ban/Unban – Block users\n"
            "• Tickets – Support replies\n"
            "• Withdrawals – Approve/reject"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="admin_back", style="primary"))
        refresh(call.message.chat.id, uid, text, kb)
        return

    if data == "admin_back":
        admin_back(call)
        return

    # যদি কোনো কিছু না মেলে
    bot.answer_callback_query(call.id, "⏳ Processing...", show_alert=False)

# ===================== বট রান =====================
if __name__ == "__main__":
    # Panel monitor
    if panel_manager.panels:
        panel_manager.start()
    else:
        logging.info("No panels, monitoring not started.")

    # Same-folder OTP script গুলো auto-launch
    script_manager.start()

    print("🤖 FULLY FIXED 100% BUTTONS WORKING BOT RUNNING...")
    print(f"📂 Script Manager: {len(script_manager._find_scripts())} টি script detected")

    try:
        bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
    except KeyboardInterrupt:
        panel_manager.stop()
        script_manager.stop()
        print("Bot stopped.")
