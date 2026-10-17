import os
import re
import ast
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BUILDER_TELEGRAM_TOKEN", "").strip()
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("🚀 Build Your Bot", callback_data="build")],
    [InlineKeyboardButton("🤖 My Bot Admin", callback_data="admin")],
    [InlineKeyboardButton("✏️ Edit", callback_data="edit")],
])

def slug(text):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)[:40] or "my_bot"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.effective_message.reply_text(
        "Build your first bot, Telegram bot with Bot Builder.",
        reply_markup=MENU,
    )

async def build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = "name"
    await update.effective_message.reply_text("What is your bot's name?")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    folder = DATA_DIR / str(update.effective_user.id)
    files = list(folder.glob("*.py")) if folder.exists() else []
    if not files:
        await update.effective_message.reply_text(
            "No bots created yet. Press Build Your Bot."
        )
        return
    await update.effective_message.reply_text(
        "Your bot files:\n" + "\n".join(f.name for f in files)
    )

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["step"] = "edit"
    await update.effective_message.reply_text(
        "Describe in English what you want to change in your bot."
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "build":
        context.user_data.clear()
        context.user_data["step"] = "name"
        await query.message.reply_text("What is your bot's name?")
    elif query.data == "admin":
        await admin(update, context)
    elif query.data == "edit":
        await edit(update, context)

def generate_bot(name, idea):
    return f'''import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to {name}!\\\\nPurpose: {idea}"
    )

def main():
    if not TOKEN:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in hosting environment.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
'''

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.effective_message.text or "").strip()
    step = context.user_data.get("step")

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "idea"
        await update.message.reply_text(
            "Describe your bot idea in ENGLISH.\\n"
            "Example: Create a study bot that answers math questions."
        )

    elif step == "idea":
        name = context.user_data.get("name", "MyBot")
        source = generate_bot(name, text)

        try:
            ast.parse(source)
        except SyntaxError:
            await update.message.reply_text("Code generation failed.")
            return

        folder = DATA_DIR / str(update.effective_user.id)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (slug(name) + ".py")
        path.write_text(source, encoding="utf-8")

        context.user_data.clear()

        with path.open("rb") as file:
            await update.message.reply_document(
                document=file,
                filename=path.name,
                caption=(
                    "Your Python bot template is ready. "
                    "Deploy it as a separate service to run it."
                ),
            )

    elif step == "edit":
        await update.message.reply_text(
            "Edit request received. This starter version does not "
            "automatically rewrite or redeploy existing code yet."
        )
        context.user_data.clear()

    else:
        await update.message.reply_text(
            "Use /start to begin.", reply_markup=MENU
        )

def main():
    if not TOKEN:
        raise RuntimeError(
            "Set BUILDER_TELEGRAM_TOKEN in hosting Environment Variables."
        )

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("build", build))
    app.add_handler(CommandHandler("mybotadmin", admin))
    app.add_handler(CommandHandler("edit", edit))
    app.add_handler(
        CallbackQueryHandler(buttons, pattern="^(build|admin|edit)$")
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, messages)
    )

    print("Assistant For You is running.")
    app.run_polling()

if __name__ == "__main__":
    main()
