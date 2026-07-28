# AI Viral Video Telegram Bot — Başlanğıc Rehberi

Bu layihə **VidMakerPro** platformasının Telegram bot alternatividir. **TikTok**, **Instagram Reels** və **YouTube Shorts** linklərini qəbul edərək avtomatik 9:16 vertikal AI videoları hazırlayır.

---

## ⚡ Quraşdırma Və İşə Salma

### 1. Asılılıqların Quraşdırılması
```bash
pip install -r requirements.txt
```

### 2. .env Faylının Təyin Olunması
`.env` faylı yaradın və aşağıdakı API açarlarını əlavə edin:
```env
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
GEMINI_API_KEY="your_gemini_api_key"
SUPADATA_API_KEY="your_supadata_api_key_optional"
```

### 3. Botun İşə Salınması
```bash
python bot.py
```

---

## 🧠 Modulların Quruluşu

- `bot.py` — Telegram Bot interfeysi (Link qəbulu, status mesajları, video gönderimi).
- `core/url_extractor.py` — TikTok/Reels/Shorts linklərindən transkript və məzmun çıxarılması.
- `core/script_generator.py` — Gemini AI vasitəsilə 9:16 viral ssenari və səhnə promptlarının tərtibi.
- `core/tts_engine.py` — Edge-TTS vasitəsilə təbii insan səsi ilə səsləndirmə (Pulsuz).
- `core/visual_engine.py` — Pollinations / Flux vasitəsilə 9:16 AI şəkillərin generasiyası.
- `core/video_composer.py` — MoviePy / FFmpeg vasitəsilə audio, vizual və dinamik subtitrlərin 9:16 MP4 videoya montajı.
