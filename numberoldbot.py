# ================= FINAL FULL OTP BOT WITH REFERRAL & BALANCE SYSTEM =================

import telebot
from telebot import types
import os, re, random, time, logging, asyncio, threading, json
from telethon import TelegramClient, events

# ================= CONFIG =================
TOKEN = "8636201280:AAGWPjNswilZvq-EFUzmnYXqcSkXDUvTAkQ"
ADMIN_IDS = [7525798243]
API_ID = 34536239
API_HASH = "5562555764e111c627f9da94c5cc756a"
OTP_GROUP_LINK = "https://t.me/axion_Otp"
OTP_GROUP_ID = None

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(level=logging.INFO)

# ================= DIRECTORIES =================
os.makedirs("numbers", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ================= JSON HELPERS =================
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
    with open(f"data/{fname}", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ================= FORCE JOIN =================
# Loaded dynamically from JSON — admin can add/remove via /force and /force_remove
REQUIRED_CHATS = load_json("force_channels.json", [
    {"id": -1002183064479, "link": "https://t.me/premiumbazar78", "name": "Premium Bazar"}
])

def get_force_channels():
    return load_json("force_channels.json", [
        {"id": -1002183064479, "link": "https://t.me/premiumbazar78", "name": "Premium Bazar"}
    ])

def check_join(uid):
    for chat in get_force_channels():
        try:
            member = bot.get_chat_member(chat["id"], uid)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def join_ui():
    channels = get_force_channels()
    kb = types.InlineKeyboardMarkup()
    for ch in channels:
        name = ch.get("name", "Channel")
        kb.add(types.InlineKeyboardButton(f"📢 {name}", url=ch["link"]))
    kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify"))
    return kb

# ================= LOAD PERSISTENT DATA =================
user_balance        = load_json("balances.json", {})
user_referrals      = load_json("referrals.json", {})
referred_by         = load_json("referred_by.json", {})
ref_channels        = load_json("ref_channels.json", [])
ref_settings        = load_json("ref_settings.json", {"amount": 0.02})
user_join_time      = load_json("user_join_time.json", {})
user_last_active    = load_json("user_last_active.json", {})
user_numbers_count  = load_json("user_numbers_count.json", {})
user_numbers_log    = load_json("user_numbers_log.json", {})   # {uid: ["+8801...", ...]}
withdraw_requests   = load_json("withdraw_requests.json", {})
all_users_list      = load_json("all_users.json", [])

all_users = set(all_users_list)

# Runtime data
user_country       = {}
user_platform      = {}
user_used_numbers  = {}
number_to_user     = {}
sent_otps          = set()
admin_state        = {}

# ================= COUNTRY FLAGS =================
COUNTRY_FLAGS = {
    "Afghanistan":"🇦🇫","Albania":"🇦🇱","Algeria":"🇩🇿","Andorra":"🇦🇩","Angola":"🇦🇴",
    "AntiguaandBarbuda":"🇦🇬","Argentina":"🇦🇷","Armenia":"🇦🇲","Australia":"🇦🇺","Austria":"🇦🇹",
    "Azerbaijan":"🇦🇿","Bahamas":"🇧🇸","Bahrain":"🇧🇭","Bangladesh":"🇧🇩","Barbados":"🇧🇧",
    "Belarus":"🇧🇾","Belgium":"🇧🇪","Belize":"🇧🇿","Benin":"🇧🇯","Bhutan":"🇧🇹",
    "Bolivia":"🇧🇴","BosniaandHerzegovina":"🇧🇦","Botswana":"🇧🇼","Brazil":"🇧🇷","Brunei":"🇧🇳",
    "Bulgaria":"🇧🇬","BurkinaFaso":"🇧🇫","Burundi":"🇧🇮","CaboVerde":"🇨🇻","Cambodia":"🇰🇭",
    "Cameroon":"🇨🇲","Canada":"🇨🇦","CentralAfricanRepublic":"🇨🇫","Chad":"🇹🇩","Chile":"🇨🇱",
    "China":"🇨🇳","Colombia":"🇨🇴","Comoros":"🇰🇲","Congo":"🇨🇩","CostaRica":"🇨🇷",
    "Croatia":"🇭🇷","Cuba":"🇨🇺","Cyprus":"🇨🇾","CzechRepublic":"🇨🇿","Denmark":"🇩🇰",
    "Djibouti":"🇩🇯","Dominica":"🇩🇲","DominicanRepublic":"🇩🇴","Ecuador":"🇪🇨","Egypt":"🇪🇬",
    "ElSalvador":"🇸🇻","EquatorialGuinea":"🇬🇶","Eritrea":"🇪🇷","Estonia":"🇪🇪","Eswatini":"🇸🇿",
    "Ethiopia":"🇪🇹","Fiji":"🇫🇯","Finland":"🇫🇮","France":"🇫🇷","Gabon":"🇬🇦",
    "Gambia":"🇬🇲","Georgia":"🇬🇪","Germany":"🇩🇪","Germany.":"🇩🇪","Ghana":"🇬🇭",
    "Greece":"🇬🇷","Grenada":"🇬🇩","Guatemala":"🇬🇹","Guinea":"🇬🇳","Guinea-Bissau":"🇬🇼",
    "Guyana":"🇬🇾","Haiti":"🇭🇹","Honduras":"🇭🇳","Hungary":"🇭🇺","Iceland":"🇮🇸",
    "India":"🇮🇳","Indonesia":"🇮🇩","Iran":"🇮🇷","Iraq":"🇮🇶","Ireland":"🇮🇪",
    "Israel":"🇮🇱","Italy":"🇮🇹","IvoryCoast":"🇨🇮","Jamaica":"🇯🇲","Japan":"🇯🇵",
    "Jordan":"🇯🇴","Kazakhstan":"🇰🇿","Kenya":"🇰🇪","Kiribati":"🇰🇮","Kuwait":"🇰🇼",
    "Kyrgyzstan":"🇰🇬","Laos":"🇱🇦","Latvia":"🇱🇻","Lebanon":"🇱🇧","Lesotho":"🇱🇸",
    "Liberia":"🇱🇷","Libya":"🇱🇾","Liechtenstein":"🇱🇮","Lithuania":"🇱🇹","Luxembourg":"🇱🇺",
    "Madagascar":"🇲🇬","Malawi":"🇲🇼","Malaysia":"🇲🇾","Maldives":"🇲🇻","Mali":"🇲🇱",
    "Malta":"🇲🇹","Marshall Islands":"🇲🇭","Mauritania":"🇲🇷","Mauritius":"🇲🇺","Mexico":"🇲🇽",
    "Micronesia":"🇫🇲","Moldova":"🇲🇩","Monaco":"🇲🇨","Mongolia":"🇲🇳","Montenegro":"🇲🇪",
    "Morocco":"🇲🇦","Mozambique":"🇲🇿","Myanmar":"🇲🇲","Namibia":"🇳🇦","Nauru":"🇳🇷",
    "Nepal":"🇳🇵","Netherlands":"🇳🇱","New Zealand":"🇳🇿","Nicaragua":"🇳🇮","Niger":"🇳🇪",
    "Nigeria":"🇳🇬","North Korea":"🇰🇵","North Macedonia":"🇲🇰","Norway":"🇳🇴","Oman":"🇴🇲",
    "Pakistan":"🇵🇰","Palau":"🇵🇼","Palestine":"🇵🇸","Panama":"🇵🇦","Papua New Guinea":"🇵🇬",
    "Paraguay":"🇵🇾","Peru":"🇵🇪","Philippines":"🇵🇭","Poland":"🇵🇱","Portugal":"🇵🇹",
    "Qatar":"🇶🇦","Romania":"🇷🇴","Russia":"🇷🇺","Rwanda":"🇷🇼","SaintKittsandNevis":"🇰🇳",
    "Saint Lucia":"🇱🇨","Saint Vincent and the Grenadines":"🇻🇨","Samoa":"🇼🇸","San Marino":"🇸🇲",
    "Sao Tome and Principe":"🇸🇹","SaudiArabia":"🇸🇦","Senegal":"🇸🇳","Serbia":"🇷🇸",
    "Seychelles":"🇸🇨","SierraLeone":"🇸🇱","Singapore":"🇸🇬","Slovakia":"🇸🇰","Slovenia":"🇸🇮",
    "SolomonIslands":"🇸🇧","Somalia":"🇸🇴","SouthAfrica":"🇿🇦","SouthKorea":"🇰🇷","SouthSudan":"🇸🇸",
    "Spain":"🇪🇸","SriLanka":"🇱🇰","Sudan":"🇸🇩","Suriname":"🇸🇷","Sweden":"🇸🇪",
    "Switzerland":"🇨🇭","Syria":"🇸🇾","Taiwan":"🇹🇼","Tajikistan":"🇹🇯","Tanzania":"🇹🇿",
    "Thailand":"🇹🇭","Timor-Leste":"🇹🇱","Togo":"🇹🇬","Tonga":"🇹🇴","Trinidad and Tobago":"🇹🇹",
    "Tunisia":"🇹🇳","Turkey":"🇹🇷","Turkmenistan":"🇹🇲","Tuvalu":"🇹🇻","Uganda":"🇺🇬",
    "Ukraine":"🇺🇦","UnitedArabEmirates":"🇦🇪","UnitedKingdom":"🇬🇧","UnitedStates":"🇺🇸",
    "Uruguay":"🇺🇾","Uzbekistan":"🇺🇿","Vanuatu":"🇻🇺","Vatican City":"🇻🇦","Venezuela":"🇻🇪",
    "Vietnam":"🇻🇳","Yemen":"🇾🇪","Zambia":"🇿🇲","Zimbabwe":"🇿🇼"
}

# ================= REFERRAL HELPERS =================
def get_bot_username():
    try:
        return bot.get_me().username
    except:
        return "YourBot"

def get_referral_link(uid):
    return f"https://t.me/{get_bot_username()}?start=ref_{uid}"

def check_referral_channels_joined(uid):
    channels = load_json("ref_channels.json", [])
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

def add_referral_balance(referrer_id):
    settings = load_json("ref_settings.json", {"amount": 0.02})
    amount = float(settings.get("amount", 0.02))
    uid_str = str(referrer_id)
    current = float(user_balance.get(uid_str, 0.0))
    user_balance[uid_str] = round(current + amount, 2)
    save_json("balances.json", user_balance)

# ================= PROCESS REFERRAL =================
def process_referral(uid):
    uid_str = str(uid)
    if uid_str not in referred_by:
        return
    referrer_id = referred_by[uid_str]
    referrer_str = str(referrer_id)
    refs = user_referrals.get(referrer_str, [])

    # type-safe check (JSON loads as int)
    if uid in refs or uid_str in [str(r) for r in refs]:
        return

    refs.append(uid)
    user_referrals[referrer_str] = refs
    save_json("referrals.json", user_referrals)

    # Check referral channel requirement
    if not check_referral_channels_joined(referrer_id):
        # Notify referrer they need to join channels
        channels = load_json("ref_channels.json", [])
        if channels:
            try:
                kb = types.InlineKeyboardMarkup()
                for ch in channels:
                    kb.add(types.InlineKeyboardButton(f"📢 {ch['name']}", url=ch["link"]))
                bot.send_message(
                    referrer_id,
                    "⚠️ <b>Referral received but balance not added!</b>\n\n"
                    "💡 Join the channels below to receive your balance:",
                    parse_mode="HTML",
                    reply_markup=kb
                )
            except:
                pass
        return

    # Add balance
    add_referral_balance(referrer_id)
    settings = load_json("ref_settings.json", {"amount": 0.02})
    amount = float(settings.get("amount", 0.02))
    new_balance = float(user_balance.get(referrer_str, 0.0))

    # Notify referrer
    try:
        bot.send_message(
            referrer_id,
            f"🎉 <b>New referral successful!</b>\n\n"
            f"👤 <b>User ID:</b> <code>{uid}</code>\n"
            f"💰 <b>+${amount:.2f}</b> has been added to your balance!\n"
            f"💵 <b>Total Balance:</b> ${new_balance:.2f}",
            parse_mode="HTML"
        )
    except:
        pass

    # Notify admin
    total_refs = len(user_referrals.get(referrer_str, []))
    admin_text = (
        f"📣 <b>New Referral!</b>\n\n"
        f"👤 <b>Referrer ID:</b> <code>{referrer_id}</code>\n"
        f"🆕 <b>New User ID:</b> <code>{uid}</code>\n"
        f"💰 <b>Amount Added:</b> ${amount:.2f}\n"
        f"📊 <b>Referrer's Total Referrals:</b> {total_refs}\n"
        f"💵 <b>Referrer Balance:</b> ${new_balance:.2f}"
    )
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, admin_text, parse_mode="HTML")
        except:
            pass

# ================= MAIN MENU =================
def show_main_menu(chat_id, uid, message_id=None):
    text = (
        "╔═════════════════════════════╗\n"
        "    🌟 Welcome to Premium Bazar 🌟\n"
        "  Please select a service\n"
        "╚═════════════════════════════╝\n"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📱 Get Numbers", callback_data="get_numbers"))
    kb.add(types.InlineKeyboardButton("👥 Referral", callback_data="referral_menu"))
    kb.add(types.InlineKeyboardButton("💰 My Balance", callback_data="my_balance"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=kb)
        except:
            bot.send_message(chat_id, text, reply_markup=kb)
    else:
        bot.send_message(chat_id, text, reply_markup=kb)

# ================= START =================
@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    uid_str = str(uid)

    args = msg.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        referrer_id_str = args[1].replace("ref_", "")
        if referrer_id_str != uid_str and uid_str not in referred_by:
            referred_by[uid_str] = int(referrer_id_str)
            save_json("referred_by.json", referred_by)

    if not check_join(uid):
        bot.send_message(
            msg.chat.id,
            "🚫 Please join the required channels first",
            reply_markup=join_ui()
        )
        return

    all_users.add(uid)
    save_json("all_users.json", list(all_users))

    now = int(time.time())
    if uid_str not in user_join_time:
        user_join_time[uid_str] = now
        save_json("user_join_time.json", user_join_time)

    user_last_active[uid_str] = now
    save_json("user_last_active.json", user_last_active)

    # Process referral after join verified
    process_referral(uid)

    show_main_menu(msg.chat.id, uid)

# ================= VERIFY BUTTON =================
@bot.callback_query_handler(func=lambda c: c.data == "verify")
def verify(call):
    uid = call.from_user.id
    try:
        if check_join(uid):
            all_users.add(uid)
            save_json("all_users.json", list(all_users))
            uid_str = str(uid)
            now = int(time.time())
            if uid_str not in user_join_time:
                user_join_time[uid_str] = now
                save_json("user_join_time.json", user_join_time)
            user_last_active[uid_str] = now
            save_json("user_last_active.json", user_last_active)
            # Process referral when user joins via verify button
            process_referral(uid)
            show_main_menu(call.message.chat.id, uid, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "🚫 Please join the channel first")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=join_ui())
    except Exception as e:
        print("VERIFY ERROR:", e)
        bot.answer_callback_query(call.id, "❌ Error")

# ================= GET NUMBERS =================
@bot.callback_query_handler(func=lambda c: c.data == "get_numbers")
def get_numbers_menu(call):
    uid = call.from_user.id
    uid_str = str(uid)
    user_last_active[uid_str] = int(time.time())
    save_json("user_last_active.json", user_last_active)

    text = (
        "╔═════════════════════════════╗\n"
        "    🌟 Welcome to Premium Bazar 🌟\n"
        "  Please select your desired service\n"
        "╚═════════════════════════════╝\n\n"
    )
    kb = types.InlineKeyboardMarkup()
    if os.path.exists("numbers"):
        for s in os.listdir("numbers"):
            kb.add(types.InlineKeyboardButton(f"📦 {s}", callback_data=f"srv|{s}"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=kb)

# ================= REFERRAL MENU =================
@bot.callback_query_handler(func=lambda c: c.data == "referral_menu")
def referral_menu(call):
    uid = call.from_user.id
    uid_str = str(uid)
    ref_link = get_referral_link(uid)
    total_refs = len(user_referrals.get(uid_str, []))
    settings = load_json("ref_settings.json", {"amount": 0.02})
    amount_per = float(settings.get("amount", 0.02))

    text = (
        "╔══════════════════════════╗\n"
        "        👥 Referral Panel\n"
        "╚══════════════════════════╝\n\n"
        f"🔗 <b>Your Referral Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👤 <b>Total Referrals:</b> {total_refs}\n"
        f"💰 <b>Per Referral:</b> ${amount_per:.2f}\n\n"
        "⚠️ <i>Balance will only be added for genuinely joined users.</i>"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 Copy Link", callback_data="copy_ref_link"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "copy_ref_link")
def copy_ref_link(call):
    uid = call.from_user.id
    ref_link = get_referral_link(uid)
    bot.answer_callback_query(call.id, "✅ Link sent below!")
    bot.send_message(
        call.message.chat.id,
        f"🔗 <b>Your Referral Link:</b>\n\n<code>{ref_link}</code>\n\n"
        f"👆 Copy the link above and share it with your friends!",
        parse_mode="HTML"
    )

# ================= MY BALANCE =================
@bot.callback_query_handler(func=lambda c: c.data == "my_balance")
def my_balance(call):
    uid = call.from_user.id
    uid_str = str(uid)
    balance = float(user_balance.get(uid_str, 0.0))

    text = (
        "╔══════════════════════════╗\n"
        "        💰 My Balance\n"
        "╚══════════════════════════╝\n\n"
        f"💵 <b>Your Balance:</b> ${balance:.2f}\n\n"
    )
    if balance >= 1.0:
        text += "✅ <i>You can withdraw!</i>"
    else:
        text += f"⚠️ <i>Minimum $1.00 required.\nYou need ${max(0, 1.0 - balance):.2f} more.</i>"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_request"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_main"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)

# ================= WITHDRAW =================
@bot.callback_query_handler(func=lambda c: c.data == "withdraw_request")
def withdraw_request(call):
    uid = call.from_user.id
    uid_str = str(uid)
    balance = float(user_balance.get(uid_str, 0.0))

    if balance < 1.0:
        needed = round(1.0 - balance, 2)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="my_balance"))
        try:
            bot.edit_message_text(
                "╔══════════════════════════╗\n"
                "        💸 Withdraw\n"
                "╚══════════════════════════╝\n\n"
                f"💵 <b>Your Balance:</b> ${balance:.2f}\n\n"
                f"❌ <b>Cannot withdraw!</b>\n"
                f"⚠️ Minimum <b>$1.00</b> required.\n"
                f"Add <b>${needed:.2f}</b> more.\n\n"
                f"💡 <i>Refer friends to increase your balance!</i>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=kb
            )
        except:
            bot.answer_callback_query(call.id, f"❌ Minimum $1.00 required! You need ${needed:.2f} more.", show_alert=True)
        return

    admin_state[uid] = {"step": "withdraw_binance"}
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ Cancel", callback_data="my_balance"))
    try:
        bot.edit_message_text(
            "╔══════════════════════════╗\n"
            "        💸 Withdraw Request\n"
            "╚══════════════════════════╝\n\n"
            f"💰 <b>Your Balance:</b> ${balance:.2f}\n\n"
            "📝 Send your <b>Binance ID / Email</b>:\n\n"
            "<i>Type below and send.</i>",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=kb
        )
    except:
        bot.send_message(
            call.message.chat.id,
            "📝 Send your <b>Binance ID / Email</b>:",
            parse_mode="HTML",
            reply_markup=kb
        )

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "withdraw_binance")
def handle_binance_id(msg):
    uid = msg.from_user.id
    uid_str = str(uid)
    binance_id = msg.text.strip()
    balance = float(user_balance.get(uid_str, 0.0))

    if balance < 1.0:
        bot.send_message(msg.chat.id, "❌ Insufficient balance!")
        admin_state.pop(uid, None)
        return

    req_id = f"wr_{uid}_{int(time.time())}"
    withdraw_requests[req_id] = {
        "user_id": uid,
        "binance_id": binance_id,
        "amount": balance,
        "status": "pending",
        "time": int(time.time())
    }
    save_json("withdraw_requests.json", withdraw_requests)
    admin_state.pop(uid, None)

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"wapprove|{req_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"wreject|{req_id}")
    )
    admin_msg = (
        f"💸 <b>New Withdraw Request!</b>\n\n"
        f"👤 <b>User ID:</b> <code>{uid}</code>\n"
        f"💳 <b>Binance ID:</b> <code>{binance_id}</code>\n"
        f"💰 <b>Amount:</b> ${balance:.2f}\n"
        f"🕒 <b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, admin_msg, parse_mode="HTML", reply_markup=kb)
        except:
            pass

    bot.send_message(
        msg.chat.id,
        "✅ <b>Withdraw request submitted!</b>\n\n"
        "⏳ You will be notified once the admin approves it.",
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("wapprove|"))
def approve_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    req_id = call.data.split("|")[1]
    req = withdraw_requests.get(req_id)
    if not req or req["status"] != "pending":
        bot.answer_callback_query(call.id, "❌ Request not found or already processed")
        return
    req["status"] = "approved"
    save_json("withdraw_requests.json", withdraw_requests)
    uid_str = str(req["user_id"])
    user_balance[uid_str] = 0.0
    save_json("balances.json", user_balance)
    bot.answer_callback_query(call.id, "✅ Approved!")
    bot.edit_message_text(
        call.message.text + "\n\n✅ <b>APPROVED</b>",
        call.message.chat.id, call.message.message_id,
        parse_mode="HTML"
    )
    try:
        bot.send_message(
            req["user_id"],
            f"🎉 <b>Your Withdraw has been Approved!</b>\n\n"
            f"💰 <b>Amount:</b> ${req['amount']:.2f}\n"
            f"💳 <b>Binance ID:</b> <code>{req['binance_id']}</code>\n\n"
            f"✅ Payment has been sent.",
            parse_mode="HTML"
        )
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("wreject|"))
def reject_withdraw(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    req_id = call.data.split("|")[1]
    req = withdraw_requests.get(req_id)
    if not req or req["status"] != "pending":
        bot.answer_callback_query(call.id, "❌ Request not found")
        return
    req["status"] = "rejected"
    save_json("withdraw_requests.json", withdraw_requests)
    bot.answer_callback_query(call.id, "❌ Rejected")
    bot.edit_message_text(
        call.message.text + "\n\n❌ <b>REJECTED</b>",
        call.message.chat.id, call.message.message_id,
        parse_mode="HTML"
    )
    try:
        bot.send_message(
            req["user_id"],
            "❌ <b>Your Withdraw Request has been Rejected.</b>\n\nPlease contact the Admin.",
            parse_mode="HTML"
        )
    except:
        pass

# ================= BACK MAIN =================
@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def back_main(call):
    show_main_menu(call.message.chat.id, call.from_user.id, call.message.message_id)

# ================= SERVICE → COUNTRY =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("srv|"))
def choose_country(call):
    uid = call.from_user.id
    service = call.data.split("|")[1]
    user_platform[uid] = service
    countries = set(f.split("_")[0] for f in os.listdir(f"numbers/{service}") if "_" in f)
    kb = types.InlineKeyboardMarkup()
    for c in sorted(countries):
        kb.add(types.InlineKeyboardButton(c, callback_data=f"cty|{c}"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="get_numbers"))
    text = f"╔══════════════════╗\n   🌐 {service} - Select Country 🌐\n╚══════════════════╝\n"
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, reply_markup=kb)

