import os
import re
from datetime import datetime
from PIL import Image, ImageFont, ImageDraw
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
import moviepy.video.fx.all as vfx
import numpy as np
import textwrap

# [설정] 레이아웃 (1920x1080 기준)
W, H = 1920, 1080

# [설정] 폰트 크기 및 위치 (큼직하게 설정)
FONT_SIZE = 100   # 1920p에서 잘 보이도록 100px로 설정
SUBTITLE_Y = 850  # 하단 여백 확보

class EditorLong:
    def __init__(self):
        os.makedirs("results", exist_ok=True)
        self.font = self.load_font()

    def load_font(self):
        """
        [수정] assets 폴더 내의 폰트를 우선적으로 찾습니다.
        """
        font_candidates = [
            ("assets/Roboto-Bold.ttf", "Asset Roboto"),     # 1순위: assets 폴더
            ("Roboto-Bold.ttf", "Root Roboto"),             # 2순위: 루트 폴더
            ("C:/Windows/Fonts/arialbd.ttf", "Windows Arial"), # 3순위: 윈도우 기본
            ("C:/Windows/Fonts/malgunbd.ttf", "Windows Malgun") # 4순위: 맑은 고딕
        ]

        for path, name in font_candidates:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, FONT_SIZE)
                    print(f"✅ [Font] Successfully loaded: {name} (Path: {path})")
                    return font
                except Exception as e:
                    print(f"⚠️ Failed loading {name}: {e}")
                    continue
        
        # 모든 시도 실패 시
        print("🚨 [Font] CRITICAL WARNING: No fonts found. Using tiny default font.")
        return ImageFont.load_default()

    def clean_text(self, text):
        if not text: return ""
        pattern = r'[^a-zA-Z0-9\s.,?!:;\'"*\-()\[\]%가-힣]'
        return re.sub(pattern, '', text).strip()

    def create_subtitle_image(self, text_chunk, width=1600):
        # [설정] 한 줄당 30자 (글자가 커졌으므로 줄바꿈 자주 일어나게)
        wrapper = textwrap.TextWrapper(width=30) 
        lines = wrapper.wrap(text_chunk)
        
        line_height = int(FONT_SIZE * 1.3)
        total_height = line_height * len(lines)
        
        img = Image.new('RGBA', (W, total_height + 40), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        y = 0
        for line in lines:
            clean_line = self.clean_text(line)
            parts = []
            buffer = ""; is_highlight = False
            
            for char in clean_line:
                if char == '*':
                    if buffer: parts.append((buffer, is_highlight))
                    buffer = ""; is_highlight = not is_highlight
                else: buffer += char
            if buffer: parts.append((buffer, is_highlight))

            try:
                total_w = sum([self.font.getlength(p[0]) for p in parts])
            except:
                total_w = self.font.getsize(clean_line)[0]

            current_x = (W - total_w) / 2

            for part_text, highlight in parts:
                fill_color = '#FFFF00' if highlight else 'white'
                # 외곽선 두께 (폰트 크기 비례)
                stroke_width = 6
                
                for dx in range(-stroke_width, stroke_width+1):
                    for dy in range(-stroke_width, stroke_width+1):
                        draw.text((current_x+dx, y+dy), part_text, font=self.font, fill='black')
                
                draw.text((current_x, y), part_text, font=self.font, fill=fill_color)
                
                try:
                    current_x += self.font.getlength(part_text)
                except:
                    current_x += self.font.getsize(part_text)[0]
            
            y += line_height

        return img

    def create_scene_clip(self, idx, scene_data, audio_path):
        if not os.path.exists(audio_path): return None
        audio = AudioFileClip(audio_path)
        duration = audio.duration + 0.5 

        visual_type = scene_data.get('visual_type', 'image')
        img_path = f"images/image_{idx}.png"
        vid_path = f"videos/video_{idx}.mp4"
        visual_clip = None

        if visual_type == 'video' and os.path.exists(vid_path):
            try:
                v = VideoFileClip(vid_path)
                if v.duration < duration: v = vfx.loop(v, duration=duration)
                else: v = v.subclip(0, duration)
                
                visual_clip = v.resize(height=H)
                if visual_clip.w < W: visual_clip = v.resize(width=W)
                visual_clip = visual_clip.crop(x1=visual_clip.w/2 - W/2, y1=0, width=W, height=H)
            except: visual_type = 'image'

        if visual_type == 'image' or visual_clip is None:
            if not os.path.exists(img_path):
                return ColorClip(size=(W, H), color=(0,0,0)).set_duration(duration).set_audio(audio)
            
            pil_img = Image.open(img_path).convert("RGB")
            iw, ih = pil_img.size
            target_ratio = W / H
            if iw / ih > target_ratio:
                new_w = int(ih * target_ratio)
                pil_img = pil_img.crop(((iw - new_w)//2, 0, (iw - new_w)//2 + new_w, ih))
            else:
                new_h = int(iw / target_ratio)
                pil_img = pil_img.crop((0, (ih - new_h)//2, iw, (ih - new_h)//2 + new_h))
            
            pil_img = pil_img.resize((W, H), Image.LANCZOS)
            clip = ImageClip(np.array(pil_img)).set_duration(duration)
            visual_clip = clip.resize(lambda t: 1 + 0.04 * t).set_position('center')

        narration = scene_data.get('narration', '')
        wrapper = textwrap.TextWrapper(width=35) 
        all_lines = wrapper.wrap(narration)
        
        pages = []
        for i in range(0, len(all_lines), 2):
            chunk = " ".join(all_lines[i:i+2])
            pages.append(chunk)

        if not pages: pages = [""]

        total_chars = len(narration.replace(" ", "")) if narration else 1
        overlays = []
        current_start = 0
        actual_audio_dur = audio.duration 

        for i, page_text in enumerate(pages):
            page_chars = len(page_text.replace(" ", ""))
            if i < len(pages) - 1:
                if total_chars > 0:
                    page_duration = (page_chars / total_chars) * actual_audio_dur
                else:
                    page_duration = actual_audio_dur / len(pages)
            else:
                page_duration = max(0, actual_audio_dur - current_start)

            sub_img = self.create_subtitle_image(page_text)
            sub_clip = ImageClip(np.array(sub_img))
            sub_clip = sub_clip.set_start(current_start).set_duration(page_duration)
            sub_clip = sub_clip.set_position(('center', SUBTITLE_Y))
            overlays.append(sub_clip)
            current_start += page_duration

        final_clip = CompositeVideoClip([visual_clip] + overlays, size=(W, H))
        final_clip = final_clip.set_audio(audio)
        return final_clip

    def make_video(self, data):
        print(f"🎬 [Editor] Assembling Long-Form Video...")
        scenes = data['script']['scenes']
        clips = []
        
        if os.path.exists("audio/intro.mp3"):
            intro_scene = {"visual_type": "image", "narration": data.get("intro_narration", "")}
            if os.path.exists("videos/video_1.mp4"): intro_scene["visual_type"] = "video"
            intro_clip = self.create_scene_clip(1, intro_scene, "audio/intro.mp3")
            if intro_clip: clips.append(intro_clip)

        for i, scene in enumerate(scenes):
            idx = i + 1
            audio_path = f"audio/audio_{idx}.mp3"
            clip = self.create_scene_clip(idx, scene, audio_path)
            if clip:
                clips.append(clip)
                print(f"   ✅ Processed Scene {idx}/{len(scenes)}")

        if os.path.exists("audio/outro.mp3"):
            outro_scene = {"visual_type": "image", "narration": data.get("outro_narration", "")}
            last_idx = len(scenes)
            if os.path.exists(f"videos/video_{last_idx}.mp4"): 
                outro_scene["visual_type"] = "video"
            outro_clip = self.create_scene_clip(last_idx, outro_scene, "audio/outro.mp3")
            if outro_clip: clips.append(outro_clip)

        if not clips: return None

        final_video = concatenate_videoclips(clips, method="compose")
        
        if os.path.exists("assets/bgm.mp3"):
            from moviepy.audio.fx import volumex
            bgm = AudioFileClip("assets/bgm.mp3").loop(duration=final_video.duration)
            bgm = bgm.fx(volumex, 0.1)
            final_audio = CompositeAudioClip([bgm, final_video.audio])
            final_video = final_video.set_audio(final_audio)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_filename = f"results/longform_{timestamp}.mp4"
        
        print(f"🚀 Rendering Final Video: {output_filename}")
        final_video.write_videofile(
            output_filename, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac", 
            bitrate="8000k", 
            preset="medium"
        )
        return output_filename