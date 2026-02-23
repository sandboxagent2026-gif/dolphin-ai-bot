import os
import logging
import concurrent.futures
import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

conversation_memory = {}
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def get_ai_response(user_id: int, user_message: str) -> str:
    if user_id not in conversation_memory:
        conversation_memory[user_id] = []

    conversation_memory[user_id].append({"role": "user", "content": user_message})
    history = conversation_memory[user_id][-20:]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://dolphin-ai-bot-fcmj.onrender.com",
        "X-Title": "Dolphin AI Bot"
    }

    payload = {
                                "model": "arcee-ai/trinity-large-preview:free",
        "messages": [
            {"role": "system", "content": "Sei Dolphin, un assistente AI utile, amichevole e intelligente. Rispondi in modo chiaro e conciso."}
        ] + history
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        assistant_message = data["choices"][0]["message"]["content"]
        conversation_memory[user_id].append({"role": "assistant", "content": assistant_message})
        return assistant_message
    except requests.exceptions.Timeout:
        return "Scusa, la richiesta ha impiegato troppo tempo. Riprova."
    except Exception as e:
        logger.error(f"Errore OpenRouter: {e}")
        return f"Errore nella comunicazione con l'AI: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Ciao {user.first_name}! Sono Dolphin AI Bot\n\n"
        "Puoi scrivermi qualsiasi cosa e ti risponder\u00f2 con l'AI.\n\n"
        "Comandi disponibili:\n"
        "/start - Messaggio di benvenuto\n"
        "/reset - Azzera la memoria della conversazione\n"
        "/help - Mostra questo aiuto"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_memory[user_id] = []
    await update.message.reply_text("Memoria conversazione azzerata! Possiamo ricominciare da capo.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Dolphin AI Bot - Comandi:\n\n"
        "/start - Messaggio di benvenuto\n"
        "/reset - Azzera la memoria della conversazione\n"
        "/help - Mostra questo aiuto\n\n"
        "Scrivi qualsiasi messaggio per chattare con l'AI!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    loop = context.application.loop if hasattr(context.application, 'loop') else __import__('asyncio').get_event_loop()
    import asyncio
    response = await asyncio.wrap_future(executor.submit(get_ai_response, user_id, user_message))
    await update.message.reply_text(response)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if WEBHOOK_URL:
        webhook_path = f"/webhook/{TELEGRAM_TOKEN}"
        full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"Avvio in modalita WEBHOOK: {full_webhook_url} porta {port}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=webhook_path,
            webhook_url=full_webhook_url
        )
    else:
        logger.info("Avvio in modalita POLLING (locale)")
        app.run_polling()

if __name__ == "__main__":
    main()
