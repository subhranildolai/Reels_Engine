import os
import sys
import random
from datetime import datetime
import requests
from google import genai
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import textwrap
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, vfx
import numpy as np

# --- CONFIGURATION ---
API_KEY = os.getenv('GEMINI_API_KEY')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')

if API_KEY is None or FB_ACCESS_TOKEN is None or FB_PAGE_ID is None:
    sys.exit("Missing Environment Variables.")

client = genai.Client(api_key=API_KEY)

# Facebook Graph API settings
ACCESS_TOKEN = FB_ACCESS_TOKEN
PAGE_ID = FB_PAGE_ID
GRAPH_API_VERSION = "v22.0"

VIDEO_DURATION = 10
WARM_WHITE = (255, 248, 231) # Cinematic off-white color


def get_daily_text():
    # Different "angles" to prevent the same old lines
    perspectives = [
        "a cold warrior preparing for battle",
        "a self-made billionaire looking at his past",
        "a silent monk in a world of noise",
        "a predator hunting its goals",
        "a master craftsman who hates mediocrity",
        "an underdog with everything to prove"
    ]
    
    themes = ["discipline", "focus", "silence", "time", "action", "pain", "winning"]
    
    angle = random.choice(perspectives)
    topic = random.choice(themes)

    prompt = f"""
    Write a 2-line quote about {topic} from the perspective of {angle}.
    
    RULES:
    - Use simple, blunt English.
    - No "AI-style" poetry or humor.
    - Line 1: The harsh truth.
    - Line 2: The relentless command.
    - Max 12 words total.
    """
    
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text.strip()

def generate_image(text_content):
    print("2. Stamping text onto the canvas...")
    background_path = os.path.join(os.getcwd(), 'background.jpg')
    font_path = os.path.join(os.getcwd(), 'font.ttf')
    
    try:
        img = Image.open(background_path).convert("RGB")
    except FileNotFoundError:
        print("Error: 'background.jpg' missing.")
        return None, None

    # Slightly darken the background for better contrast
    img = ImageEnhance.Brightness(img).enhance(0.82)
    
    try:
        font = ImageFont.truetype(font_path, size=40) 
    except IOError:
        font = ImageFont.load_default()

    wrapped_text = textwrap.fill(text_content, width=20)
    
    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (img.size[0] - text_width) / 2
    y = (img.size[1] - text_height) / 2

    # Subtle text shadow
    shadow_color = (0, 0, 0, 110)
    draw.multiline_text((x + 2, y + 2), wrapped_text, font=font, fill=shadow_color, align="center")

    # Warm white text
    draw.multiline_text((x, y), wrapped_text, font=font, fill=WARM_WHITE, align="center")
    
    temp_bg_path = 'temp_bg.png'
    temp_text_path = 'temp_text.png'
    img.save(temp_bg_path)
    text_layer.save(temp_text_path)
    return temp_bg_path, temp_text_path

def assemble_video(bg_image_path, text_image_path):
    print("3. Assembling the final cinematic reel (Subtle Edition)...")
    music_path = os.path.join(os.getcwd(), 'background_music.mp3')
    
    if not bg_image_path or not text_image_path:
        return None

    # 1. Stable cinematic motion (slow zoom + smooth drift, no jitter)
    base = ImageClip(bg_image_path, duration=VIDEO_DURATION)
    frame_size = base.size

    zoomed = base.resized(1.06)
    max_x_shift = max(0, zoomed.w - frame_size[0])
    max_y_shift = max(0, zoomed.h - frame_size[1])

    def smooth_drift(t):
        progress = min(max(t / VIDEO_DURATION, 0), 1)
        eased = 0.5 - 0.5 * np.cos(np.pi * progress)
        x = -max_x_shift * (0.35 + 0.30 * eased)
        y = -max_y_shift * (0.45 + 0.20 * eased)
        return (x, y)

    moving_bg = zoomed.with_position(smooth_drift)
    final_visual = CompositeVideoClip([moving_bg], size=frame_size).with_duration(VIDEO_DURATION)

    # 2. Text layer reveal in first 3 seconds
    text_clip = ImageClip(text_image_path, duration=VIDEO_DURATION)
    text_clip = text_clip.with_effects([vfx.FadeIn(3)])
    final_visual = CompositeVideoClip([final_visual, text_clip], size=frame_size).with_duration(VIDEO_DURATION)

    # 3. Fade in from black for the whole scene
    final_visual = final_visual.with_effects([vfx.FadeIn(3)])

    # 4. Audio
    try:
        audio = AudioFileClip(music_path).with_duration(VIDEO_DURATION)
        final_video = final_visual.with_audio(audio)
    except Exception:
        print("Warning: 'background_music.mp3' missing. Video will be silent.")
        final_video = final_visual

    # 5. Save with today's date
    today_str = datetime.now().strftime("%Y_%m_%d")
    output_filename = f"Reel_{today_str}.mp4"
    
    print(f"4. Rendering {output_filename}...")
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
    
    # Clean up
    for temp_file in ["temp_bg.png", "temp_text.png"]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
    print(f"\n✅ DONE! Video saved as {output_filename}")
    return output_filename


