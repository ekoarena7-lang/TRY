import os
import sys
import re
import json
import asyncio
import logging
import tempfile
import urllib.parse
from io import BytesIO
from dotenv import load_dotenv
import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
KIE_API_KEY = os.getenv("KIE_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ==========================================
# 1. URL EXTRACTOR MODULE
# ==========================================
def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    return "unknown"

def extract_youtube_id(url: str) -> str:
    pattern = r"(?:v=|\/\|vi=|\/v\/|youtu\.be\/|\/shorts\/|\/embed\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def extract_transcript(url: str) -> dict:
    platform = detect_platform(url)
    content = ""
    title = f"{platform.capitalize()} Video Content"

    if platform == "youtube":
        video_id = extract_youtube_id(url)
        if video_id:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['az', 'tr', 'en'])
                content = " ".join([item['text'] for item in transcript_list])
                title = f"YouTube Short #{video_id}"
            except Exception as e:
                logging.warning(f"YouTube transcript extraction warning: {e}")

    if not content and SUPADATA_API_KEY:
        try:
            headers = {"x-api-key": SUPADATA_API_KEY}
            res = requests.get(f"https://api.supadata.ai/v1/transcript?url={url}", headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                content = data.get("content") or data.get("transcript") or ""
                title = data.get("title") or title
        except Exception as e:
            logging.warning(f"Supadata API fallback warning: {e}")

    if not content:
        try:
            ydl_opts = {'skip_download': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title') or title
                description = info.get('description') or ""
                content = f"Basliq: {title}. Tesvir: {description[:500]}"
        except Exception as e:
            logging.warning(f"yt-dlp extraction warning: {e}")

    if not content or len(content.strip()) < 10:
        content = f"{platform.capitalize()} uzerinde viral 9:16 video mezmunu: {url}"

    return {
        "platform": platform,
        "content": content,
        "title": title,
        "url": url
    }

# ==========================================
# 2. SCRIPT GENERATOR MODULE
# ==========================================
def generate_viral_script(extracted_info: dict, language: str = "az") -> dict:
    raw_content = extracted_info.get("content", "")
    title = extracted_info.get("title", "")

    lang_names = {
        "az": "Azerbaijan dili",
        "tr": "Turkce",
        "en": "English"
    }
    target_lang_name = lang_names.get(language, "Turkce")

    prompt = f"""
    Asagidaki video mezmununu analiz et ve TikTok / YouTube Shorts / Instagram Reels ucun VIRAL 9:16 video ssenarisi hazirla:

    VIDEO MEZMUNU:
    Basliq: {title}
    Metn: {raw_content[:2000]}

    ZORUNLU DIL: {target_lang_name} ({language.upper()})

    XAHIS OLUNUR ASAGIDAKIDAN IBARET STRICT JSON FORMATINDA CAVAB VER:
    {{
        "title": "Videonun celbedici basliqi ({target_lang_name})",
        "hook": "Ilk 3 saniyede diqqet ceken guclu giris cumlesi ({target_lang_name})",
        "full_narration": "Videonun butun diktor metni ({target_lang_name})",
        "scenes": [
            {{
                "scene_id": 1,
                "text_segment": "Bu sehnede oxunacaq qisa altyazi metni ({target_lang_name})",
                "image_prompt": "Detailed English prompt for AI image generator depicting this scene in 9:16 vertical format, cinematic lighting, 8k quality",
                "duration_est": 5
            }}
        ]
    }}
    Yalniz JSON qaytar.
    """

    if not GEMINI_API_KEY:
        logging.warning("GEMINI_API_KEY missing. Returning fallback sample script.")
        return _fallback_script(title)

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        if "```json" in text:
            text = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL).group(1)
        elif "```" in text:
            text = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL).group(1)

        return json.loads(text)
    except Exception as e:
        logging.error(f"Gemini script generation error: {e}")
        return _fallback_script(title)

