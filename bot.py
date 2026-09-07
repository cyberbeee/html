import os
import re
import zipfile
import tempfile
import telebot
from flask import Flask

# Render च्या Environment Variable मधून टोकन घेतले जाईल
TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Cookie Cleaner Bot is running!"

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
    bot.reply_to(message, "नमस्ते! कुकी फाईल क्लिन करण्यासाठी कृपया तुमची **.txt** किंवा **.zip** फाईल इथे पाठवा.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
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
    # Render ने दिलेला PORT ऑटोमॅटिक घेण्यासाठी
    import threading
    import time

    def run_bot():
        # थोडा वेळ थांबून बॉट पोलिंग सुरू होईल
        time.sleep(2)
        bot.infinity_polling()

    # बॅकग्राउंडमध्ये टेलिग्राम बॉट चालू करा
    t = threading.Thread(target=run_bot)
    t.start()

    # मुख्य प्रक्रियेत फ्लॅस्क सर्व्हर चालू ठेवा जेणेकरून Render बंद पडणार नाही
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
