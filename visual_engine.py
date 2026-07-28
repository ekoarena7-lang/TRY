import os
import urllib.parse
import requests
from PIL import Image
from io import BytesIO

KIE_API_KEY = os.getenv("KIE_API_KEY")

def generate_scene_image(prompt: str, output_path: str, width: int = 1080, height: int = 1920) -> str:
    """
    Generate 9:16 vertical image for a scene using Pollinations.ai / Flux AI.
    Falls back to Kie AI or placeholder if needed.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 1. Primary engine: Pollinations.ai (Free, fast, flux model)
    encoded_prompt = urllib.parse.quote(f"9:16 vertical format, {prompt}")
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&seed=42&nologo=true"

    try:
        res = requests.get(pollinations_url, timeout=25)
        if res.status_code == 200 and len(res.content) > 5000:
            img = Image.open(BytesIO(res.content))
            img.save(output_path)
            return output_path
    except Exception as e:
        print(f"Pollinations AI image generation warning: {e}")

    # 2. Kie AI fallback (if key is configured)
    if KIE_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {KIE_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": "nano-banana-2", "input": {"prompt": prompt, "aspect_ratio": "9:16"}}
            res = requests.post("https://api.kie.ai/api/v1/jobs/createTask", json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                task_id = res.json().get("data", {}).get("taskId")
                if task_id:
                    # Poll Kie task
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
            print(f"Kie AI image fallback warning: {e}")

    # 3. Fallback placeholder (solid background with text/gradient)
    img = Image.new('RGB', (width, height), color=(15, 23, 42))
    img.save(output_path)
    return output_path

if __name__ == "__main__":
    out_img = "temp_scene_1.jpg"
    generate_scene_image("Futuristic cybernetic city sunset, 9:16 vertical, cinematic", out_img)
    print(f"Generated image: {out_img}, Size: {os.path.getsize(out_img)} bytes")
