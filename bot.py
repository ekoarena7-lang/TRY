import os
import sys
import asyncio
import logging
import tempfile
from dotenv import load_dotenv

# Add current directory to top of sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.url_extractor import extract_transcript
from core.script_generator import generate_viral_script
from core.tts_engine import generate_speech_async
from core.visual_engine import generate_scene_image
from core.video_composer import compose_viral_video

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Salam! AI Viral Video Generator Botuna Xoş Gelmisiniz!**\n\n"
        "Mən VidMakerPro sisteminin Telegram versiyasıyam. Mənə istənilən **TikTok**, **Instagram Reel** "
        "və ya **YouTube Shorts** linkini daxil edin (və ya hər hansı ideya/mövzu yazın).\n\n"
        "⚡ **Mən nə edirəm?**\n"
        "1. Linkdəki məzmunu təhlil edirəm.\n"
        "2. Seçdiyiniz dildə (Türkçe, English, Azərbaycan) viral 9:16 ssenari hazırlayıram.\n"
        "3. Diktor səsi və AI vizualları generasiya edirəm.\n"
        "4. Dinamik subtitrlərlə 9:16 MP4 video render edib sizə göndərirəm!\n\n"
        "💡 *Başlamaq üçün sadəcə videonun keçid linkini mənə göndərin!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def ask_language_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    context.user_data["pending_input"] = user_text

    keyboard = [
        [
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇦🇿 Azərbaycan", callback_data="lang_az"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌐 **Lütfən videonun və diktorun dilini seçin / Please select the language for the video:**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_lang = query.data.replace("lang_", "")
    user_text = context.user_data.get("pending_input", "")

    if not user_text:
        await query.edit_message_text("❌ **Məlumat tapılmadı. Lütfən linki yenidən göndərin.**")
        return

    lang_labels = {
        "tr": "🇹🇷 Türkçe",
        "en": "🇬🇧 English",
        "az": "🇦🇿 Azərbaycan"
    }

    selected_label = lang_labels.get(selected_lang, selected_lang)
    status_msg = await query.edit_message_text(
        f"🌐 Dil seçildi: **{selected_label}**\n🔎 **URL təhlil edilir və məzmun oxunur...**",
        parse_mode="Markdown"
    )

    chat_id = update.effective_chat.id

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. Extract content from URL / Text
            extracted_info = extract_transcript(user_text)

            # 2. Generate Viral Script with LLM in selected language
            await status_msg.edit_text(
                f"🧠 **AI Viral Ssenari ({selected_label}) hazırlanır...**",
                parse_mode="Markdown"
            )
            script_data = generate_viral_script(extracted_info, language=selected_lang)

            # 3. Generate Audio Speech in selected language
            await status_msg.edit_text(
                f"🎙 **Diktor səsləndirməsi ({selected_label}) hazırlanır...**",
                parse_mode="Markdown"
            )
            audio_path = os.path.join(temp_dir, "narration.mp3")
            await generate_speech_async(script_data.get("full_narration", ""), audio_path, lang=selected_lang)

            # 4. Generate AI Images for Scenes
            await status_msg.edit_text("🎨 **9:16 AI səhnə vizualları generasiya olunur...**", parse_mode="Markdown")
            scenes = script_data.get("scenes", [])
            scene_image_paths = []
            
            for idx, scene in enumerate(scenes):
                img_path = os.path.join(temp_dir, f"scene_{idx}.jpg")
                prompt = scene.get("image_prompt", "viral 9:16 scene")
                generate_scene_image(prompt, img_path)
                scene_image_paths.append(img_path)

            # 5. Compose Video MP4 with Subtitles
            await status_msg.edit_text("🎬 **9:16 Video render edilir və subtitrlər montaj olunur...**", parse_mode="Markdown")
            output_video_path = os.path.join(temp_dir, "final_viral_short.mp4")
            compose_viral_video(script_data, scene_image_paths, audio_path, output_video_path)

            # 6. Send Video to Telegram Chat
            await status_msg.edit_text("🚀 **Video hazır oldu! Telegram çatına göndərilir...**", parse_mode="Markdown")
            
            caption = (
                f"🔥 **{script_data.get('title', 'AI Viral Short')}**\n\n"
                f"🎯 **Hook:** {script_data.get('hook', '')}\n"
                f"🌐 **Dil:** {selected_label}\n\n"
                f"🤖 *VidMaker Pro AI Generator ilə hazırlanmışdır.*"
            )

            with open(output_video_path, "rb") as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    parse_mode="Markdown",
                    supports_streaming=True
                )
                
            await status_msg.delete()

        except Exception as e:
            logging.error(f"Error processing video: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ **Xəta baş verdi:** {str(e)[:200]}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set in environment variables.")
        print("Please set TELEGRAM_BOT_TOKEN in .env or master.env file.")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_language_preference))
    app.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))

    print("🤖 AI Viral Video Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