def upload_to_reels(video_path, description):
    print("5. Uploading video to Facebook Reels...")
    print(f"DEBUG: Using Page ID {PAGE_ID}")
    FB_TOKEN = ACCESS_TOKEN

    if not ACCESS_TOKEN or not PAGE_ID:
        print("Error: ACCESS_TOKEN or PAGE_ID is empty.")
        return False

    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return False

    base_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    session_url = f"{base_url}/{PAGE_ID}/video_reels"

    print("   • Stage 1/3: Init upload session...")
    try:
        init_response = requests.post(
            session_url,
            data={
                "upload_phase": "start",
                "access_token": ACCESS_TOKEN
            },
            timeout=60
        )
    except Exception as error:
        print(f"Facebook init request failed: {error}")
        return False

    try:
        init_json = init_response.json()
    except ValueError:
        print(f"Facebook init response is not JSON: {init_response.text}")
        return False

    if init_response.status_code >= 400 or "error" in init_json:
        print("Facebook init error response:")
        print(init_json)
        return False

    video_id = init_json.get("video_id") or init_json.get("id")
    upload_url = init_json.get("upload_url") or f"https://rupload.facebook.com/video-upload/{video_id}"
    if not video_id:
        print("Facebook init response missing video_id/id:")
        print(init_json)
        return False

    print("   • Stage 2/3: Upload binary .mp4 to rupload...")
    file_size = os.path.getsize(video_path)
    try:
        with open(video_path, "rb") as f:
            headers = {
                'Authorization': f'OAuth {FB_TOKEN}',
                'offset': '0',
                'file_size': str(file_size),
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(file_size)
            }
            upload_response = requests.post(
                upload_url,
                headers=headers,
                data=f,
                timeout=300
            )
    except Exception as error:
        print(f"Facebook upload request failed: {error}")
        return False

    try:
        upload_json = upload_response.json()
    except ValueError:
        upload_json = None

    if upload_response.status_code >= 400 or (upload_json and "error" in upload_json):
        print("Facebook upload error response:")
        if upload_json is not None:
            print(upload_json)
        else:
            print(upload_response.text)
        return False

    print("   • Stage 3/3: Publish reel...")
    try:
        publish_response = requests.post(
            session_url,
            data={
                "upload_phase": "finish",
                "video_id": video_id,
                "video_state": "PUBLISHED",
                "description": description,
                "access_token": ACCESS_TOKEN
            },
            timeout=60
        )
    except Exception as error:
        print(f"Facebook publish request failed: {error}")
        return False

    try:
        publish_json = publish_response.json()
    except ValueError:
        print(f"Facebook publish response is not JSON: {publish_response.text}")
        return False

    if publish_response.status_code >= 400 or "error" in publish_json:
        print("Facebook publish error response:")
        print(publish_json)
        return False

    print("✅ Facebook Reel uploaded successfully.")
    print(publish_json)

    try:
        os.remove(video_path)
        print(f"🧹 Deleted local file after upload: {video_path}")
    except Exception as error:
        print(f"Warning: Upload succeeded but local file could not be deleted: {error}")

    return True


def upload_to_facebook(video_path, caption):
    return upload_to_reels(video_path, caption)

# --- RUN THE ENGINE ---
if __name__ == "__main__":
    daily_text = get_daily_text()
    print(f"\nQuote Generated:\n{daily_text}\n")
    
    bg_file, text_file = generate_image(daily_text)
    if bg_file and text_file:
        generated_video_path = assemble_video(bg_file, text_file)
        if generated_video_path:
            upload_to_facebook(generated_video_path, daily_text)