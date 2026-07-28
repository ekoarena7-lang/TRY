import os
import re
import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

def detect_platform(url: str) -> str:
    """Detect platform from URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    return "unknown"

def extract_youtube_id(url: str) -> str:
    """Extract YouTube Video ID from Shorts or standard URL."""
    pattern = r"(?:v=|\/\|vi=|\/v\/|youtu\.be\/|\/shorts\/|\/embed\/)([a-zA-Z0-9_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def extract_transcript(url: str) -> dict:
    """
    Extract transcript, title, and topic from a TikTok, Instagram Reel, or YouTube Shorts URL.
    Returns dict with keys: 'platform', 'content', 'title'.
    """
    platform = detect_platform(url)
    content = ""
    title = f"{platform.capitalize()} Video Content"

    # 1. YouTube Shorts Transcript
    if platform == "youtube":
        video_id = extract_youtube_id(url)
        if video_id:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['az', 'tr', 'en'])
                content = " ".join([item['text'] for item in transcript_list])
                title = f"YouTube Short #{video_id}"
            except Exception as e:
                print(f"YouTube transcript extraction warning: {e}")

    # 2. Supadata API fallback (if configured for TikTok/Instagram/YouTube)
    if not content and SUPADATA_API_KEY:
        try:
            headers = {"x-api-key": SUPADATA_API_KEY}
            res = requests.get(f"https://api.supadata.ai/v1/transcript?url={url}", headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                content = data.get("content") or data.get("transcript") or ""
                title = data.get("title") or title
        except Exception as e:
            print(f"Supadata API fallback warning: {e}")

    # 3. yt-dlp fallback for metadata / video info
    if not content:
        try:
            ydl_opts = {'skip_download': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title') or title
                description = info.get('description') or ""
                content = f"Başlıq: {title}. Təsvir: {description[:500]}"
        except Exception as e:
            print(f"yt-dlp extraction warning: {e}")

    # 4. Ultimate fallback if extraction fails
    if not content or len(content.strip()) < 10:
        content = f"{platform.capitalize()} üzərində viral 9:16 video məzmunu: {url}"

    return {
        "platform": platform,
        "content": content,
        "title": title,
        "url": url
    }

if __name__ == "__main__":
    test_url = "https://www.youtube.com/shorts/sample"
    print(extract_transcript(test_url))
