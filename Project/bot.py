import os
import re
import zipfile
import tempfile
import time
import threading
import requests
import http.server
import socketserver
import telebot

# Render च्या Environment Variable मधून टोकन घेतले जाईल
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# ----------------- अ‍ॅडमिन सेटिंग्ज -----------------
# इथे तुमचा Telegram User ID टाका (फक्त तुम्हीच हा बॉट वापरू शकाल)
ADMIN_IDS = [123456789]  # <--- तुमचा खरा टेलिग्राम आयडी इथे टाका
# --------------------------------------------------

# तुम्ही सांगितलेला PingHandler (Render वर सर्व्हर चालू ठेवण्यासाठी)
class PingHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self): 
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Server Active")
    
    # अनावश्यक सर्व्हर लॉग्ज लपवण्यासाठी (पर्यायी)
    def log_message(self, format, *args):
        return

# तुम्ही सांगितलेला always-on पिंगर
def run_always_on_pinger():
    time.sleep(20)
    while True:
        try:
            requests.get("https://checker-9kyv.onrender.com", timeout=12)
            print("[*] 24x7 Active-Pulse Sent Successfully. Server Kept Awake.")
        except: 
            pass
        time.sleep(540)

# HTTP Server चालवण्यासाठी फंक्शन
def run_http_server():
    PORT = int(os.environ.get("PORT", 5000))
    with socketserver.TCPServer(("", PORT), PingHandler) as httpd:
        print(f"HTTP Server serving at port {PORT}")
        httpd.serve_forever()

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

    # २. तुमचे नेहमी चालू राहणारे पिंग फंक्शन बॅकग्राउंडमध्ये चालू करा
    t_pinger = threading.Thread(target=run_always_on_pinger)
    t_pinger.start()

    # ३. मुख्य HTTP Server चालू करा (Render port requirement पूर्ण करण्यासाठी)
    run_http_server()
    
