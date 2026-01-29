import os
import re
from datetime import datetime
from PIL import Image, ImageFont, ImageDraw
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
import moviepy.video.fx.all as vfx
import numpy as np
import textwrap

# [설정] 레이아웃
W, H = 1920, 1080
SUBTITLE_Y = 750  

# [수정 1] 폰트 크기 축소 (95 -> 80)
FONT_SIZE = 80    

class EditorLong:
    def __init__(self):
        os.makedirs("results", exist_ok=True)
        self.font = self.load_font()

    def load_font(self):
        font_candidates = [
            ("assets/Roboto-Bold.ttf", "Asset Roboto"),     
            ("Roboto-Bold.ttf", "Root Roboto"),             
            ("C:/Windows/Fonts/arialbd.ttf", "Windows Arial"), 
            ("C:/Windows/Fonts/malgunbd.ttf", "Windows Malgun") 
        ]
        for path, name in font_candidates:
            if os.path.exists(path):
                try: return ImageFont.truetype(path, FONT_SIZE)
                except: continue
        return ImageFont.load_default()

    def clean_text(self, text):
        if not text: return ""
        pattern = r'[^a-zA-Z0-9\s.,?!:;\'"*\-()\[\]%가-힣]'
        return re.sub(pattern, '', text).strip()

    def create_subtitle_image_from_lines(self, lines):
        # [수정 2] 줄 간격(Gap) 자동 조정
        # 폰트가 작아졌으므로 1.4배수로 설정하여 가독성 확보 (80 * 1.4 = 112px 높이)
        line_height = int(FONT_SIZE * 1.4) 
        total_height = line_height * len(lines)
        
        # 캔버스 높이 여유있게
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

            try: total_w = sum([self.font.getlength(p[0]) for p in parts])
            except: total_w = self.font.getsize(clean_line)[0]
            current_x = (W - total_w) / 2

            for part_text, highlight in parts:
                fill_color = '#FFFF00' if highlight else 'white'
                
                # [수정 3] 외곽선 두께 조정 (7 -> 6)
                # 글씨가 작아졌으니 테두리도 살짝 얇게 해서 뭉침 방지
                stroke_width = 6 
                
                for dx in range(-stroke_width, stroke_width+1):
                    for dy in range(-stroke_width, stroke_width+1):
                        draw.text((current_x+dx, y+dy), part_text, font=self.font, fill='black')
                draw.text((current_x, y), part_text, font=self.font, fill=fill_color)
                try: current_x += self.font.getlength(part_text)
                except: current_x += self.font.getsize(part_text)[0]
            y += line_height
        return img

    def create_scene_clip(self, idx, scene_data, audio_path, override_video_path=None, loop_video=True):
        if not os.path.exists(audio_path): return None
        audio = AudioFileClip(audio_path)
        duration = audio.duration + 0.5 

        visual_type = scene_data.get('visual_type', 'image')
        img_path = f"images/image_{idx}.png"
        
        if override_video_path and os.path.exists(override_video_path):
            vid_path = override_video_path
            visual_type = 'video'
        else:
            vid_path = f"videos/video_{idx}.mp4"

        visual_clip = None

        if visual_type == 'video' and os.path.exists(vid_path):
            try:
                v = VideoFileClip(vid_path)
                if loop_video:
                    if v.duration < duration: v = vfx.loop(v, duration=duration)
                    else: v = v.subclip(0, duration)
                else:
                    # Intro/Outro freezing logic
                    if v.duration < duration:
                        freeze_duration = duration - v.duration
                        if freeze_duration > 0:
                            last_frame = v.get_frame(max(0, v.duration - 0.1))
                            freeze_clip = ImageClip(last_frame).set_duration(freeze_duration)
                            v = concatenate_videoclips([v, freeze_clip])
                    else:
                        v = v.subclip(0, duration)

                visual_clip = v.resize(height=H)
                if visual_clip.w < W: visual_clip = v.resize(width=W)
                visual_clip = visual_clip.crop(x1=visual_clip.w/2 - W/2, y1=0, width=W, height=H)
            except Exception as e:
                print(f"⚠️ Video Error ({vid_path}): {e}. Fallback to Image.")
                visual_type = 'image'

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
        if not narration: return visual_clip.set_audio(audio)

        wrapper = textwrap.TextWrapper(width=30) 
        all_lines = wrapper.wrap(narration)
        
        pages = []
        for i in range(0, len(all_lines), 2):
            pages.append(all_lines[i:i+2]) 

        if not pages: return visual_clip.set_audio(audio)

        total_chars = len(narration.replace(" ", ""))
        if total_chars == 0: total_chars = 1
        
        overlays = []
        current_start = 0
        actual_audio_dur = audio.duration 

        for i, page_lines in enumerate(pages):
            chunk_text = "".join(page_lines)
            page_chars = len(chunk_text.replace(" ", ""))
            
            if i < len(pages) - 1:
                ratio = page_chars / total_chars
                page_duration = ratio * actual_audio_dur
                if page_duration < 2.0: page_duration = 2.0
            else:
                page_duration = max(0, duration - current_start)

            if current_start + page_duration > duration:
                page_duration = duration - current_start

            sub_img = self.create_subtitle_image_from_lines(page_lines)
            sub_clip = ImageClip(np.array(sub_img))
            
            sub_clip = sub_clip.set_start(current_start).set_duration(page_duration)
            sub_clip = sub_clip.set_position(('center', SUBTITLE_Y))
            
            overlays.append(sub_clip)
            current_start += page_duration
            
            if current_start >= duration: break

        final_clip = CompositeVideoClip([visual_clip] + overlays, size=(W, H))
        final_clip = final_clip.set_audio(audio)
        return final_clip

    def make_video(self, data):
        print(f"🎬 [Editor] Assembling Long-Form Video...")
        scenes = data['script']['scenes']
        clips = []
        
        # 1. Intro
        if os.path.exists("audio/intro.mp3"):
            print("   🔹 Processing Intro...")
            intro_text = data.get("intro_narration", "")
            intro_scene = {"visual_type": "image", "narration": intro_text}
            
            intro_vid = None
            if os.path.exists("assets/intro_long.mp4"):
                intro_vid = "assets/intro_long.mp4"
                print("      ✅ Using 'intro_long.mp4'")
            elif os.path.exists("assets/intro.mp4"):
                intro_vid = "assets/intro.mp4"

            intro_clip = self.create_scene_clip(0, intro_scene, "audio/intro.mp3", 
                                                override_video_path=intro_vid, 
                                                loop_video=False)
            if intro_clip: clips.append(intro_clip)

        # 2. Main Scenes
        for i, scene in enumerate(scenes):
            idx = i + 1
            audio_path = f"audio/audio_{idx}.mp3"
            clip = self.create_scene_clip(idx, scene, audio_path, loop_video=True)
            if clip:
                clips.append(clip)
                print(f"   ✅ Processed Scene {idx}/{len(scenes)}")

        # 3. Outro
        if os.path.exists("audio/outro.mp3"):
            print("   🔹 Processing Outro...")
            outro_text = data.get("outro_narration", "")
            outro_scene = {"visual_type": "image", "narration": outro_text}
            
            outro_vid = None
            if os.path.exists("assets/outro_long.mp4"):
                outro_vid = "assets/outro_long.mp4"
                print("      ✅ Using 'outro_long.mp4'")
            elif os.path.exists("assets/outro.mp4"):
                outro_vid = "assets/outro.mp4"

            outro_clip = self.create_scene_clip(len(scenes)+1, outro_scene, "audio/outro.mp3", 
                                                override_video_path=outro_vid, 
                                                loop_video=False)
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