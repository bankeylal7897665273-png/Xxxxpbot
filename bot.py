import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
import os
from flask import Flask
import threading

# --- FIREBASE DIRECT API SETUP ---
# Bina JSON file ke direct link connect hoga
BASE_URL = "https://earning-a9b0c-default-rtdb.firebaseio.com/phonepe_botz"

# --- BOT SETUP ---
BOT_TOKEN = "8701965138:AAEQ84qHLUVr8Bk0JrQKeQEPOJjfsutD7cs"
bot = telebot.TeleBot(BOT_TOKEN)

CHANNELS = ["@earninglootsbestd", "@earnbox1"]
GIVEAWAY_IMG = "https://i.ibb.co/7KzXb4p/giveaway-image.jpg" # Apna giveaway image URL
YT_VIDEO_LINK = "https://youtube.com/shorts/YOUR_VIDEO" # How to redeem video

def check_joined(user_id):
    try:
        for ch in CHANNELS:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except:
        return False

def get_user(uid):
    res = requests.get(f"{BASE_URL}/users/{uid}.json")
    return res.json() if res.status_code == 200 else None

def update_user(uid, data):
    requests.patch(f"{BASE_URL}/users/{uid}.json", json=data)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.from_user.id)
    args = message.text.split()
    
    user_data = get_user(user_id)
    if not user_data:
        referrer = args[1] if len(args) > 1 else ""
        new_user = {"balance": 0.0, "verified": False, "active_key": "", "referrer": referrer}
        requests.put(f"{BASE_URL}/users/{user_id}.json", json=new_user)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("JOIN CHANNEL 1", url=f"https://t.me/{CHANNELS[0][1:]}"))
    markup.add(InlineKeyboardButton("JOIN CHANNEL 2", url=f"https://t.me/{CHANNELS[1][1:]}"))
    markup.add(InlineKeyboardButton("✅ VERIFY", callback_data="verify_channels"))

    bot.send_photo(message.chat.id, GIVEAWAY_IMG, caption="<b>HI USER JOIN CHANNEL AND EARN PHONEPE GIFT CARDS</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_callback(call):
    user_id = str(call.from_user.id)
    
    if check_joined(user_id):
        user_data = get_user(user_id) or {}
        
        if not user_data.get('verified', False):
            update_user(user_id, {"verified": True})
            referrer_id = user_data.get('referrer', "")
            if referrer_id:
                ref_data = get_user(referrer_id)
                if ref_data:
                    ref_bal = ref_data.get('balance', 0.0)
                    update_user(referrer_id, {"balance": ref_bal + 0.5})

        if not user_data.get('active_key', ""):
            gen_data = requests.get(f"{BASE_URL}/settings.json").json() or {}
            gen_url = gen_data.get('gen_url', "Link Not Set by Admin")
            bot.send_message(call.message.chat.id, f"✅ Channels Verified!\n\n⚠️ Now please enter your <b>Bot Active Key</b> to continue.\n\n🌐 Active Generator Website:\n{gen_url}", parse_mode="HTML")
            bot.register_next_step_handler(call.message, process_active_key)
        else:
            show_main_menu(call.message.chat.id)
    else:
        bot.answer_callback_query(call.id, "Bhai pehle dono channels join karo!", show_alert=True)
        start_cmd(call.message)

def process_active_key(message):
    user_id = str(message.from_user.id)
    key_entered = message.text.strip()
    
    key_res = requests.get(f"{BASE_URL}/keys/{key_entered}.json").json()
    
    if key_res and not key_res.get('used', True):
        requests.patch(f"{BASE_URL}/keys/{key_entered}.json", json={"used": True})
        update_user(user_id, {"active_key": key_entered})
        bot.send_message(message.chat.id, "✅ Key Verified Successfully!")
        show_main_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Invalid or Used Key. Please generate a new one.")
        bot.register_next_step_handler(message, process_active_key)

def show_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("💰 Balance"), KeyboardButton("🔗 Refer & Withdrawal"))
    bot.send_message(chat_id, "Welcome to Main Menu! Choose an option:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["💰 Balance", "🔗 Refer & Withdrawal"])
def handle_menu(message):
    user_id = str(message.from_user.id)
    user_data = get_user(user_id) or {}
    
    if not user_data.get('active_key', ""):
        bot.send_message(message.chat.id, "Please /start and verify your key first.")
        return

    bal = user_data.get('balance', 0.0)

    if message.text == "💰 Balance":
        bot.send_message(message.chat.id, f"💳 Your Real Balance: <b>₹{bal}</b>", parse_mode="HTML")
    
    elif message.text == "🔗 Refer & Withdrawal":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        msg = (f"🔗 <b>Your Referral Link:</b>\n{ref_link}\n\n"
               f"👥 Invite 2 friends to earn ₹1.0 (₹0.5 per valid refer).\n"
               f"💳 Current Balance: ₹{bal}\n"
               f"💵 Max & Min Withdrawal limit is exactly ₹1.0")
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"Withdraw ₹1", callback_data="withdraw_1"))
        bot.send_message(message.chat.id, msg, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_1")
def handle_withdrawal(call):
    user_id = str(call.from_user.id)
    user_data = get_user(user_id) or {}
    bal = user_data.get('balance', 0.0)
    
    if bal >= 1.0:
        cards_res = requests.get(f"{BASE_URL}/gift_cards.json").json() or {}
        card_found = False
        
        for card_key, card_data in cards_res.items():
            if not card_data.get('used', True):
                # Mark card used & cut balance
                requests.patch(f"{BASE_URL}/gift_cards/{card_key}.json", json={'used': True})
                update_user(user_id, {'balance': bal - 1.0})
                
                success_msg = (
                    "🎉 <b>Withdrawal Successful!</b>\n\n"
                    "👇 Click below to copy your details:\n"
                    f"<b>ID:</b> <code>{card_data['id']}</code>\n"
                    f"<b>PIN:</b> <code>{card_data['pin']}</code>\n\n"
                    f"📺 <a href='{YT_VIDEO_LINK}'>How to Redeem Video</a>"
                )
                bot.send_message(call.message.chat.id, success_msg, parse_mode="HTML")
                bot.answer_callback_query(call.id, "Redeem Successful!")
                card_found = True
                break
                
        if not card_found:
            bot.answer_callback_query(call.id, "Please wait 24 hours for your redeem successful", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "Insufficient balance! Minimum exactly ₹1 needed.", show_alert=True)

# --- RENDER WEB SERVICE DUMMY SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "VIP Bot is Running Perfectly on Render (No JSON File Needed)!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.start()
    print("🤖 VIP Bot is live!")
    bot.infinity_polling()
