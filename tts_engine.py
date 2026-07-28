import os
import asyncio
import edge_tts

# Default voice choices for Azerbaijani/Turkish/English
VOICE_MAPPING = {
    "az": "az-AZ-BabekNeural",
    "tr": "tr-TR-AhmetNeural",
    "en": "en-US-ChristopherNeural"
}

async def generate_speech_async(text: str, output_path: str, lang: str = "tr") -> str:
    """
    Generate speech MP3 file using Edge-TTS.
    """
    voice = VOICE_MAPPING.get(lang, "tr-TR-AhmetNeural")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

def generate_speech(text: str, output_path: str, lang: str = "tr") -> str:
    """
    Synchronous wrapper for speech generation.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    asyncio.run(generate_speech_async(text, output_path, lang))
    return output_path

if __name__ == "__main__":
    out_file = "temp_test_voice.mp3"
    generate_speech("Salam! Bu sınaq səs faylıdır.", out_file, lang="tr")
    print(f"Generated: {out_file}, Size: {os.path.getsize(out_file)} bytes")
