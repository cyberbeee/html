import os
import re
import zipfile
import tempfile
import time
import threading
import requests
import telebot
from flask import Flask

# Render च्या Environment Variable मधून टोकन घेतले जाईल
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Cookie Cleaner Bot is running 24x7!"

# ----------------- अ‍ॅडमिन सेटिंग्ज -----------------
# इथे तुमचा Telegram User ID टाका (फक्त तुम्हीच हा बॉट वापरू शकाल)
ADMIN_IDS = [1115202962]  # <--- तुमचा खरा टेलिग्राम आयडी इथे टाका
# --------------------------------------------------

# 24x7 चालू ठेवण्यासाठी स्वतःलाच स्वयंचलित रिक्वेस्ट (Ping) पाठवणारे फंक्शन
def self_ping():
    # Render वरून तुमच्या अ‍ॅपचे नाव किंवा URL मिळवली जाईल (किंवा Render चे आतील लोहोस्ट)
    port = int(os.environ.get("PORT", 5000))
    url = f"http://127.0.0.1:{port}/"
    
    while True:
        try:
            time.sleep(300) # दर ५ मिनिटांनी (३०० सेकंद) रिक्वेस्ट जाईल
            requests.get(url)
            print("Self-ping sent to keep the bot alive!")
        except Exception as e:
            print(f"Ping error: {e}")

cookie_pattern = re.compile(
    r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s+'
    r'(TRUE|FALSE)\s+'
    r'([^\s]+)\s+'
    r'(TRUE|FALSE)\s+'
    r'(\d+)\s+'
    r'([^\s]+)\s+'
    r'([^\s]*)'
)

def clean_cookie_content(content):
    matches = cookie_pattern.findall(content)
    if matches:
        formatted_lines = ["\t".join(match) for match in matches]
        return "\n".join(formatted_lines) + "\n"
    return None

@bot.message_handler(commands=['start', 'upload'])
def send_welcome(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⚠️ तुम्हाला हा बॉट वापरण्याची परवानगी नाही. हा फक्त अ‍ॅडमिनसाठी आहे.")
        return
    
    bot.reply_to(message, "नमस्ते अ‍ॅडमिन! कुकी फाईल क्लिन करण्यासाठी कृपया तुमची **.txt** किंवा **.zip** फाईल इथे पाठवा.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⚠️ तुम्हाला कुकीज क्लिन करण्याची परवानगी नाही.")
        return

    try:
        bot.reply_to(message, "तुमची फाईल प्रोसेस होत आहे, कृपया प्रतीक्षा करा...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = message.document.file_name
        file_ext = file_name.split('.')[-1].lower()

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = os.path.join(tmp_dir, file_name)
            with open(input_path, 'wb') as f:
                f.write(downloaded_file)

            if file_ext == 'txt':
                with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                cleaned = clean_cookie_content(content)
                if cleaned:
                    cleaned_path = os.path.join(tmp_dir, f"cleaned_{file_name}")
                    with open(cleaned_path, 'w', encoding='utf-8') as f:
                        f.write(cleaned)
                    
                    with open(cleaned_path, 'rb') as f:
                        bot.send_document(message.chat.id, f, caption="ही घ्या तुमची क्लिन केलेली कुकी फाईल!")
                else:
                    bot.reply_to(message, "एरर: या फाईलमध्ये कोणतीही मॅचिंग कुकी सापडली नाही.")

            elif file_ext == 'zip':
                extracted_dir = os.path.join(tmp_dir, "extracted")
                os.makedirs(extracted_dir, exist_ok=True)
                
                with zipfile.ZipFile(input_path, 'r') as zip_ref:
                    zip_ref.extractall(extracted_dir)

                cleaned_zip_path = os.path.join(tmp_dir, f"cleaned_{file_name}")
                with zipfile.ZipFile(cleaned_zip_path, 'w') as out_zip:
                    for root, dirs, files in os.walk(extracted_dir):
                        for file in files:
                            if file.endswith('.txt'):
                                txt_path = os.path.join(root, file)
                                with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                
                                cleaned = clean_cookie_content(content)
                                if cleaned:
                                    with open(txt_path, 'w', encoding='utf-8') as f:
                                        f.write(cleaned)
                                    out_zip.write(txt_path, arcname=file)

                with open(cleaned_zip_path, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption="ही घ्या तुमच्या क्लिन केलेल्या कुकीजची ZIP फाईल!")

            else:
                bot.reply_to(message, "कृपया फक्त .txt किंवा .zip फाईल पाठवा.")

    except Exception as e:
        bot.reply_to(message, f"काहीतरी त्रुटी आली: {e}")

if __name__ == '__main__':
    # १. टेलिग्राम बॉट बॅकग्राउंडमध्ये चालू करा
    def run_bot():
        time.sleep(2)
        bot.infinity_polling()

    t_bot = threading.Thread(target=run_bot)
    t_bot.start()

    # २. स्वतःलाच पिंग करणारी सिस्टीम बॅकग्राउंडमध्ये चालू करा (24x7 साठी)
    t_ping = threading.Thread(target=self_ping)
    t_ping.start()

    # ३. मुख्य फ्लॅस्क सर्व्हर चालू ठेवा
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
