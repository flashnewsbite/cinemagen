import os
from moviepy.editor import *
from PIL import Image, ImageFont, ImageDraw
import numpy as np

# 한글 폰트 경로 (윈도우 기준)
FONT_KO = "C:/Windows/Fonts/malgunbd.ttf"

class Editor:
    def __init__(self):
        os.makedirs("results", exist_ok=True)

    def create_subtitle(self, text, duration):
        """노란색 자막 생성"""
        w, h = 720, 1280
        img = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        try: font = ImageFont.truetype(FONT_KO, 45)
        except: font = ImageFont.load_default()
        
        # 텍스트 중앙 하단 정렬
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) / 2
        y = 950 # 하단 위치
        
        # 외곽선
        for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            draw.text((x+dx, y+dy), text, font=font, fill='black')
        draw.text((x, y), text, font=font, fill='#FFD700') # Gold color
        
        return ImageClip(np.array(img)).set_duration(duration)

    def process_special_clip(self, video_path, duration):
        """Intro/Outro 로직: 영상이 짧으면 마지막 프레임 Freeze"""
        try:
            base = VideoFileClip(video_path).without_audio().resize(width=720)
            if duration > base.duration:
                freeze_time = duration - base.duration
                last_frame = base.to_ImageClip(t=base.duration - 0.01).set_duration(freeze_time)
                return concatenate_videoclips([base, last_frame])
            return base.subclip(0, duration)
        except:
            # 파일 없거나 에러시 블랙 스크린
            return ColorClip((720, 1280), color=(0,0,0)).set_duration(duration)

    def make_shorts(self, scenes):
        print("🎬 [Editor] 영상 편집 시작...")
        clips = []
        
        # 1. Intro
        if scenes:
            # 첫 씬의 오디오 길이에 맞춰 Intro 영상 조절 (Intro가 Scene 1 역할)
            # 혹은 별도 Intro 후 Scene 1 시작? -> 여기선 Intro를 Scene 1 배경으로 사용하거나
            # 사용자 요청: "Intro/Outro 영상을 따로 만들어 놓을거야"
            # 보통 Intro는 0번으로 따로 붙이는게 자연스러움.
            if os.path.exists("assets/intro.mp4"):
                 # Intro는 나레이션 없이 그냥 2-3초 붙이기
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
            
            # 이미지
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
        output_path = "results/final_shorts.mp4"
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"✨ 영상 생성 완료: {output_path}")