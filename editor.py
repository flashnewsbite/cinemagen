import os
from PIL import Image, ImageFont, ImageDraw
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
import numpy as np
import textwrap

FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

class Editor:
    def __init__(self):
        os.makedirs("results", exist_ok=True)

    def draw_text_with_highlight(self, draw, text, position, font, max_width, align='center'):
        x, y = position
        
        # [안전 장치] text가 문자열이 아니면 문자열로 변환
        if not isinstance(text, str): text = str(text)
            
        lines = textwrap.wrap(text, width=30)
        if len(lines) > 4: lines = lines[:4] 
        line_height = font.getbbox("Ay")[3] + 15
        
        for line in lines:
            parts = []
            buffer = ""; is_highlight = False
            for char in line:
                if char == '*':
                    if buffer: parts.append((buffer, is_highlight))
                    buffer = ""; is_highlight = not is_highlight
                else: buffer += char
            if buffer: parts.append((buffer, is_highlight))

            total_w = sum([font.getlength(p[0]) for p in parts])
            current_x = (1080 - total_w) / 2 if align == 'center' else x

            for part_text, highlight in parts:
                color = '#FFFF00' if highlight else 'white'
                for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
                    draw.text((current_x+dx, y+dy), part_text, font=font, fill='black')
                draw.text((current_x, y), part_text, font=font, fill=color)
                current_x += font.getlength(part_text)
            y += line_height
        return y

    def create_layout_clip(self, scene_data, img_path, duration, video_title):
        W, H = 720, 1280
        canvas = Image.new('RGB', (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        try: 
            font_title = ImageFont.truetype(FONT_BOLD, 50)
            font_sub = ImageFont.truetype(FONT_BOLD, 40)
        except: 
            font_title = ImageFont.load_default(); font_sub = ImageFont.load_default()

        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGB")
            target_ratio = 4/3
            iw, ih = img.size
            if iw/ih > target_ratio:
                new_w = int(ih * target_ratio)
                img = img.crop(((iw-new_w)//2, 0, (iw-new_w)//2+new_w, ih))
            else:
                new_h = int(iw / target_ratio)
                img = img.crop((0, (ih-new_h)//2, iw, (ih-new_h)//2+new_h))
            img = img.resize((W, int(W/target_ratio)), Image.LANCZOS)
            canvas.paste(img, (0, (H - img.size[1]) // 2))

        self.draw_text_with_highlight(draw, video_title, (0, 100), font_title, W, 'center')
        
        # [에러 해결 포인트] scene_data가 딕셔너리가 맞는지 확인
        narration_text = ""
        if isinstance(scene_data, dict):
            narration_text = scene_data.get('narration', "")
        elif isinstance(scene_data, str):
            narration_text = scene_data # 문자열로 바로 들어온 경우 처리
            
        subtitle_y = ((H + int(W * 3/4)) // 2) + 50 
        self.draw_text_with_highlight(draw, narration_text, (0, subtitle_y), font_sub, W, 'center')

        if os.path.exists("assets/logo.png"):
            logo = Image.open("assets/logo.png").convert("RGBA")
            logo.thumbnail((150, 150), Image.LANCZOS)
            canvas.paste(logo, ((W - logo.size[0]) // 2, H - logo.size[1] - 50), logo)

        return ImageClip(np.array(canvas)).set_duration(duration)

    def process_special_clip(self, video_path, audio_path):
        if not os.path.exists(video_path): return None
        video = VideoFileClip(video_path).resize(width=720)
        if os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            if audio.duration > video.duration:
                freeze = video.to_ImageClip(t='end').set_duration(audio.duration - video.duration)
                return concatenate_videoclips([video, freeze]).set_audio(audio)
            return video.set_audio(audio)
        return video

    def make_shorts(self, data):
        print("🎬 [Editor] Editing Video (High-End & Fast)...")
        scenes = data['script']['scenes']
        video_title = data.get('title', "News Update")
        clips = []
        
        intro = self.process_special_clip("assets/intro.mp4", "audio/intro.mp3")
        if intro: clips.append(intro)

        for i, scene in enumerate(scenes):
            idx = i + 1
            aud_path = f"audio/audio_{idx}.mp3"
            if not os.path.exists(aud_path): continue
            audio = AudioFileClip(aud_path)
            clip = self.create_layout_clip(scene, f"images/image_{idx}.png", audio.duration, video_title)
            clips.append(clip.set_audio(audio))

        outro = self.process_special_clip("assets/outro.mp4", "audio/outro.mp3")
        if outro: clips.append(outro)

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile("results/final_shorts_dynamic.mp4", fps=24, codec="libx264", audio_codec="aac")
        print(f"✨ Video Created: results/final_shorts_dynamic.mp4")