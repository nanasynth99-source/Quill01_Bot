import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from google import genai

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to store user states
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message and instructions."""
    print("-> /start command received!", flush=True)
    await update.message.reply_text(
        "👋 Welcome to the AI Writing Assistant Bot!\n\n"
        "Send me any text first, and then choose what you want me to do with it."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores the user's text and presents processing options."""
    user_id = update.message.from_user.id
    text_to_process = update.message.text
    print(f"-> Received message from user {user_id}", flush=True)

    user_data[user_id] = {"text": text_to_process}

    keyboard = [
        [
            InlineKeyboardButton("🔄 Paraphrase", callback_data="paraphrase"),
            InlineKeyboardButton("📝 Summarize", callback_data="summarize")
        ],
        [
            InlineKeyboardButton("✨ Fix Grammar", callback_data="grammar"),
            InlineKeyboardButton("✍️ Rewrite (Formal)", callback_data="rewrite_formal")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("What would you like me to do with this text?", reply_markup=reply_markup)

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the button click and calls the Gemini AI."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    print(f"-> User {user_id} selected action: {action}", flush=True)

    if user_id not in user_data or "text" not in user_data[user_id]:
        await query.edit_message_text("Error: Please send your text again.")
        return

    original_text = user_data[user_id]["text"]
    await query.edit_message_text("🤖 Processing your text... please wait.")

    prompts = {
        "paraphrase": f"Paraphrase the following text in a natural, engaging way while keeping the original meaning:\n\n{original_text}",
        "summarize": f"Provide a concise summary and key bullet points for the following text:\n\n{original_text}",
        "grammar": f"Correct all grammatical, spelling, and punctuation errors in the following text. Output ONLY the corrected text without explanations:\n\n{original_text}",
        "rewrite_formal": f"Rewrite the following text using a professional and formal tone:\n\n{original_text}"
    }

    try:
        # Initialize client inside handler to catch key issues safely
        ai_client = genai.Client(api_key=GEMINI_KEY)
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompts[action],
        )
        result_text = response.text
        await query.message.reply_text(f"✨ **Result:**\n\n{result_text}", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"AI Error: {e}")
        print(f"⚠️ AI Error details: {e}", flush=True)
        await query.message.reply_text("❌ Sorry, something went wrong while processing your request.")
        
    finally:
        if user_id in user_data:
            del user_data[user_id]

def main():
    """Starts the bot application."""
    print("-> Starting bot execution...", flush=True)
    if not TOKEN:
        print("❌ CRITICAL ERROR: TELEGRAM_BOT_TOKEN environment variable is missing!", flush=True)
        return
    if not GEMINI_KEY:
        print("❌ CRITICAL ERROR: GEMINI_API_KEY environment variable is missing!", flush=True)
        return

    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(CallbackQueryHandler(handle_choice))

        print("🚀 Bot setup complete. Starting polling loop...", flush=True)
        app.run_polling()
    except Exception as e:
        print(f"❌ CRITICAL CRASH DURING STARTUP: {e}", flush=True)

if __name__ == "__main__":
    main()
