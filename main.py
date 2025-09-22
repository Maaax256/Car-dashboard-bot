import time
import telebot
import os
from dotenv import load_dotenv
import re
import google.generativeai as genai

load_dotenv()

TG_BOT_API_TOKEN = os.getenv("TG_BOT_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
bot = telebot.TeleBot(TG_BOT_API_TOKEN)

help_text = (
        "Here are the commands you can use:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/result - Calculate mileage difference"
    )
welcome_text = "Welcome! I'm your friendly bot. How can I assist you today?"
advice_text = ("You can start sending me photos of your car's "
               "dashboard showing the mileage.")

user_mileages = {}


def extract_mileage_from_image(image_bytes):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    image_part = {
        "mime_type": "image/jpeg",
        "data": image_bytes
    }
    prompt_part = {
        "text": "Return ONLY the number of the mileage (kilometers or miles) "
                "shown on the car dashboard in this photo. If there is no mileage, "
                "return nothing. Do not return any other text or explanation."
    }
    response = model.generate_content([image_part, prompt_part])
    mileage_text = response.text.strip()
    if not mileage_text:
        raise ValueError("No mileage found in Gemini response.")
    match = re.search(r"[0-9]+(?:[.,][0-9]+)?", mileage_text)
    if not match:
        raise ValueError("No valid number found in Gemini response.")
    mileage = float(match.group(0).replace(",", "."))
    return mileage


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, f"{welcome_text}\n\n{help_text}\n\n{advice_text}")


@bot.message_handler(commands=["help"])
def send_help(message):
    bot.reply_to(message, help_text)


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.photo[-1].file_id)
    file = bot.download_file(file_info.file_path)
    try:
        mileage = extract_mileage_from_image(file)
    except Exception as e:
        bot.reply_to(message, "Could not extract a valid mileage value "
                              "from the photo. Please try again.")
        print(f"Error extracting mileage: {e}")
        return
    user_mileages.setdefault(user_id, []).append(mileage)
    bot.reply_to(message, f"Extracted mileage: {mileage}\nSend more photos "
                          f"or type /result to get the difference.")


@bot.message_handler(commands=["result"])
def send_result(message):
    user_id = message.from_user.id
    mileages = user_mileages.get(user_id, [])
    if len(mileages) < 2:
        bot.reply_to(message, "Please send at least two dashboard photos first.")
        return
    diff = max(mileages) - min(mileages)
    bot.reply_to(message, f"Difference between highest and lowest mileage: {diff}\n"
                          f"Highest: {max(mileages)}, Lowest: {min(mileages)}")
    user_mileages[user_id] = []


while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Bot crashed with error: {e}")
        time.sleep(15)