# ================= COUNTRY → NUMBERS =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("cty|"))
def send_numbers(call):
    uid = call.from_user.id
    uid_str = str(uid)
    country = call.data.split("|")[1]
    service = user_platform.get(uid)
    user_country[uid] = country

    nums = get_numbers_for_user(uid, service, country)
    text = build_number_ui(country, service, nums)

    user_numbers_count[uid_str] = user_numbers_count.get(uid_str, 0) + len(nums)
    save_json("user_numbers_count.json", user_numbers_count)
    user_last_active[uid_str] = int(time.time())
    save_json("user_last_active.json", user_last_active)

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Change", callback_data="change"))
    kb.add(types.InlineKeyboardButton("💬 OTP Group", url=OTP_GROUP_LINK))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_cty"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# ================= CHANGE NUMBERS =================
@bot.callback_query_handler(func=lambda c: c.data == "change")
def change(call):
    uid = call.from_user.id
    uid_str = str(uid)
    if not check_join(uid):
        bot.answer_callback_query(call.id, "🚫 Join first")
        return
    service = user_platform.get(uid)
    country = user_country.get(uid)
    if not service or not country:
        bot.answer_callback_query(call.id, "❌ Error! Please send /start again")
        return
    nums = get_numbers_for_user(uid, service, country)
    text = build_number_ui(country, service, nums)
    user_numbers_count[uid_str] = user_numbers_count.get(uid_str, 0) + len(nums)
    save_json("user_numbers_count.json", user_numbers_count)
    user_last_active[uid_str] = int(time.time())
    save_json("user_last_active.json", user_last_active)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🔄 Change", callback_data="change"))
    kb.add(types.InlineKeyboardButton("💬 OTP Group", url=OTP_GROUP_LINK))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_cty"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# ================= BACK HANDLERS =================
