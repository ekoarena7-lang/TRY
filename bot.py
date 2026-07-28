import os
import sys
import asyncio
import logging
import tempfile
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.url_extractor import extract_transcript
from core.script_generator import generate_viral_script
from core.tts_engine import generate_speech
from core.visual_engine import generate_scene_image
from core.video_composer import compose_viral_video

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

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
        "2. Orijinal viral 9:16 ssenari yazam.\n"
        "3. Diktor səsi və AI vizualları generasiya edirəm.\n"
        "4. Dinamik subtitrlərlə 9:16 MP4 video render edib sizə göndərirəm!\n\n"
        "💡 *Başlamaq üçün sadəcə videonun keçid linkini mənə göndərin!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def process_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    status_msg = await update.message.reply_text("🔎 **URL təhlil edilir və video məzmunu oxunur...**", parse_mode="Markdown")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. Extract content from URL / Text
            await status_msg.edit_text("🔎 **URL təhlil edilir və video məzmunu oxunur...**", parse_mode="Markdown")
            extracted_info = extract_transcript(user_text)

            # 2. Generate Viral Script with LLM
            await status_msg.edit_text("🧠 **AI Viral Ssenari və səhnə planı hazırlanır...**", parse_mode="Markdown")
            script_data = generate_viral_script(extracted_info)

            # 3. Generate Audio Speech
            await status_msg.edit_text("🎙 **Diktor səsləndirməsi hazırlanır...**", parse_mode="Markdown")
            audio_path = os.path.join(temp_dir, "narration.mp3")
            generate_speech(script_data.get("full_narration", ""), audio_path, lang="tr")

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
                f"🎯 **Hook:** {script_data.get('hook', '')}\n\n"
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_video_request))

    print("🤖 AI Viral Video Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