def _fallback_script(title: str) -> dict:
    return {
        "title": f"Viral Video: {title[:30]}",
        "hook": "Bunu bilirdiniz? Dunyani deyisen sirr acildi!",
        "full_narration": "Bunu bilirdiniz? Dunyani deyisen sirr acildi! Coxlari bunun ferqinde deyil, amma bu melumat sizin heyatinizi deyise biler. Sona qeder izleyin ve dostlarinizla paylasin!",
        "scenes": [
            {
                "scene_id": 1,
                "text_segment": "Bunu bilirdiniz? Dunyani deyisen sirr acildi!",
                "image_prompt": "A dramatic futuristic discovery with glowing light, cinematic 9:16 vertical, highly detailed",
                "duration_est": 4
            },
            {
                "scene_id": 2,
                "text_segment": "Coxlari bunun ferqinde deyil, amma bu melumat sizin heyatinizi deyise biler.",
                "image_prompt": "A person looking astonished at a glowing holographic screen, futuristic atmosphere, 9:16 vertical, 8k",
                "duration_est": 6
            },
            {
                "scene_id": 3,
                "text_segment": "Sona qeder izleyin ve dostlarinizla paylasin!",
                "image_prompt": "A vibrant tech digital viral animation background, 9:16 vertical format",
                "duration_est": 5
            }
        ]
    }

# ==========================================
# 3. TTS ENGINE MODULE
# ==========================================
VOICE_MAPPING = {
    "az": "az-AZ-BabekNeural",
    "tr": "tr-TR-AhmetNeural",
    "en": "en-US-ChristopherNeural"
}

async def generate_speech_async(text: str, output_path: str, lang: str = "az") -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    voice = VOICE_MAPPING.get(lang, "az-AZ-BabekNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

# ==========================================
# 4. VISUAL ENGINE MODULE
# ==========================================
def generate_scene_image(prompt: str, output_path: str, width: int = 1080, height: int = 1920) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    encoded_prompt = urllib.parse.quote(f"9:16 vertical format, {prompt}")
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&seed=42&nologo=true"

    try:
        res = requests.get(pollinations_url, timeout=25)
        if res.status_code == 200 and len(res.content) > 5000:
            img = Image.open(BytesIO(res.content))
            img.save(output_path)
            return output_path
    except Exception as e:
        logging.warning(f"Pollinations AI image generation warning: {e}")

    if KIE_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": "nano-banana-2", "input": {"prompt": prompt, "aspect_ratio": "9:16"}}
            res = requests.post("https://api.kie.ai/api/v1/jobs/createTask", json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                task_id = res.json().get("data", {}).get("taskId")
                if task_id:
                    import time
                    for _ in range(10):
                        time.sleep(3)
                        r_info = requests.get(f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={task_id}", headers=headers)
                        if r_info.status_code == 200:
                            data = r_info.json().get("data", {})
                            if data.get("state") == "success":
                                img_url = data.get("resultJson", {}).get("resultUrls", [None])[0]
                                if img_url:
                                    img_data = requests.get(img_url).content
                                    with open(output_path, "wb") as f:
                                        f.write(img_data)
                                    return output_path
        except Exception as e:
            logging.warning(f"Kie AI image fallback warning: {e}")

    img = Image.new('RGB', (width, height), color=(15, 23, 42))
    img.save(output_path)
    return output_path

# ==========================================
# 5. VIDEO COMPOSER MODULE
# ==========================================
def add_subtitles_to_image(image_path: str, text: str, output_path: str, width: int = 1080, height: int = 1920):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 54)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
        except Exception:
            font = ImageFont.load_default()

    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 22:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    formatted_text = "\n".join(lines)

    text_bbox = draw.multiline_textbbox((0, 0), formatted_text, font=font, align="center")
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    x = (width - text_w) // 2
    y = height - text_h - 280

    padding = 24
    box = [x - padding, y - padding, x + text_w + padding, y + text_h + padding]

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(box, radius=18, fill=(15, 23, 42, 210))

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    draw.multiline_text((x, y), formatted_text, font=font, fill=(255, 255, 255), align="center")

    img.convert("RGB").save(output_path)
    return output_path

def compose_viral_video(script_data: dict, scene_image_paths: list, audio_path: str, output_mp4: str) -> str:
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
    audio_clip = AudioFileClip(audio_path)
    total_audio_duration = audio_clip.duration

    scenes = script_data.get("scenes", [])
    num_scenes = len(scenes)

    if num_scenes == 0:
        raise ValueError("No scenes provided in script data.")

    scene_duration = total_audio_duration / num_scenes
    clips = []
    temp_subtitled_images = []

    try:
        output_dir = os.path.dirname(output_mp4)
        for idx, scene in enumerate(scenes):
            img_path = scene_image_paths[idx] if idx < len(scene_image_paths) else scene_image_paths[0]
            sub_text = scene.get("text_segment", "")

            sub_img_path = os.path.join(output_dir, f"temp_sub_{idx}.jpg")
            add_subtitles_to_image(img_path, sub_text, sub_img_path)
            temp_subtitled_images.append(sub_img_path)

            clip = ImageClip(sub_img_path).set_duration(scene_duration)
            clips.append(clip)

        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip)

        final_video.write_videofile(
            output_mp4,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger=None
        )
    finally:
        audio_clip.close()
        for c in clips:
            c.close()
        for t_img in temp_subtitled_images:
            if os.path.exists(t_img):
                os.remove(t_img)

    return output_mp4

# ==========================================
# 6. TELEGRAM BOT HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Salam! AI Viral Video Generator Botuna Xos Gelmisiniz!\n\n"
        "Men VidMakerPro sisteminin Telegram versiyasiyam. Mene istenilen TikTok, Instagram Reel "
        "ve ya YouTube Shorts linkini daxil edin (ve ya her hansi ideya/movzu yazin).\n\n"
        "Men ne edirem?\n"
        "1. Linkdeki mezmunu tehlil edirem.\n"
        "2. Secdiyiniz dilde (Turkce, English, Azerbaycan) viral 9:16 ssenari hazirlayiram.\n"
        "3. Diktor sesi ve AI vizuallari generasiya edirem.\n"
        "4. Dinamik subtitlerle 9:16 MP4 video render edib size gonderem!\n\n"
        "Baslamaq ucun sadece videonun kecid linkini mene gonderin!"
    )
    await update.message.reply_text(welcome_text)