@bot.callback_query_handler(func=lambda c: c.data == "back_cty")
def back_to_country(call):
    uid = call.from_user.id
    service = user_platform.get(uid)
    if not service:
        show_main_menu(call.message.chat.id, uid, call.message.message_id)
        return
    countries = set(f.split("_")[0] for f in os.listdir(f"numbers/{service}") if "_" in f)
    text = (
        "╔════════════════════════╗\n"
        f"   🌐 {service} - Country List 🌐\n"
        "╚════════════════════════╝\n\n"
        "Please select your country:\n"
    )
    kb = types.InlineKeyboardMarkup()
    for c in sorted(countries):
        kb.add(types.InlineKeyboardButton(c, callback_data=f"cty|{c}"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="get_numbers"))
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# ================= HELPER FUNCTIONS =================
def build_number_ui(country, service, nums):
    text = f"╔══════════════════╗\n   🌍 {country} ({service})\n╚══════════════════╝\n\n"
    for i, n in enumerate(nums, 1):
        text += f"📲 **{i}** ➜ `{n}`\n\n"
    text += "━━━━━━━━━━━━━━━\n⏳ **Waiting for OTP...**"
    return text

def load_numbers(service, country):
    nums = []
    path = f"numbers/{service}"
    if not os.path.exists(path):
        return nums
    for f in os.listdir(path):
        if f.startswith(country):
            with open(f"{path}/{f}", errors="ignore") as file:
                nums.extend([x.strip() for x in file if x.strip()])
    return list(set(nums))

