import os
import sys
import re
import json
import asyncio
import logging
import tempfile
import urllib.parse
import requests
from io import BytesIO
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import google.generativeai as genai
import edge_tts
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def extract_transcript(url):
    try:
        ydl_opts = {'skip_download': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {"title": info.get('title', 'Video'), "content": info.get('description', '')[:500]}
    except Exception as e:
        return {"title": "Viral Short", "content": url}

def generate_viral_script(info, lang="az"):
    if not GEMINI_API_KEY:
        return {"title": "Viral Short", "hook": "Bunu bilirdiniz?", "full_narration": "Bunu bilirdiniz? Dunyani deyisen sirr acildi!", "scenes": [{"text_segment": "Bunu bilirdiniz?", "image_prompt": "Futuristic discovery 9:16"}]}
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        res = model.generate_content(f"Create 9:16 script in JSON with keys title, hook, full_narration, scenes (array of text_segment, image_prompt) for content: {info['title']} {info['content']}")
        text = res.text.strip()
        if "```json" in text:
            text = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL).group(1)
        elif "```" in text:
            text = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL).group(1)
        return json.loads(text)
    except Exception as e:
        return {"title": "Viral Short", "hook": "Bunu bilirdiniz?", "full_narration": "Bunu bilirdiniz? Dunyani deyisen sirr acildi!", "scenes": [{"text_segment": "Bunu bilirdiniz?", "image_prompt": "Futuristic discovery 9:16"}]}

async def generate_speech_async(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = edge_tts.Communicate(text, "az-AZ-BabekNeural")
    await c.save(path)

def generate_scene_image(prompt, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    p = urllib.parse.quote(f"9:16 vertical, {prompt}")
    r = requests.get(f"https://image.pollinations.ai/prompt/{p}?width=1080&height=1920&nologo=true", timeout=20)
    if r.status_code == 200 and len(r.content) > 5000:
        Image.open(BytesIO(r.content)).save(path)
    else:
        Image.new('RGB', (1080, 1920), (15, 23, 42)).save(path)

def compose_viral_video(script, img_paths, audio_path, output_mp4):
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
    audio = AudioFileClip(audio_path)
    dur = audio.duration / max(1, len(img_paths))
    clips = [ImageClip(p).set_duration(dur) for p in img_paths]
    final = concatenate_videoclips(clips, method="compose").set_audio(audio)
    final.write_videofile(output_mp4, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    audio.close()
    for c in clips:
        c.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salam! Video linki gonderin!")

async def ask_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["url"] = update.message.text.strip()
    kb = [[InlineKeyboardButton("AZ Azerbaijan", callback_data="lang_az"), InlineKeyboardButton("TR Turkce", callback_data="lang_tr")]]
    await update.message.reply_text("Dil secin:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    url = context.user_data.get("url", "")
    msg = await q.edit_message_text("Video hazirlanir...")
    with tempfile.TemporaryDirectory() as d:
        try:
            info = extract_transcript(url)
            script = generate_viral_script(info)
            a_path = os.path.join(d, "audio.mp3")
            await generate_speech_async(script.get("full_narration", "Salam"), a_path)
            img_paths = []
            for i, sc in enumerate(script.get("scenes", [])):
                ip = os.path.join(d, f"img_{i}.jpg")
                generate_scene_image(sc.get("image_prompt", "9:16 scene"), ip)
                img_paths.append(ip)
            out_p = os.path.join(d, "out.mp4")
            compose_viral_video(script, img_paths, a_path, out_p)
            with open(out_p, "rb") as f:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption=script.get("title", "Video"))
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"Xeta: {str(e)[:100]}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing!")
        return
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_language))
    app.add_handler(CallbackQueryHandler(handle_lang, pattern="^lang_"))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