async def ask_language_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    context.user_data["pending_input"] = user_text

    keyboard = [
        [
            InlineKeyboardButton("TR Turkce", callback_data="lang_tr"),
            InlineKeyboardButton("EN English", callback_data="lang_en"),
            InlineKeyboardButton("AZ Azerbaijan", callback_data="lang_az"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Lutfen videonun ve diktorun dilini secin / Please select the language for the video:",
        reply_markup=reply_markup
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected_lang = query.data.replace("lang_", "")
    user_text = context.user_data.get("pending_input", "")

    if not user_text:
        await query.edit_message_text("Melumat tapilmadi. Lutfen linki yeniden gonderin.")
        return

    lang_labels = {
        "tr": "TR Turkce",
        "en": "EN English",
        "az": "AZ Azerbaijan"
    }

    selected_label = lang_labels.get(selected_lang, selected_lang)
    status_msg = await query.edit_message_text(
        f"Dil secildi: {selected_label}\nURL tehlil edilir ve mezmun oxunur..."
    )

    chat_id = update.effective_chat.id

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            extracted_info = extract_transcript(user_text)

            await status_msg.edit_text(
                f"AI Viral Ssenari ({selected_label}) hazirlanir..."
            )
            script_data = generate_viral_script(extracted_info, language=selected_lang)

            await status_msg.edit_text(
                f"Diktor seslendirmesi ({selected_label}) hazirlanir..."
            )
            audio_path = os.path.join(temp_dir, "narration.mp3")
            await generate_speech_async(script_data.get("full_narration", ""), audio_path, lang=selected_lang)

            await status_msg.edit_text("9:16 AI sehne vizuallari generasiya olunur...")
            scenes = script_data.get("scenes", [])
            scene_image_paths = []

            for idx, scene in enumerate(scenes):
                img_path = os.path.join(temp_dir, f"scene_{idx}.jpg")
                prompt = scene.get("image_prompt", "viral 9:16 scene")
                generate_scene_image(prompt, img_path)
                scene_image_paths.append(img_path)

            await status_msg.edit_text("9:16 Video render edilir ve subtitler montaj olunur...")
            output_video_path = os.path.join(temp_dir, "final_viral_short.mp4")
            compose_viral_video(script_data, scene_image_paths, audio_path, output_video_path)

            await status_msg.edit_text("Video hazir oldu! Telegram catina gonderilir...")

            caption = (
                f"Title: {script_data.get('title', 'AI Viral Short')}\n\n"
                f"Hook: {script_data.get('hook', '')}\n"
                f"Dil: {selected_label}\n\n"
                f"VidMaker Pro AI Generator ile hazirlanmisdir."
            )

            with open(output_video_path, "rb") as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=caption,
                    supports_streaming=True
                )

            await status_msg.delete()

        except Exception as e:
            logging.error(f"Error processing video: {e}", exc_info=True)
            await status_msg.edit_text(f"Xeta bas verdi: {str(e)[:200]}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set in environment variables.")
        print("Please set TELEGRAM_BOT_TOKEN in .env or master.env file.")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_language_preference))
    app.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))

    print("AI Viral Video Telegram Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