def count_left(service, country):
    nums = load_numbers(service, country)
    used = set(number_to_user.keys())
    return len([n for n in nums if n.replace("+", "") not in used])

LOW_STOCK_THRESHOLD = 150

def check_and_notify_low_stock(service, country):
    remaining = count_left(service, country)
    if remaining <= LOW_STOCK_THRESHOLD:
        flag = COUNTRY_FLAGS.get(country, "🌍")
        alert_text = (
            f"⚠️ <b>Low Stock Alert!</b>\n\n"
            f"📡 <b>Service:</b> {service}\n"
            f"🌍 <b>Country:</b> {flag} {country}\n"
            f"📉 <b>Remaining:</b> {remaining}\n\n"
            f"❗ <i>Please add more numbers.</i>"
        )
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, alert_text, parse_mode="HTML")
            except:
                pass

def remove_number_from_file(service, country, number):
    path = f"numbers/{service}"
    if not os.path.exists(path):
        return
    for fname in os.listdir(path):
        if fname.startswith(country):
            fpath = f"{path}/{fname}"
            with open(fpath, "r", errors="ignore") as f:
                lines = [x.strip() for x in f.readlines()]
            new_lines = [x for x in lines if x != number]
            if len(new_lines) != len(lines):
                with open(fpath, "w") as f:
                    f.write("\n".join(new_lines) + ("\n" if new_lines else ""))

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
    # Log numbers per user (persistent)
    uid_str = str(user)
    log = user_numbers_log.get(uid_str, [])
    for n in selected:
        entry = f"{n} [{service}/{country}]"
        if entry not in log:
            log.append(entry)
    user_numbers_log[uid_str] = log[-50:]  # keep last 50
    save_json("user_numbers_log.json", user_numbers_log)
    used.extend(selected)
    for n in selected:
        number_to_user[n.replace("+", "")] = user
        remove_number_from_file(service, country, n)
    check_and_notify_low_stock(service, country)
    return selected

