import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

def add_subtitles_to_image(image_path: str, text: str, output_path: str, width: int = 1080, height: int = 1920):
    """
    Overlay stylish dynamic 9:16 subtitles onto a scene image using Pillow.
    Guarantees cross-platform execution without relying on ImageMagick.
    """
    img = Image.open(image_path).convert("RGB")
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    draw = ImageDraw.Draw(img)
    
    # Try system fonts or default font
    try:
        font = ImageFont.truetype("arial.ttf", 54)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
        except Exception:
            font = ImageFont.load_default()

    # Wrap text to max 25 characters per line
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

    # Subtitle box position (lower center of 9:16 frame)
    text_bbox = draw.multiline_textbbox((0, 0), formatted_text, font=font, align="center")
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    x = (width - text_w) // 2
    y = height - text_h - 280

    # Draw dark semi-transparent pill box background for high readability
    padding = 24
    box = [x - padding, y - padding, x + text_w + padding, y + text_h + padding]
    
    # Create transparent overlay for box
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(box, radius=18, fill=(15, 23, 42, 210))
    
    # Draw text outline and main text
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    
    draw.multiline_text((x, y), formatted_text, font=font, fill=(255, 255, 255), align="center")
    
    img.convert("RGB").save(output_path)
    return output_path

def compose_viral_video(script_data: dict, scene_image_paths: list, audio_path: str, output_mp4: str) -> str:
    """
    Assemble scene images, overlay subtitles, attach audio, and render 9:16 MP4 video.
    """
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
    
    # Load audio to get exact total duration
    audio_clip = AudioFileClip(audio_path)
    total_audio_duration = audio_clip.duration
    
    scenes = script_data.get("scenes", [])
    num_scenes = len(scenes)
    
    if num_scenes == 0:
        raise ValueError("No scenes provided in script data.")
        
    # Calculate duration per scene based on audio duration
    scene_duration = total_audio_duration / num_scenes
    
    clips = []
    temp_subtitled_images = []
    
    try:
        for idx, scene in enumerate(scenes):
            img_path = scene_image_paths[idx] if idx < len(scene_image_paths) else scene_image_paths[0]
            sub_text = scene.get("text_segment", "")
            
            output_dir = os.path.dirname(output_mp4)
            sub_img_path = os.path.join(output_dir, f"temp_sub_{idx}.jpg")
            add_subtitles_to_image(img_path, sub_text, sub_img_path)
            temp_subtitled_images.append(sub_img_path)
            
            clip = ImageClip(sub_img_path).set_duration(scene_duration)
            clips.append(clip)
            
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_audio(audio_clip)
        
        # Render 9:16 MP4 at 24fps
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
        # Cleanup temporary clips and audio handlers
        audio_clip.close()
        for c in clips:
            c.close()
        for t_img in temp_subtitled_images:
            if os.path.exists(t_img):
                os.remove(t_img)
                
    return output_mp4

if __name__ == "__main__":
    print("Video composer module ready.")
