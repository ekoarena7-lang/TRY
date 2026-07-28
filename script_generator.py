import os
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_viral_script(extracted_info: dict, language: str = "az") -> dict:
    """
    Generate a 9:16 viral short video script from extracted content.
    Returns structured dict with hook, narrative_script, and scene prompts.
    """
    raw_content = extracted_info.get("content", "")
    title = extracted_info.get("title", "")

    lang_names = {
        "az": "Azərbaycan dili",
        "tr": "Türkçe",
        "en": "English"
    }
    target_lang_name = lang_names.get(language, "Türkçe")

    prompt = f"""
    Aşağıdakı video məzmununu analiz et və TikTok / YouTube Shorts / Instagram Reels üçün VIRAL 9:16 video ssenarisi hazırla:

    VİDEO MƏZMUNU:
    Başlıq: {title}
    Mətn: {raw_content[:2000]}

    ZORUNLU DİL: {target_lang_name} ({language.upper()})
    Tüm başlık, hook, anlatım mətni və subtitrlər strictly {target_lang_name} dilində yazılmalıdır.

    XAHİŞ OLUNUR AŞAĞIDAKIDAN İBARƏT STRICT JSON FORMATINDA CAVAB VER:
    {{
        "title": "Videonun cəlbedici başlığı ({target_lang_name})",
        "hook": "İlk 3 saniyədə diqqət çəkən güclü giriş cümləsi ({target_lang_name})",
        "full_narration": "Videonun bütün diktor mətni ({target_lang_name})",
        "scenes": [
            {{
                "scene_id": 1,
                "text_segment": "Bu səhnədə oxunacaq qısa altyazı mətni ({target_lang_name})",
                "image_prompt": "Detailed English prompt for AI image generator depicting this scene in 9:16 vertical format, cinematic lighting, 8k quality",
                "duration_est": 5
            }}
        ]
    }}
    Yalnız JSON qaytar.
    """

    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY missing. Returning fallback sample script.")
        return _fallback_script(title)

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean JSON markdown quotes if present
        if "```json" in text:
            text = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL).group(1)
        elif "```" in text:
            text = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL).group(1)

        return json.loads(text)
    except Exception as e:
        print(f"Gemini script generation error: {e}")
        return _fallback_script(title)

def _fallback_script(title: str) -> dict:
    return {
        "title": f"Viral Video: {title[:30]}",
        "hook": "Bunu bilirdiniz? Dünyanı dəyişən sirr açıldı!",
        "full_narration": "Bunu bilirdiniz? Dünyanı dəyişən sirr açıldı! Çoxları bunun fərqində deyil, amma bu məlumat sizin həyatınızı dəyişə bilər. Sona qədər izləyin və dostlarınızla paylaşın!",
        "scenes": [
            {
                "scene_id": 1,
                "text_segment": "Bunu bilirdiniz? Dünyanı dəyişən sirr açıldı!",
                "image_prompt": "A dramatic futuristic discovery with glowing light, cinematic 9:16 vertical, highly detailed",
                "duration_est": 4
            },
            {
                "scene_id": 2,
                "text_segment": "Çoxları bunun fərqində deyil, amma bu məlumat sizin həyatınızı dəyişə bilər.",
                "image_prompt": "A person looking astonished at a glowing holographic screen, futuristic atmosphere, 9:16 vertical, 8k",
                "duration_est": 6
            },
            {
                "scene_id": 3,
                "text_segment": "Sona qədər izləyin və dostlarınızla paylaşın!",
                "image_prompt": "A vibrant tech digital viral animation background, 9:16 vertical format",
                "duration_est": 5
            }
        ]
    }

if __name__ == "__main__":
    test_data = {"title": "Süni İntellekt", "content": "Süni intellekt gələcəyimizi neçə dəyişəcək."}
    script = generate_viral_script(test_data)
    print(json.dumps(script, ensure_ascii=False, indent=2))
