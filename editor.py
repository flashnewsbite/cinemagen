import os
# [핵심 수정] Pillow 10.0+ 호환성 패치
# ANTIALIAS가 없다는 에러를 방지하기 위해 최신 기술(LANCZOS)로 연결해줍니다.
from PIL import Image, ImageFont, ImageDraw
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import *
import numpy as np

# 영어 전용 폰트 (Arial Bold)
FONT_EN = "C:/Windows/Fonts/arialbd.ttf"

class Editor:
    def __init__(self):
        os.makedirs("results", exist_ok=True)

    def create_subtitle(self, text, duration):
        """Create English Subtitles (Yellow)"""
        w, h = 720, 1280
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # 폰트 로드
        try: font = ImageFont.truetype(FONT_EN, 50) 
        except: font = ImageFont.load_default()
        
        # 텍스트 중앙 하단 정렬
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) / 2
        y = 950 # 하단 위치
        
        # 외곽선 (검정)
        for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            draw.text((x+dx, y+dy), text, font=font, fill='black')
        
        # 본문 (노란색)
        draw.text((x, y), text, font=font, fill='#FFD700')
        
        return ImageClip(np.array(img)).set_duration(duration)

    def make_shorts(self, scenes):
        print("🎬 [Editor] Editing Video...")
        clips = []
        
        # 1. Intro
        if os.path.exists("assets/intro.mp4"):
             # 오디오 없이 영상만 사용 (혹은 필요시 오디오 포함)
             intro_clip = VideoFileClip("assets/intro.mp4").resize(width=720)
             clips.append(intro_clip)

        # 2. Main Content
        for i, scene in enumerate(scenes):
            idx = i + 1
            img_path = f"images/image_{idx}.png"
            aud_path = f"audio/audio_{idx}.mp3"
            
            if not os.path.exists(aud_path): continue
            
            audio = AudioFileClip(aud_path)
            duration = audio.duration
            
            # 이미지 (가로 720으로 리사이즈 + 중앙 정렬)
            if os.path.exists(img_path):
                visual = ImageClip(img_path).set_duration(duration).resize(width=720).set_position("center")
            else:
                visual = ColorClip((720, 1280), color=(0,0,0)).set_duration(duration)
            
            # 자막
            sub = self.create_subtitle(scene['narration'], duration)
            
            # 합성
            clip = CompositeVideoClip([visual, sub], size=(720, 1280)).set_audio(audio)
            clips.append(clip)

        # 3. Outro
        if os.path.exists("assets/outro.mp4"):
            outro_clip = VideoFileClip("assets/outro.mp4").resize(width=720)
            clips.append(outro_clip)

        # 최종 렌더링
        final = concatenate_videoclips(clips, method="compose")
        output_path = "results/final_shorts_english.mp4"
        
        # fps=24로 설정하여 렌더링 속도 최적화
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"✨ Video Created: {output_path}")