# ================= ADMIN: /cmd =================
@bot.message_handler(commands=["cmd"])
def show_cmd(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    text = (
        "⚙️ <b>Admin Commands:</b>\n\n"
        "📦 <b>Service:</b>\n"
        "/addservice name\n"
        "/removeservice name\n\n"
        "📱 <b>Numbers:</b>\n"
        "/addnumber\n"
        "/removenumber\n\n"
        "👑 <b>Admin:</b>\n"
        "/addadmin id\n"
        "/removeadmin id\n"
        "/adminlist\n\n"
        "📊 <b>Stats:</b>\n"
        "/userinfo\n"
        "/live_stock\n\n"
        "📢 <b>Force Join:</b>\n"
        "/force — add a channel\n"
        "/force_remove — remove a channel\n\n"
        "💰 <b>Referral:</b>\n"
        "/referral add\n"
        "/referral deleted\n"
        "/referral balance"
    )
    bot.send_message(msg.chat.id, text, parse_mode="HTML")

# ================= ADMIN: /live_stock =================
@bot.message_handler(commands=["live_stock"])
def live_stock(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return

    if not os.path.exists("numbers") or not os.listdir("numbers"):
        bot.send_message(msg.chat.id, "❌ No service or numbers found.")
        return

    lines = ["📦 <b>Live Stock Report</b>\n"]
    total_all = 0

    for service in sorted(os.listdir("numbers")):
        service_path = f"numbers/{service}"
        if not os.path.isdir(service_path):
            continue

        country_stock = {}
        for fname in os.listdir(service_path):
            if "_" not in fname:
                continue
            country = fname.split("_")[0]
            fpath = f"{service_path}/{fname}"
            try:
                with open(fpath, "r", errors="ignore") as f:
                    count = len([x for x in f.readlines() if x.strip()])
            except:
                count = 0
            country_stock[country] = country_stock.get(country, 0) + count

        if not country_stock:
            continue

        service_total = sum(country_stock.values())
        total_all += service_total
        lines.append(f"\n📡 <b>{service.upper()}</b> — Total: <b>{service_total}</b>")
        lines.append("─────────────────")
        for country in sorted(country_stock):
            flag = COUNTRY_FLAGS.get(country, "🌍")
            stock = country_stock[country]
            if stock == 0:
                status = "❌"
            elif stock <= 50:
                status = "🔴"
            elif stock <= 150:
                status = "🟡"
            else:
                status = "🟢"
            lines.append(f"{status} {flag} <b>{country}</b>: {stock}")

    lines.append(f"\n━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 <b>Total Stock:</b> {total_all}")
    lines.append("\n🟢 >150  🟡 ≤150  🔴 ≤50  ❌ Empty")

    final_text = "\n".join(lines)

    # Split if too long
    if len(final_text) > 4000:
        chunks = []
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > 4000:
                chunks.append(chunk)
                chunk = line
            else:
                chunk += "\n" + line
        if chunk:
            chunks.append(chunk)
        for c in chunks:
            bot.send_message(msg.chat.id, c, parse_mode="HTML")
    else:
        bot.send_message(msg.chat.id, final_text, parse_mode="HTML")

# ================= ADMIN: /force (Add Force Join Channel) =================
@bot.message_handler(commands=["force"])
def force_add_start(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id] = {"step": "force_link"}
    bot.send_message(
        msg.chat.id,
        "📢 <b>Add Force Join Channel</b>\n\n"
        "Step 1️⃣: Send the Channel <b>Invite Link</b>:\n"
        "<i>(Example: https://t.me/channelname)</i>",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "force_link")
def force_add_link(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    link = msg.text.strip()
    if not link.startswith("http"):
        bot.send_message(msg.chat.id, "❌ Please enter a valid link (must start with https://).")
        return
    admin_state[msg.from_user.id]["force_link"] = link
    admin_state[msg.from_user.id]["step"] = "force_id"
    bot.send_message(
        msg.chat.id,
        "✅ Link received!\n\n"
        "Step 2️⃣: Send the Channel <b>ID</b>:\n"
        "<i>(Example: -1001234567890)</i>\n\n"
        "💡 Use @userinfobot to get the Channel ID.",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "force_id")
def force_add_id(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        ch_id = int(msg.text.strip())
    except:
        bot.send_message(msg.chat.id, "❌ Please enter a valid Channel ID (numbers only, e.g: -1001234567890).")
        return

    link = admin_state[msg.from_user.id].get("force_link", "")
    admin_state[msg.from_user.id]["step"] = "force_name"
    admin_state[msg.from_user.id]["force_id"] = ch_id
    bot.send_message(
        msg.chat.id,
        "✅ ID received!\n\n"
        "Step 3️⃣: Enter the Channel <b>Name</b>:\n"
        "<i>(Example: Premium Bazar)</i>",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "force_name")
def force_add_name(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    name = msg.text.strip()
    ch_id = admin_state[msg.from_user.id].get("force_id")
    link = admin_state[msg.from_user.id].get("force_link")

    channels = load_json("force_channels.json", [])
    # Check duplicate
    for ch in channels:
        if ch.get("id") == ch_id:
            bot.send_message(msg.chat.id, "⚠️ This Channel ID has already been added!")
            admin_state.pop(msg.from_user.id, None)
            return

    channels.append({"id": ch_id, "link": link, "name": name})
    save_json("force_channels.json", channels)
    admin_state.pop(msg.from_user.id, None)

    bot.send_message(
        msg.chat.id,
        f"✅ <b>Force Join Channel added!</b>\n\n"
        f"📢 <b>Name:</b> {name}\n"
        f"🔗 <b>Link:</b> {link}\n"
        f"🆔 <b>ID:</b> <code>{ch_id}</code>\n\n"
        f"From now on, new users must join this channel to use the bot.",
        parse_mode="HTML"
    )

# ================= ADMIN: /force_remove (Remove Force Join Channel) =================
@bot.message_handler(commands=["force_remove"])
def force_remove(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    channels = load_json("force_channels.json", [])
    if not channels:
        bot.send_message(msg.chat.id, "❌ No Force Join channels added.")
        return

    kb = types.InlineKeyboardMarkup()
    for i, ch in enumerate(channels):
        name = ch.get("name", "Channel")
        kb.add(types.InlineKeyboardButton(f"🗑 {name}", callback_data=f"frc_del|{i}"))

    bot.send_message(
        msg.chat.id,
        "📢 <b>Force Join Channels</b>\n\n"
        "Click the channel you want to remove:",
        parse_mode="HTML",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("frc_del|"))
def frc_del_confirm(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    idx = int(call.data.split("|")[1])
    channels = load_json("force_channels.json", [])
    if idx >= len(channels):
        bot.answer_callback_query(call.id, "❌ Channel not found")
        return
    ch = channels[idx]
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🗑 Yes, Delete", callback_data=f"frc_del_ok|{idx}"),
        types.InlineKeyboardButton("❌ No", callback_data="frc_del_cancel")
    )
    try:
        bot.edit_message_text(
            f"⚠️ <b>Confirm</b>\n\n"
            f"Remove <b>{ch.get('name', 'Channel')}</b> from force join?\n"
            f"🔗 {ch.get('link', '')}\n"
            f"🆔 <code>{ch.get('id', '')}</code>",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=kb
        )
    except:
        bot.send_message(call.message.chat.id,
            f"⚠️ Remove <b>{ch.get('name', 'Channel')}</b>?",
            parse_mode="HTML", reply_markup=kb
        )

@bot.callback_query_handler(func=lambda c: c.data.startswith("frc_del_ok|"))
def frc_del_do(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    idx = int(call.data.split("|")[1])
    channels = load_json("force_channels.json", [])
    if idx < len(channels):
        removed = channels.pop(idx)
        save_json("force_channels.json", channels)
        bot.answer_callback_query(call.id, f"✅ {removed.get('name', 'Channel')} has been removed!")
        try:
            bot.edit_message_text(
                f"✅ <b>{removed.get('name', 'Channel')}</b> has been removed from force join.\n"
                f"🆔 ID: <code>{removed.get('id', '')}</code>",
                call.message.chat.id, call.message.message_id,
                parse_mode="HTML"
            )
        except:
            bot.send_message(call.message.chat.id,
                f"✅ <b>{removed.get('name', 'Channel')}</b> has been removed.",
                parse_mode="HTML"
            )
    else:
        bot.answer_callback_query(call.id, "❌ Channel not found")

@bot.callback_query_handler(func=lambda c: c.data == "frc_del_cancel")
def frc_del_cancel(call):
    bot.answer_callback_query(call.id, "❌ Cancelled")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

# ================= ADMIN: /userinfo =================
@bot.message_handler(commands=["userinfo"])
def userinfo(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return

    total_users = len(all_users)
    now = int(time.time())
    active_threshold = 86400  # 24 hours
    active = 0
    inactive = 0
    for uid in all_users:
        last = user_last_active.get(str(uid), 0)
        if now - last <= active_threshold:
            active += 1
        else:
            inactive += 1

    total_refs = sum(len(v) for v in user_referrals.values())
    total_numbers = sum(user_numbers_count.values())
    pending_withdrawals = sum(1 for r in withdraw_requests.values() if r.get("status") == "pending")
    total_balance_issued = sum(float(v) for v in user_balance.values())

    text = (
        "╔══════════════════════════╗\n"
        "        📊 Bot Statistics\n"
        "╚══════════════════════════╝\n\n"
        f"👥 <b>Total Users:</b> {total_users}\n"
        f"✅ <b>Active (24h):</b> {active}\n"
        f"😴 <b>Inactive:</b> {inactive}\n\n"
        f"📲 <b>Total Numbers Used:</b> {total_numbers}\n"
        f"🔗 <b>Total Referrals:</b> {total_refs}\n"
        f"💵 <b>Total Balance Issued:</b> ${total_balance_issued:.2f}\n"
        f"💸 <b>Pending Withdrawals:</b> {pending_withdrawals}\n"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 All Users List", callback_data="admin_all_users|0"))
    kb.add(types.InlineKeyboardButton("🔍 Search Specific User", callback_data="admin_search_user"))
    kb.add(types.InlineKeyboardButton("🏆 Top Referrers", callback_data="admin_top_refs"))
    kb.add(types.InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals"))
    bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=kb)

# --- All users paginated list ---
@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_all_users|"))
def admin_all_users(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    page = int(call.data.split("|")[1])
    per_page = 10
    now = int(time.time())
    active_threshold = 86400

    all_uid_list = sorted(list(all_users))
    total = len(all_uid_list)
    start = page * per_page
    end = start + per_page
    chunk = all_uid_list[start:end]

    if not chunk:
        bot.answer_callback_query(call.id, "No users found")
        return

    lines = [f"📋 <b>User List</b> (Page {page+1})\n"]
    for uid in chunk:
        uid_str = str(uid)
        refs = len(user_referrals.get(uid_str, []))
        nums = user_numbers_count.get(uid_str, 0)
        bal = float(user_balance.get(uid_str, 0.0))
        last = user_last_active.get(uid_str, 0)
        active_mark = "🟢" if (now - last) <= active_threshold else "🔴"
        lines.append(
            f"{active_mark} <code>{uid}</code> | 🔗{refs} | 📱{nums} | 💰${bal:.2f}"
        )

    text = "\n".join(lines)
    text += f"\n\n<i>Showing {start+1}-{min(end,total)} of {total}</i>"

    kb = types.InlineKeyboardMarkup()
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("⬅ Prev", callback_data=f"admin_all_users|{page-1}"))
    if end < total:
        nav.append(types.InlineKeyboardButton("Next ➡", callback_data=f"admin_all_users|{page+1}"))
    if nav:
        kb.add(*nav)
    kb.add(types.InlineKeyboardButton("🔍 View User Details", callback_data="admin_search_user"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML", reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=kb)

# --- Top referrers ---
@bot.callback_query_handler(func=lambda c: c.data == "admin_top_refs")
def admin_top_refs(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    sorted_refs = sorted(user_referrals.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    if not sorted_refs:
        bot.answer_callback_query(call.id, "No referrals found")
        return
    lines = ["🏆 <b>Top Referrers</b>\n"]
    for i, (uid_str, refs) in enumerate(sorted_refs, 1):
        bal = float(user_balance.get(uid_str, 0.0))
        lines.append(f"{i}. <code>{uid_str}</code> → {len(refs)} referral | 💰${bal:.2f}")
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("\n".join(lines), call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except:
        bot.send_message(call.message.chat.id, "\n".join(lines), parse_mode="HTML")

# --- Search specific user ---
@bot.callback_query_handler(func=lambda c: c.data == "admin_search_user")
def admin_search_user(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    admin_state[call.from_user.id] = {"step": "search_user"}
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "🔍 Enter User's Telegram ID:")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "search_user")
def show_user_detail(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        target_uid = int(msg.text.strip())
        uid_str = str(target_uid)
        balance = float(user_balance.get(uid_str, 0.0))
        ref_list = user_referrals.get(uid_str, [])
        ref_count = len(ref_list)
        numbers_used = user_numbers_count.get(uid_str, 0)
        join_t = user_join_time.get(uid_str, 0)
        last_t = user_last_active.get(uid_str, 0)
        join_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(join_t)) if join_t else "Unknown"
        last_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(last_t)) if last_t else "Unknown"
        referred_by_id = referred_by.get(uid_str, "None")
        now = int(time.time())
        is_active = "🟢 Active" if (now - last_t) <= 86400 else "🔴 Inactive"

        # Number log (last 10)
        num_log = user_numbers_log.get(uid_str, [])
        num_log_text = ""
        if num_log:
            last_nums = num_log[-10:]
            num_log_text = "\n📞 <b>Last Used Numbers:</b>\n"
            for n in last_nums:
                num_log_text += f"  • <code>{n}</code>\n"

        # Referral list (show IDs)
        ref_ids_text = ""
        if ref_list:
            ref_ids_text = "\n👥 <b>Referred Users:</b>\n"
            for r in ref_list[-10:]:
                ref_ids_text += f"  • <code>{r}</code>\n"
            if len(ref_list) > 10:
                ref_ids_text += f"  <i>...and {len(ref_list)-10} more</i>\n"

        text = (
            f"╔══════════════════════╗\n"
            f"     👤 User Details\n"
            f"╚══════════════════════╝\n\n"
            f"🆔 <b>User ID:</b> <code>{target_uid}</code>\n"
            f"📶 <b>Status:</b> {is_active}\n"
            f"💰 <b>Balance:</b> ${balance:.2f}\n"
            f"🔗 <b>Referrals Made:</b> {ref_count}\n"
            f"📱 <b>Numbers Used:</b> {numbers_used}\n"
            f"👆 <b>Referred By:</b> <code>{referred_by_id}</code>\n"
            f"📅 <b>Join Date:</b> {join_str}\n"
            f"🕒 <b>Last Active:</b> {last_str}"
            f"{ref_ids_text}"
            f"{num_log_text}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🔍 Search Another", callback_data="admin_search_user"))
        bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Invalid ID or Error: {e}")
    admin_state.pop(msg.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data == "admin_withdrawals")
def admin_withdrawals(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    pending = [(k, v) for k, v in withdraw_requests.items() if v.get("status") == "pending"]
    if not pending:
        bot.answer_callback_query(call.id, "✅ No pending requests")
        return
    bot.answer_callback_query(call.id)
    for req_id, req in pending:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"wapprove|{req_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"wreject|{req_id}")
        )
        bot.send_message(
            call.message.chat.id,
            f"💸 <b>Withdraw Request</b>\n\n"
            f"👤 <b>User:</b> <code>{req['user_id']}</code>\n"
            f"💳 <b>Binance:</b> <code>{req['binance_id']}</code>\n"
            f"💰 <b>Amount:</b> ${req['amount']:.2f}",
            parse_mode="HTML",
            reply_markup=kb
        )

# ================= ADMIN: /referral =================
@bot.message_handler(commands=["referral"])
def referral_cmd(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    parts = msg.text.strip().split()
    sub = parts[1].lower() if len(parts) > 1 else ""

    if sub == "add":
        admin_state[msg.from_user.id] = {"step": "ref_add_channel"}
        bot.send_message(msg.chat.id,
            "📢 <b>Add Referral Channel</b>\n\n"
            "Send the channel name and link in this format:\n"
            "<code>Channel Name | https://t.me/channelname | -100123456789</code>",
            parse_mode="HTML"
        )

    elif sub == "deleted":
        channels = load_json("ref_channels.json", [])
        if not channels:
            bot.send_message(msg.chat.id, "❌ No referral channels added.")
            return
        kb = types.InlineKeyboardMarkup()
        for i, ch in enumerate(channels):
            kb.add(types.InlineKeyboardButton(f"📢 {ch['name']}", callback_data=f"ref_del_ch|{i}"))
        bot.send_message(msg.chat.id, "🗑 <b>Select a channel to delete:</b>", parse_mode="HTML", reply_markup=kb)

    elif sub == "balance":
        current = load_json("ref_settings.json", {"amount": 0.02})
        admin_state[msg.from_user.id] = {"step": "ref_set_amount"}
        bot.send_message(
            msg.chat.id,
            f"💰 <b>Set Referral Balance</b>\n\n"
            f"Current amount: <b>${float(current['amount']):.2f}</b> per referral\n\n"
            f"Send the new amount (e.g: <code>0.50</code>):",
            parse_mode="HTML"
        )
    else:
        bot.send_message(msg.chat.id,
            "ℹ️ <b>Referral Commands:</b>\n\n"
            "/referral add — add a channel\n"
            "/referral deleted — delete a channel\n"
            "/referral balance — set per referral amount",
            parse_mode="HTML"
        )

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ref_add_channel")
def ref_add_channel(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = [p.strip() for p in msg.text.split("|")]
        if len(parts) < 3:
            bot.send_message(msg.chat.id, "❌ Invalid format. Example:\n<code>Channel Name | https://t.me/ch | -100123456789</code>", parse_mode="HTML")
            return
        name, link, ch_id = parts[0], parts[1], int(parts[2])
        channels = load_json("ref_channels.json", [])
        channels.append({"name": name, "link": link, "id": ch_id})
        save_json("ref_channels.json", channels)
        bot.send_message(msg.chat.id, f"✅ <b>{name}</b> has been added as a referral channel!", parse_mode="HTML")
    except:
        bot.send_message(msg.chat.id, "❌ Error! Please check the format.")
    admin_state.pop(msg.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref_del_ch|"))
def ref_del_confirm(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    idx = int(call.data.split("|")[1])
    channels = load_json("ref_channels.json", [])
    if idx >= len(channels):
        bot.answer_callback_query(call.id, "❌ Channel not found")
        return
    ch = channels[idx]
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🗑 Delete", callback_data=f"ref_del_confirm|{idx}"),
        types.InlineKeyboardButton("❌ No", callback_data="ref_del_cancel")
    )
    try:
        bot.edit_message_text(
            f"⚠️ <b>Confirm</b>\n\nAre you sure you want to delete <b>{ch['name']}</b>?",
            call.message.chat.id, call.message.message_id,
            parse_mode="HTML", reply_markup=kb
        )
    except:
        bot.send_message(call.message.chat.id, f"⚠️ Delete <b>{ch['name']}</b>?", parse_mode="HTML", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ref_del_confirm|"))
def ref_del_do(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    idx = int(call.data.split("|")[1])
    channels = load_json("ref_channels.json", [])
    if idx < len(channels):
        removed = channels.pop(idx)
        save_json("ref_channels.json", channels)
        bot.answer_callback_query(call.id, f"✅ {removed['name']} deleted!")
        try:
            bot.edit_message_text(f"✅ <b>{removed['name']}</b> has been deleted.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except:
            bot.send_message(call.message.chat.id, f"✅ <b>{removed['name']}</b> has been deleted.", parse_mode="HTML")
    else:
        bot.answer_callback_query(call.id, "❌ Not found")

@bot.callback_query_handler(func=lambda c: c.data == "ref_del_cancel")
def ref_del_cancel(call):
    bot.answer_callback_query(call.id, "❌ Cancelled")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "ref_set_amount")
def ref_set_amount(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        amount = float(msg.text.strip())
        if amount < 0:
            raise ValueError
        ref_settings["amount"] = amount
        save_json("ref_settings.json", ref_settings)
        bot.send_message(msg.chat.id, f"✅ Per referral amount set to <b>${amount:.2f}</b>!", parse_mode="HTML")
    except:
        bot.send_message(msg.chat.id, "❌ Invalid amount! Example: <code>0.50</code>", parse_mode="HTML")
    admin_state.pop(msg.from_user.id, None)

# ================= ADMIN: OTHER COMMANDS =================
@bot.message_handler(commands=["adminlist"])
def admin_list(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(msg.chat.id, "👑 Admins:\n" + "\n".join(map(str, ADMIN_IDS)))

@bot.message_handler(commands=["addadmin"])
def add_admin(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(msg.text.split()[1])
        if uid not in ADMIN_IDS:
            ADMIN_IDS.append(uid)
        bot.reply_to(msg, "✅ Admin Added")
    except:
        bot.reply_to(msg, "Usage: /addadmin 123456")

@bot.message_handler(commands=["removeadmin"])
def remove_admin(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        uid = int(msg.text.split()[1])
        if uid in ADMIN_IDS:
            ADMIN_IDS.remove(uid)
        bot.reply_to(msg, "✅ Admin Removed")
    except:
        bot.reply_to(msg, "Usage: /removeadmin 123456")

@bot.message_handler(commands=["addservice"])
def add_service(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        name = msg.text.split()[1].lower()
        os.makedirs(f"numbers/{name}", exist_ok=True)
        bot.reply_to(msg, f"✅ Service {name} added")
    except:
        bot.reply_to(msg, "Usage: /addservice whatsapp")

@bot.message_handler(commands=["removeservice"])
def remove_service(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        name = msg.text.split()[1].lower()
        path = f"numbers/{name}"
        if os.path.exists(path):
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
            os.rmdir(path)
            bot.reply_to(msg, "✅ Removed")
        else:
            bot.reply_to(msg, "❌ Not found")
    except:
        bot.reply_to(msg, "Usage: /removeservice whatsapp")

@bot.message_handler(commands=["addnumber"])
def add_number(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    admin_state[msg.from_user.id] = "service"
    bot.send_message(msg.chat.id, "Send service name")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "service")
def set_service(msg):
    admin_state[msg.from_user.id] = {"service": msg.text, "step": "country"}
    bot.send_message(msg.chat.id, "Send country name")

@bot.message_handler(func=lambda m: isinstance(admin_state.get(m.from_user.id), dict) and admin_state[m.from_user.id].get("step") == "country")
def set_country(msg):
    admin_state[msg.from_user.id]["country"] = msg.text
    admin_state[msg.from_user.id]["step"] = "file"
    bot.send_message(msg.chat.id, "Upload .txt file")

# ================= ADMIN FILE UPLOAD =================
@bot.message_handler(content_types=["document"])
def upload_file(msg):
    if msg.from_user.id not in ADMIN_IDS:
        bot.reply_to(msg, "❌ Only admins can upload numbers.")
        return
    state = admin_state.get(msg.from_user.id)
    if not isinstance(state, dict) or state.get("step") != "file":
        return
    service = state["service"]
    country = state["country"]
    file_info = bot.get_file(msg.document.file_id)
    data = bot.download_file(file_info.file_path)
    os.makedirs(f"numbers/{service}", exist_ok=True)
    filename = f"{country}_{int(time.time())}.txt"
    with open(f"numbers/{service}/{filename}", "wb") as f:
        f.write(data)
    lines = [x.strip() for x in data.decode(errors="ignore").splitlines() if x.strip()]
    total = len(lines)
    admin_text = (
        f"✅ Upload Complete\n"
        f"Service : {service}\n"
        f"Country : {COUNTRY_FLAGS.get(country, '')} {country}\n"
        f"Total Lines : {total}\n"
        f"Added : {total}\n"
        f"Duplicate : 0\n"
        f"Invalid : 0"
    )
    bot.send_message(msg.from_user.id, admin_text)
    user_text = (
        f"✨ <b>NEW STOCK AVAILABLE</b>\n\n"
        f"📡 <b>Service:</b> {service}\n"
        f"🌍 <b>Country:</b> {COUNTRY_FLAGS.get(country,'🌍')} {country}\n"
        f"📦 <b>Stock:</b> {total}\n\n"
        f"⚡ <i>Fresh numbers added. Try now!</i>"
    )
    for u in all_users:
        try:
            bot.send_message(u, user_text, parse_mode="HTML")
        except:
            pass
    admin_state.pop(msg.from_user.id)

# ================= REMOVE NUMBER UI =================
@bot.message_handler(commands=["removenumber"])
def remove_number_ui(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    countries = set()
    for service in os.listdir("numbers"):
        path = f"numbers/{service}"
        if os.path.exists(path):
            for f in os.listdir(path):
                if "_" in f:
                    countries.add(f.split("_")[0])
    if not countries:
        bot.send_message(msg.chat.id, "❌ No country found")
        return
    kb = types.InlineKeyboardMarkup()
    for c in sorted(countries):
        kb.add(types.InlineKeyboardButton(f"🌍 {c}", callback_data=f"del_cty|{c}"))
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_admin"))
    bot.send_message(msg.chat.id, "🗑 Select Country", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_cty|"))
def show_files(call):
    country = call.data.split("|")[1]
    kb = types.InlineKeyboardMarkup()
    found = False
    for service in os.listdir("numbers"):
        path = f"numbers/{service}"
        if os.path.exists(path):
            for f in os.listdir(path):
                if f.startswith(country):
                    found = True
                    kb.add(types.InlineKeyboardButton(f"📂 {service} | {f}", callback_data=f"del_file|{service}|{f}"))
    if not found:
        bot.answer_callback_query(call.id, "❌ No files found")
        return
    kb.add(types.InlineKeyboardButton("⬅ Back", callback_data="back_cty_list"))
    try:
        bot.edit_message_text(f"📁 Files of {country}", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, f"📁 Files of {country}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_file|"))
def confirm_delete(call):
    _, service, filename = call.data.split("|")
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Delete", callback_data=f"confirm_del|{service}|{filename}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data="back_cty_list")
    )
    try:
        bot.edit_message_text(f"⚠️ Are you sure?\n\n📄 {filename}", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        bot.send_message(call.message.chat.id, f"⚠️ Are you sure?\n\n📄 {filename}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_del|"))
def delete_file(call):
    _, service, filename = call.data.split("|")
    path = f"numbers/{service}/{filename}"
    if os.path.exists(path):
        os.remove(path)
        bot.answer_callback_query(call.id, "✅ File Deleted")
    else:
        bot.answer_callback_query(call.id, "❌ File Not Found")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "back_cty_list")
def back_to_country_list(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "back_admin")
def back_admin(call):
    try:
        bot.edit_message_text(
            "⚙️ Admin Panel\n\nUse commands like:\n/addnumber\n/removenumber",
            call.message.chat.id, call.message.message_id
        )
    except:
        pass

# ================= TELETHON OTP LISTENER =================
client = TelegramClient("ayan_final_session", API_ID, API_HASH)

def delete_message_later(chat_id, msg_id, delay=30):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

@client.on(events.NewMessage(chats=OTP_GROUP_ID))
async def otp_listener(event):
    global sent_otps
    text = event.raw_text
    if not text:
        return

    prothom_4 = None
    shesh_4 = None

    # Format 1: 8490SHU5853 (digits + uppercase letters + digits)
    # Example: #VN 🇻🇳 ⚙️ 8490SHU5853
    match_format1 = re.search(r"(\d{3,4})[A-Za-z]{2,6}(\d{4})", text)

    # Format 2: 998•••••4959 or 6019•••1989 (digits + dots/bullets + digits)
    # Example: WA | 🇺🇿 998•••••4959 #English
    # Example: 🇲🇾 #MY 📞 6019•••1989
    match_format2 = re.search(r"(\d{3,4})[•\*\.\s]{2,10}(\d{4})", text)

    # Existing format: generic digit matching
    match_existing = re.search(r"(\d{3,4})[•\*]+(\d{4})", text)

    if match_format1:
        prothom_4 = match_format1.group(1)
        shesh_4 = match_format1.group(2)
    elif match_format2:
        prothom_4 = match_format2.group(1)
        shesh_4 = match_format2.group(2)
    elif match_existing:
        prothom_4 = match_existing.group(1)
        shesh_4 = match_existing.group(2)
    else:
        clean_digits = re.sub(r"\D", "", text)
        if len(clean_digits) >= 8:
            prothom_4 = clean_digits[:4]
            shesh_4 = clean_digits[-4:]
        else:
            return

    final_otp = None

    # Priority: "OTP baton" or "Otp baton" keyword (case-insensitive)
    # Supports:
    #   OTP baton 686588       (plain digits)
    #   Otp baton 6886         (4-digit)
    #   OTP baton 578-686      (hyphen format)
    otp_baton_match = re.search(
        r"[Oo][Tt][Pp]\s+[Bb]aton\s+(\d{3,4}-\d{3,4}|\d{4,8})",
        text
    )
    if otp_baton_match:
        final_otp = otp_baton_match.group(1)

    # Fallback: existing OTP patterns
    if not final_otp:
        otp_patterns = [
            r"\b\d{5,8}\b",
            r"\b\d{3}[-\s]\d{3}\b"
        ]
        for pattern in otp_patterns:
            match = re.search(pattern, text)
            if match:
                code = match.group()
                clean_code = code.replace("-", "").replace(" ", "")
                if clean_code in [prothom_4, shesh_4]:
                    continue
                final_otp = code
                break

    if not final_otp:
        return

    unique_id = f"{final_otp}_{shesh_4}"
    if unique_id in sent_otps:
        return

    for db_number, user_id in list(number_to_user.items()):
        if db_number.startswith(prothom_4) and db_number.endswith(shesh_4):
            sent_otps.add(unique_id)
            country = user_country.get(user_id, "Unknown")
            platform = user_platform.get(user_id, "Service")
            flag = COUNTRY_FLAGS.get(country, "🌍")
            masked_number = f"+{prothom_4}***{shesh_4}"
            msg_text = (
                f"{flag} <b>{country} {platform} OTP Received.</b>\n\n"
                f"📱 <b>Number:</b> <code>{masked_number}</code>\n\n"
                f"🔑 <b>Main OTP:</b> <code>{final_otp}</code>\n\n"
                f"⏳ <i>This message will be deleted after 30 seconds.</i>"
            )
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("💬 OTP Group Check", url=OTP_GROUP_LINK))
            try:
                sent_msg = bot.send_message(user_id, msg_text, parse_mode="HTML", reply_markup=kb)
                print(f"[✅] OTP Sent for {platform} to User: {user_id}")
                # Auto-delete after 30 seconds
                threading.Thread(
                    target=delete_message_later,
                    args=(user_id, sent_msg.message_id, 30),
                    daemon=True
                ).start()
                return
            except Exception as e:
                logging.error(f"Error: {e}")
                break

async def run_userbot():
    await client.start()
    print("USERBOT RUNNING AND LISTENING FOR OTPS...")
    await client.run_until_disconnected()

# ================= RUN BOTH =================
def run_telebot():
    print("NUMBER BOT RUNNING...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    print("Starting bot...")
    threading.Thread(target=run_telebot, daemon=True).start()
    try:
        asyncio.run(run_userbot())
    except KeyboardInterrupt:
        print("Bot Stopped.")
    except EOFError:
        print("[ERROR] Telethon session not found. Please run locally to authenticate first.")
    except Exception as e:
        print(f"[ERROR] {e}")
