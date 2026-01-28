import os
import re
from datetime import datetime
from PIL import Image, ImageFont, ImageDraw
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
from moviepy.audio.AudioClip import CompositeAudioClip
import numpy as np
import textwrap

# 폰트 설정 (Windows 기준)
FONT_TITLE_PATH = "C:/Windows/Fonts/arialbi.ttf" # Arial Bold Italic
FONT_SUB_PATH = "C:/Windows/Fonts/arialbd.ttf"   # Arial Bold

# 레이아웃 좌표 상수
FIXED_TITLE_Y = 190      
FIXED_SUBTITLE_Y = 1040  

# 오디오 사이의 휴식 간격 (초 단위)
PAUSE_DURATION = 0.6 

class Editor:
    def __init__(self):
        os.makedirs("results", exist_ok=True)
        try:
            self.font_title = ImageFont.truetype(FONT_TITLE_PATH, 50)
            self.font_sub = ImageFont.truetype(FONT_SUB_PATH, 46)
        except:
            print("⚠️ Custom fonts not found. Using default.")
            self.font_title = ImageFont.load_default()
            self.font_sub = ImageFont.load_default()

    def clean_text(self, text):
        if not text: return ""
        pattern = r'[^a-zA-Z0-9\s.,?!:;\'"*\-()\[\]%가-힣]'
        clean_text = re.sub(pattern, '', text)
        return clean_text.strip()

    def auto_highlight_title(self, title):
        if '*' in title: return title
        words = title.split()
        long_words = sorted([w for w in words if len(w) > 3], key=len, reverse=True)
        targets = long_words[:3]
        for t in targets:
            if t in title:
                title = title.replace(t, f"*{t}*", 1)
        return title

    def draw_text_with_highlight(self, draw, text_lines, position, font, max_width, align='center', line_spacing=1.2, highlight_style='text'):
        x, start_y = position
        try:
            bbox = font.getbbox("Ay")
            ascender, descender = bbox[1], bbox[3]
        except:
            ascender, descender = 0, 20

        line_height = int((descender - ascender) * line_spacing)
        total_height = line_height * len(text_lines)
        current_y = start_y - (total_height // 2)

        for line in text_lines:
            clean_line = self.clean_text(line)
            parts = []
            buffer = ""; is_highlight = False
            for char in clean_line:
                if char == '*':
                    if buffer: parts.append((buffer, is_highlight))
                    buffer = ""; is_highlight = not is_highlight
                else: buffer += char
            if buffer: parts.append((buffer, is_highlight))

            total_w = sum([font.getlength(p[0]) for p in parts])
            current_x = (max_width - total_w) / 2 if align == 'center' else x

            for part_text, highlight in parts:
                part_w = font.getlength(part_text)
                if highlight and highlight_style == 'box':
                    pad_x, pad_y = 8, 5
                    box_x1 = current_x - pad_x
                    box_y1 = current_y + ascender - pad_y
                    box_x2 = current_x + part_w + pad_x
                    box_y2 = current_y + descender + pad_y
                    draw.rectangle([(box_x1, box_y1), (box_x2, box_y2)], fill='#FFD700')
                    draw.text((current_x, current_y), part_text, font=font, fill='black')
                elif highlight and highlight_style == 'text':
                    for dx, dy in [(-2,-2),(2,2)]:
                        draw.text((current_x+dx, current_y+dy), part_text, font=font, fill='black')
                    draw.text((current_x, current_y), part_text, font=font, fill='#FFFF00')
                else:
                    for dx, dy in [(-2,-2),(2,2)]:
                        draw.text((current_x+dx, current_y+dy), part_text, font=font, fill='black')
                    draw.text((current_x, current_y), part_text, font=font, fill='white')
                current_x += part_w
            current_y += line_height

    def create_base_layer(self, img_path, video_title, duration):
        W, H = 720, 1280
        final_bg_clip = None
        
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
            
            box_height = int(W / target_ratio) 
            img = img.resize((W, box_height), Image.LANCZOS)
            
            def zoom_effect(t):
                scale = 1.0 + (0.04 * t) 
                return scale

            raw_clip = ImageClip(np.array(img)).set_duration(duration)
            zooming_clip = raw_clip.resize(zoom_effect).set_position('center')
            img_container = CompositeVideoClip([zooming_clip], size=(W, box_height))
            bg_base = ColorClip(size=(W, H), color=(0,0,0)).set_duration(duration)
            final_bg_clip = CompositeVideoClip([bg_base, img_container.set_position("center")])
        else:
            final_bg_clip = ColorClip(size=(W, H), color=(0,0,0)).set_duration(duration)

        text_canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_canvas)

        video_title = self.auto_highlight_title(self.clean_text(video_title))
        title_lines = textwrap.wrap(video_title, width=22)
        self.draw_text_with_highlight(
            draw, title_lines, (W//2, FIXED_TITLE_Y), self.font_title, W, highlight_style='box'
        )
        
        if os.path.exists("assets/logo.png"):
            logo = Image.open("assets/logo.png").convert("RGBA")
            logo.thumbnail((150, 150), Image.LANCZOS)
            logo_y = H - logo.size[1] - 30
            text_canvas.paste(logo, ((W - logo.size[0]) // 2, logo_y), logo)

        fixed_layer = ImageClip(np.array(text_canvas)).set_duration(duration)
        return CompositeVideoClip([final_bg_clip, fixed_layer])

    def create_subtitle_clip(self, text_lines, duration):
        W, H = 720, 1280
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        
        if text_lines:
            self.draw_text_with_highlight(
                draw, text_lines, (W//2, FIXED_SUBTITLE_Y), self.font_sub, W, highlight_style='text'
            )
            
        return ImageClip(np.array(canvas)).set_duration(duration)

    def process_special_clip(self, video_path, audio_path, text_content, full_title):
        if not os.path.exists(video_path): return None
        video = VideoFileClip(video_path).resize(width=720)
        
        if os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            total_duration = audio.duration + PAUSE_DURATION
            if total_duration > video.duration:
                freeze_duration = total_duration - video.duration
                last_frame = video.to_ImageClip(t=video.duration - 0.1).set_duration(freeze_duration)
                video = concatenate_videoclips([video, last_frame])
            else:
                video = video.subclip(0, total_duration)
            video = video.set_audio(audio) 
        
        bg = ColorClip(size=(720, 1280), color=(0, 0, 0)).set_duration(video.duration)
        video_centered = video.set_position("center")
        
        W, H = 720, 1280
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        if os.path.exists("assets/logo.png"):
            logo = Image.open("assets/logo.png").convert("RGBA")
            logo.thumbnail((150, 150), Image.LANCZOS)
            logo_y = H - logo.size[1] - 30
            canvas.paste(logo, ((W - logo.size[0]) // 2, logo_y), logo)

        title = self.auto_highlight_title(self.clean_text(full_title))
        title_lines = textwrap.wrap(title, width=22)
        self.draw_text_with_highlight(draw, title_lines, (W//2, FIXED_TITLE_Y), self.font_title, W, highlight_style='box')
        
        if text_content:
            sub_lines = textwrap.wrap(self.clean_text(text_content), width=28)
            self.draw_text_with_highlight(draw, sub_lines, (W//2, FIXED_SUBTITLE_Y), self.font_sub, W, highlight_style='text')

        overlay = ImageClip(np.array(canvas)).set_duration(video.duration)
        return CompositeVideoClip([bg, video_centered, overlay])

    def make_shorts(self, data, category="world"):
        print(f"🎬 [Editor] Creating Video with Framed Zoom...")
        scenes = data['script']['scenes']
        
        raw_title = data.get('title', "News Update")
        final_title = re.sub(r'-?\d{2}-\d{2}', '', raw_title).strip()
        final_title = final_title.strip('-').strip()
        
        clips = []

        # 0. Thumbnail
        thumb_img_path = "images/image_1.png"
        if os.path.exists(thumb_img_path):
            print("📸 [Editor] Creating Thumbnail...")
            thumb_clip = self.create_base_layer(thumb_img_path, final_title, 0.1)
            clips.append(thumb_clip)
        
        # 1. Intro
        intro_text = data.get('intro_narration', "Welcome to Flash News Bite.")
        intro = self.process_special_clip("assets/intro.mp4", "audio/intro.mp3", intro_text, final_title)
        if intro: clips.append(intro)

        # 2. Main Scenes
        for i, scene in enumerate(scenes):
            idx = i + 1
            aud_path = f"audio/audio_{idx}.mp3"
            img_path = f"images/image_{idx}.png"
            if not os.path.exists(aud_path): continue
            
            full_audio = AudioFileClip(aud_path)
            narr_text = scene.get('narration', "")
            
            all_lines = textwrap.wrap(narr_text, width=28)
            num_pages = (len(all_lines) + 3) // 4
            if num_pages < 1: num_pages = 1
            
            total_lines = len(all_lines)
            base_cnt = total_lines // num_pages
            extra = total_lines % num_pages
            
            pages = []
            curr = 0
            for p in range(num_pages):
                cnt = base_cnt + (1 if p < extra else 0)
                pages.append(all_lines[curr : curr + cnt])
                curr += cnt
            
            total_scene_duration = full_audio.duration + PAUSE_DURATION
            base_clip = self.create_base_layer(img_path, final_title, total_scene_duration)
            
            overlays = []
            dur_per_page = full_audio.duration / len(pages)
            
            for p_idx, page_lines in enumerate(pages):
                start_time = p_idx * dur_per_page
                if p_idx == len(pages) - 1:
                    sub_duration = dur_per_page + PAUSE_DURATION
                else:
                    sub_duration = dur_per_page
                
                sub_clip = self.create_subtitle_clip(page_lines, sub_duration)
                sub_clip = sub_clip.set_start(start_time).set_position('center')
                overlays.append(sub_clip)
            
            scene_clip = CompositeVideoClip([base_clip] + overlays)
            scene_clip = scene_clip.set_audio(full_audio)
            clips.append(scene_clip)

        # 3. Outro
        outro_text = data.get('outro_narration', "Thanks for watching.")
        outro = self.process_special_clip("assets/outro.mp4", "audio/outro.mp3", outro_text, final_title)
        if outro: clips.append(outro)

        # Final Render
        final = concatenate_videoclips(clips, method="compose")
        
        # [수정] 맵핑에 health 추가
        suffix_map = {
            "world": "USWORLD", "tech": "TECH", "finance": "FINANCE", 
            "art": "ARTS", "sports": "SPORTS", "ent": "ENT",
            "health": "HEALTH"
        }
        suffix = suffix_map.get(category, "USWORLD")
        out_file = f"results/final_shorts_{suffix}.mp4"
        
        final.write_videofile(out_file, fps=30, codec="libx264", audio_codec="aac", bitrate="5000k", preset="medium")
        print(f"✨ Video Created: {out_file}")