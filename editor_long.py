import os
import re
from datetime import datetime  # [수정 1] datetime 모듈 추가
from PIL import Image, ImageFont, ImageDraw
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
import moviepy.video.fx.all as vfx # [수정 2] vfx 명시적 임포트
import numpy as np
import textwrap

# [설정] 폰트 경로 (Windows 기준) - 없으면 기본 폰트 사용
# Roboto-Bold.ttf 파일을 프로젝트 폴더에 넣어주세요
FONT_PATH = "Roboto-Bold.ttf" 

# [설정] 레이아웃 (1920x1080 기준)
W, H = 1920, 1080
SUBTITLE_Y = 900  # 자막 위치 (하단)
FONT_SIZE = 65    # 자막 크기

class EditorLong:
    def __init__(self):
        os.makedirs("results", exist_ok=True)
        try:
            self.font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        except:
            print("⚠️ Custom font not found. Using default.")
            self.font = ImageFont.load_default()

    def clean_text(self, text):
        if not text: return ""
        # 특수문자 제거하되, 강조 표시(*)는 남김
        pattern = r'[^a-zA-Z0-9\s.,?!:;\'"*\-()\[\]%가-힣]'
        return re.sub(pattern, '', text).strip()

    def create_subtitle_image(self, text, width=1600):
        """
        투명 배경에 자막을 그리는 함수 (하이라이트 포함)
        """
        # 1. 텍스트 줄바꿈 (화면 너비에 맞게)
        wrapper = textwrap.TextWrapper(width=50) # 약 50자 마다 줄바꿈
        lines = wrapper.wrap(text)
        if len(lines) > 2: lines = lines[:2] # 최대 2줄 제한

        # 2. 캔버스 준비
        line_height = int(FONT_SIZE * 1.4)
        total_height = line_height * len(lines)
        img = Image.new('RGBA', (W, total_height + 20), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 3. 텍스트 그리기 (중앙 정렬)
        y = 0
        for line in lines:
            # *별표* 파싱 (하이라이트 로직)
            clean_line = self.clean_text(line)
            parts = []
            buffer = ""; is_highlight = False
            for char in clean_line:
                if char == '*':
                    if buffer: parts.append((buffer, is_highlight))
                    buffer = ""; is_highlight = not is_highlight
                else: buffer += char
            if buffer: parts.append((buffer, is_highlight))

            # 라인 전체 너비 계산 (중앙 정렬용)
            total_w = sum([self.font.getlength(p[0]) for p in parts])
            current_x = (W - total_w) / 2

            # 검은색 외곽선(Stroke) + 텍스트 그리기
            for part_text, highlight in parts:
                fill_color = '#FFFF00' if highlight else 'white'
                # 외곽선 (가독성 확보)
                stroke_width = 4
                for dx in range(-stroke_width, stroke_width+1):
                    for dy in range(-stroke_width, stroke_width+1):
                        draw.text((current_x+dx, y+dy), part_text, font=self.font, fill='black')
                # 본문
                draw.text((current_x, y), part_text, font=self.font, fill=fill_color)
                current_x += self.font.getlength(part_text)
            
            y += line_height

        return img

    def create_scene_clip(self, idx, scene_data, audio_path):
        """
        하나의 씬(오디오+비주얼+자막)을 만드는 함수
        """
        # 1. 오디오 로드
        if not os.path.exists(audio_path): return None
        audio = AudioFileClip(audio_path)
        duration = audio.duration + 0.5 # 0.5초 여유

        # 2. 비주얼 로드 (이미지 vs 비디오)
        visual_type = scene_data.get('visual_type', 'image')
        img_path = f"images/image_{idx}.png"
        vid_path = f"videos/video_{idx}.mp4"
        
        visual_clip = None

        # [Case A] 비디오 (Pexels)
        if visual_type == 'video' and os.path.exists(vid_path):
            try:
                # 비디오 로드
                v = VideoFileClip(vid_path)
                
                # [수정 2] vfx 모듈을 사용하여 루프 처리
                if v.duration < duration:
                    v = vfx.loop(v, duration=duration)
                else:
                    v = v.subclip(0, duration)
                
                # 1920x1080에 맞춰 Crop & Resize
                visual_clip = v.resize(height=H) # 높이 기준 맞춤
                if visual_clip.w < W: 
                    visual_clip = v.resize(width=W) # 너비 기준 맞춤
                visual_clip = visual_clip.crop(x1=visual_clip.w/2 - W/2, y1=0, width=W, height=H)
                
            except Exception as e:
                print(f"      ⚠️ Video Load Error: {e}. Fallback to Image.")
                visual_type = 'image'

        # [Case B] 이미지 (Zoom Effect)
        if visual_type == 'image' or visual_clip is None:
            if not os.path.exists(img_path):
                # 이미지도 없으면 블랙 스크린
                return ColorClip(size=(W, H), color=(0,0,0)).set_duration(duration).set_audio(audio)
            
            # 이미지 로드
            pil_img = Image.open(img_path).convert("RGB")
            
            # 1920x1080 비율(16:9)로 크롭
            iw, ih = pil_img.size
            target_ratio = W / H
            if iw / ih > target_ratio: # 이미지가 더 넓음 -> 양옆 자름
                new_w = int(ih * target_ratio)
                pil_img = pil_img.crop(((iw - new_w)//2, 0, (iw - new_w)//2 + new_w, ih))
            else: # 이미지가 더 길쭉함 -> 위아래 자름
                new_h = int(iw / target_ratio)
                pil_img = pil_img.crop((0, (ih - new_h)//2, iw, (ih - new_h)//2 + new_h))
            
            pil_img = pil_img.resize((W, H), Image.LANCZOS)
            
            # Zoom Effect (Ken Burns)
            clip = ImageClip(np.array(pil_img)).set_duration(duration)
            visual_clip = clip.resize(lambda t: 1 + 0.04 * t)  # 4% 줌인
            # 중앙 정렬 (줌인 시 위치 보정)
            visual_clip = visual_clip.set_position('center')

        # 3. 자막 오버레이
        narration = scene_data.get('narration', '')
        sub_img = self.create_subtitle_image(narration)
        sub_clip = ImageClip(np.array(sub_img)).set_duration(duration)
        sub_clip = sub_clip.set_position(('center', SUBTITLE_Y))

        # 4. 최종 합성 (비주얼 + 자막)
        final_clip = CompositeVideoClip([visual_clip, sub_clip], size=(W, H))
        final_clip = final_clip.set_audio(audio)
        
        return final_clip

    def make_video(self, data):
        print(f"🎬 [Editor] Assembling Long-Form Video...")
        scenes = data['script']['scenes']
        clips = []
        
        # 1. Intro (있으면 처리)
        if os.path.exists("audio/intro.mp3"):
            # 인트로는 첫 번째 이미지나 비디오를 배경으로 사용
            intro_scene = {"visual_type": "image", "narration": data.get("intro_narration", "")}
            # 첫 번째 씬의 리소스를 빌려옴
            if os.path.exists("videos/video_1.mp4"): intro_scene["visual_type"] = "video"
            
            intro_clip = self.create_scene_clip(1, intro_scene, "audio/intro.mp3")
            if intro_clip: clips.append(intro_clip)

        # 2. Main Scenes
        for i, scene in enumerate(scenes):
            idx = i + 1
            audio_path = f"audio/audio_{idx}.mp3"
            clip = self.create_scene_clip(idx, scene, audio_path)
            if clip:
                clips.append(clip)
                print(f"   ✅ Processed Scene {idx}/{len(scenes)}")

        # 3. Outro (있으면 처리)
        if os.path.exists("audio/outro.mp3"):
            outro_scene = {"visual_type": "image", "narration": data.get("outro_narration", "")}
            # 마지막 씬 리소스 활용
            last_idx = len(scenes)
            if os.path.exists(f"videos/video_{last_idx}.mp4"): 
                outro_scene["visual_type"] = "video"
            
            outro_clip = self.create_scene_clip(last_idx, outro_scene, "audio/outro.mp3")
            if outro_clip: clips.append(outro_clip)

        if not clips:
            print("❌ No clips created.")
            return None

        # 4. 렌더링
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 배경음악 (옵션: assets/bgm.mp3가 있다면 추가)
        if os.path.exists("assets/bgm.mp3"):
            from moviepy.audio.fx import volumex
            bgm = AudioFileClip("assets/bgm.mp3").loop(duration=final_video.duration)
            bgm = bgm.fx(volumex, 0.1) # 볼륨 10%
            final_audio = CompositeAudioClip([bgm, final_video.audio])
            final_video = final_video.set_audio(final_audio)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_filename = f"results/longform_{timestamp}.mp4"
        
        print(f"🚀 Rendering Final Video: {output_filename}")
        # YouTube 권장: 1080p, 30fps, High Bitrate
        final_video.write_videofile(
            output_filename, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac", 
            bitrate="8000k", 
            preset="medium"
        )
        
        return output_filename