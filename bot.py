import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import firebase_admin
from firebase_admin import credentials, db

# --- FIREBASE SETUP ---
# Apni downloaded JSON file ka naam yahan daalein
cred = credentials.Certificate("firebase-adminsdk.json")
# Apne firebase database ka URL yahan daalein
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://YOUR-FIREBASE-PROJECT.firebaseio.com/'
})
root_db = db.reference('phonepe_botz')

# --- BOT SETUP ---
BOT_TOKEN = "8701965138:AAEQ84qHLUVr8Bk0JrQKeQEPOJjfsutD7cs"
bot = telebot.TeleBot(BOT_TOKEN)

CHANNELS = ["@earninglootsbestd", "@earnbox1"]
GIVEAWAY_IMG = "https://i.ibb.co/7KzXb4p/giveaway-image.jpg" # Apna giveaway image URL lagao
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

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = str(message.from_user.id)
    args = message.text.split()
    
    # Save referrer if exists
    user_ref = root_db.child('users').child(user_id)
    if not user_ref.get():
        referrer = args[1] if len(args) > 1 else ""
        user_ref.set({"balance": 0.0, "verified": False, "active_key": "", "referrer": referrer})

    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("JOIN CHANNEL 1", url=f"https://t.me/{CHANNELS[0][1:]}")
    btn2 = InlineKeyboardButton("JOIN CHANNEL 2", url=f"https://t.me/{CHANNELS[1][1:]}")
    btn3 = InlineKeyboardButton("✅ VERIFY", callback_data="verify_channels")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)

    bot.send_photo(message.chat.id, GIVEAWAY_IMG, caption="<b>HI USER JOIN CHANNEL AND EARN PHONEPE GIFT CARDS</b>", parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_callback(call):
    user_id = str(call.from_user.id)
    
    if check_joined(user_id):
        user_data = root_db.child('users').child(user_id).get()
        
        # Referrer logic (0.5 rs per verify)
        if not user_data.get('verified', False):
            root_db.child('users').child(user_id).update({"verified": True})
            referrer_id = user_data.get('referrer', "")
            if referrer_id:
                ref_bal = root_db.child('users').child(referrer_id).child('balance').get() or 0.0
                root_db.child('users').child(referrer_id).update({"balance": ref_bal + 0.5})

        if not user_data.get('active_key', ""):
            gen_url = root_db.child('settings').child('gen_url').get() or "Link Not Set by Admin"
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
    
    key_ref = root_db.child('keys').child(key_entered)
    key_data = key_ref.get()
    
    if key_data and not key_data.get('used', True):
        key_ref.update({"used": True})
        root_db.child('users').child(user_id).update({"active_key": key_entered})
        bot.send_message(message.chat.id, "✅ Key Verified Successfully!")
        show_main_menu(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Invalid or Used Key. Please generate a new one and send it again.")
        bot.register_next_step_handler(message, process_active_key)

def show_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("💰 Balance"), KeyboardButton("🔗 Refer & Withdrawal"))
    bot.send_message(chat_id, "Welcome to Main Menu! Choose an option:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["💰 Balance", "🔗 Refer & Withdrawal"])
def handle_menu(message):
    user_id = str(message.from_user.id)
    user_data = root_db.child('users').child(user_id).get()
    
    if not user_data or not user_data.get('active_key', ""):
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
    user_ref = root_db.child('users').child(user_id)
    bal = user_ref.child('balance').get() or 0.0
    
    if bal >= 1.0:
        cards = root_db.child('gift_cards').order_by_child('used').equal_to(False).limit_to_first(1).get()
        
        if cards:
            card_key = list(cards.keys())[0]
            card_data = cards[card_key]
            
            # Mark card as used & deduct balance
            root_db.child('gift_cards').child(card_key).update({'used': True})
            user_ref.update({'balance': bal - 1.0})
            
            success_msg = (
                "🎉 <b>Withdrawal Successful!</b>\n\n"
                "👇 Click below to copy your details:\n"
                f"<b>ID:</b> <code>{card_data['id']}</code>\n"
                f"<b>PIN:</b> <code>{card_data['pin']}</code>\n\n"
                f"📺 <a href='{YT_VIDEO_LINK}'>How to Redeem Video</a>"
            )
            bot.send_message(call.message.chat.id, success_msg, parse_mode="HTML")
            bot.answer_callback_query(call.id, "Redeem Successful!")
        else:
            bot.answer_callback_query(call.id, "Please wait 24 hours for your redeem successful", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "Insufficient balance! Minimum exactly ₹1 needed.", show_alert=True)

print("Bot is running...")
bot.infinity_polling()
