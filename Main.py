import os
import random
from datetime import datetime
from google import genai
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import textwrap
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, VideoFileClip, vfx
import numpy as np

# --- CONFIGURATION ---
# Put your real Google Gemini API key here
API_KEY = 'AIzaSyABX_NHWghpSn7XddDu_BJXbwiBEsnoJs4'
client = genai.Client(api_key=API_KEY)

VIDEO_DURATION = 10
WARM_WHITE = (255, 248, 231) # Cinematic off-white color

def get_daily_text():
    print("1. Generating daily philosophy from AI...")
    moods = ["aggressive discipline", "quiet stoicism", "ancient wisdom", "modern psychological warfare"]
    daily_mood = random.choice(moods)

    prompt = f"""
    You are a philosopher and master of self-mastery. Generate 2 lines of text for a video about mastering lust and desire.
    Current Tone: {daily_mood}
    Strict Rules:
    1. Avoid clichés like "Stay strong," "Be a king," or "Master your mind."
    2. Use raw, visceral, and provocative language.
    3. Output exactly two short sentences (under 120 characters total).
    4. Provide ONLY the raw text.
    5. Easy english words, no hard english term. easy to understand, but with a powerful punch. No fluff, no filler. Just pure, unfiltered wisdom.
    6. Should be meaningful.
    """
    
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return response.text.strip()

def generate_image(text_content):
    print("2. Stamping text onto the canvas...")
    
    try:
        img = Image.open('background.jpg').convert("RGB")
    except FileNotFoundError:
        print("Error: 'background.jpg' missing.")
        return None, None

    # Slightly darken the background for better contrast
    img = ImageEnhance.Brightness(img).enhance(0.82)
    
    try:
        font = ImageFont.truetype('font.ttf', size=40) 
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
    
    if not bg_image_path or not text_image_path:
        return

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

    # 2. Optional texture overlay (very subtle)
    try:
        overlay = VideoFileClip("overlay.mp4").with_duration(VIDEO_DURATION).resized(frame_size)
        overlay = overlay.with_opacity(0.05)
        final_visual = CompositeVideoClip([final_visual, overlay], size=frame_size).with_duration(VIDEO_DURATION)
    except Exception:
        pass

    # 3. Text layer reveal in first 3 seconds
    text_clip = ImageClip(text_image_path, duration=VIDEO_DURATION)
    text_clip = text_clip.with_effects([vfx.FadeIn(3)])
    final_visual = CompositeVideoClip([final_visual, text_clip], size=frame_size).with_duration(VIDEO_DURATION)

    # 4. Fade in from black for the whole scene
    final_visual = final_visual.with_effects([vfx.FadeIn(3)])

    # 5. Audio
    try:
        audio = AudioFileClip("background_music.mp3").with_duration(VIDEO_DURATION)
        final_video = final_visual.with_audio(audio)
    except Exception:
        print("Warning: 'background_music.mp3' missing. Video will be silent.")
        final_video = final_visual

    # 6. Save with today's date
    today_str = datetime.now().strftime("%Y_%m_%d")
    output_filename = f"Reel_{today_str}.mp4"
    
    print(f"4. Rendering {output_filename}...")
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
    
    # Clean up
    for temp_file in ["temp_bg.png", "temp_text.png"]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
    print(f"\n✅ DONE! Video saved as {output_filename}")

# --- RUN THE ENGINE ---
if __name__ == "__main__":
    daily_text = get_daily_text()
    print(f"\nQuote Generated:\n{daily_text}\n")
    
    bg_file, text_file = generate_image(daily_text)
    if bg_file and text_file:
        assemble_video(bg_file, text_file)