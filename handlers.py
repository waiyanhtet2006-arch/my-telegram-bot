"""
All Telegram bot handlers — commands, text, photo, voice.
"""
import logging
import io
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

import history as hist
import gemini_client as ai
from personality import get_personality_mode_prompt, PERSONALITY_MODES

logger = logging.getLogger(__name__)

NO_KEY_MSG = (
    "ayy bestie, my brain isn't plugged in yet 😭 "
    "the GEMINI_API_KEY secret hasn't been added — "
    "once it's set i'll be fully online and chaotic fr fr 💀"
)


def _get_system_prompt(chat_id: int) -> str:
    mode = hist.get_personality(chat_id)
    return get_personality_mode_prompt(mode)


async def _ai_unavailable(update: Update) -> bool:
    """Check if AI is configured; send error message if not."""
    import os
    if not os.environ.get("GEMINI_API_KEY"):
        await update.message.reply_text(NO_KEY_MSG)
        return True
    return False


# ─── Command Handlers ───────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    hist.clear_history(chat_id)
    await update.message.reply_text(
        "ayyyy hiiiii 👋✨ i'm Zay Zay, your chronically online bestie from Yangon!\n\n"
        "send me literally anything — texts, pics, voice notes — and i'll be here "
        "being my full chaotic self la 😭💖\n\n"
        "type /help to see what i can do daw~"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    modes_text = "\n".join(
        f"  • `{mode}` — {desc}" for mode, desc in PERSONALITY_MODES.items()
    )
    await update.message.reply_text(
        "ok so here's the rundown bestie 📋\n\n"
        "💬 *Text* — just talk to me, i'll talk back (obviously)\n"
        "📸 *Photos* — send any pic and i'll give u my unfiltered take\n"
        "🎙 *Voice notes* — i'll listen and respond (yes i can hear u)\n\n"
        "⚙️ *Commands:*\n"
        "/start — fresh start, clear our history\n"
        "/help — this thing u're reading rn\n"
        "/setpersonality `[mode]` — switch my vibe:\n"
        f"{modes_text}\n\n"
        "no cap i'm built different. let's goooo 🔥",
        parse_mode="Markdown"
    )


async def setpersonality_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    args = context.args

    if not args or args[0] not in PERSONALITY_MODES:
        modes_list = ", ".join(f"`{m}`" for m in PERSONALITY_MODES)
        await update.message.reply_text(
            f"bestie i need a valid mode 😅 choose one: {modes_list}\n"
            "example: `/setpersonality chaos`",
            parse_mode="Markdown"
        )
        return

    mode = args[0]
    hist.set_personality(chat_id, mode)
    confirmations = {
        "default": "ok we're back to default Zay Zay energy ✨ let's go",
        "soft": "soft girl mode activated 🩷 i'll be nice-ish fr",
        "chaos": "CHAOS MODE ON omg we are SO unhinged rn 💀🔥",
        "advice": "wise bestie mode fr fr 🧠✨ i got u, let's talk",
    }
    await update.message.reply_text(confirmations[mode])


# ─── Message Handlers ────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if await _ai_unavailable(update):
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        history = hist.get_history(chat_id)
        system_prompt = _get_system_prompt(chat_id)
        response = await ai.chat(system_prompt, history, user_text)

        if response:
            hist.add_message(chat_id, "user", user_text)
            hist.add_message(chat_id, "model", response)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "ngl something went wrong with my brain rn 😭 try again?"
            )
    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await update.message.reply_text(
            "ok my brain short-circuited for a sec 💀 try again bestie"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    caption = update.message.caption or ""

    if await _ai_unavailable(update):
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        # Get the highest resolution photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)

        # Download photo bytes
        photo_bytes_io = io.BytesIO()
        await file.download_to_memory(photo_bytes_io)
        photo_bytes = photo_bytes_io.getvalue()

        history = hist.get_history(chat_id)
        system_prompt = _get_system_prompt(chat_id)

        user_context = caption if caption else "[user sent a photo]"
        response = await ai.analyze_photo(
            system_prompt, history, photo_bytes, "image/jpeg", caption or None
        )

        if response:
            hist.add_message(chat_id, "user", f"[sent a photo] {caption}".strip())
            hist.add_message(chat_id, "model", response)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "omg i looked at this pic but my words failed me rn 😭 try again?"
            )
    except Exception as e:
        logger.error(f"Photo handler error: {e}")
        await update.message.reply_text(
            "the pic didn't load properly bestie 😭 send again?"
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if await _ai_unavailable(update):
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        # Download voice bytes
        audio_bytes_io = io.BytesIO()
        await file.download_to_memory(audio_bytes_io)
        audio_bytes = audio_bytes_io.getvalue()

        # Check size limit for inline data (8MB)
        size_mb = len(audio_bytes) / (1024 * 1024)
        if size_mb > 7.5:
            await update.message.reply_text(
                "bestie that voice note is TOO LONG 😭 send something shorter la"
            )
            return

        history = hist.get_history(chat_id)
        system_prompt = _get_system_prompt(chat_id)

        response = await ai.transcribe_and_respond(
            system_prompt, history, audio_bytes, "audio/ogg"
        )

        if response:
            hist.add_message(chat_id, "user", "[sent a voice message]")
            hist.add_message(chat_id, "model", response)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "i heard something but idk what 😭 try again?"
            )
    except Exception as e:
        logger.error(f"Voice handler error: {e}")
        await update.message.reply_text(
            "the voice note didn't come through properly 💀 try again bestie"
        )
