import os
from PIL import Image, ImageFont, ImageDraw
# PIL.Image.ANTIALIAS가 최신 버전에서 삭제되어 LANCZOS로 대체
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
import numpy as np
import textwrap

# 폰트 설정 (Windows 기준 Arial Bold)
# * 중요: 이 경로에 폰트 파일이 없으면 스타일이 적용되지 않고 기본 폰트로 나옵니다.
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

class Editor:
    def __init__(self):
        os.makedirs("results", exist_ok=True)

    # [핵심 수정] 텍스트 그리기 함수 (중앙 정렬 버그 수정됨)
    def draw_text_with_highlight(self, draw, text, position, font, max_width, align='center', line_spacing=1.2, highlight_style='text'):
        """
        highlight_style: 'text' (글자색 변경, 자막용) 또는 'box' (배경 박스, 타이틀용)
        """
        x, start_y = position
        if not isinstance(text, str): text = str(text)
            
        # 텍스트 줄바꿈 (너비에 맞춰 자동 줄바꿈, 최대 4줄)
        lines = textwrap.wrap(text, width=30)
        if len(lines) > 4: lines = lines[:4]
        
        # 폰트 높이 계산
        bbox_sample = font.getbbox("Ay")
        font_ascender = bbox_sample[1]
        font_descender = bbox_sample[3]
        font_height = font_descender - font_ascender
        line_height = int(font_height * line_spacing)
        
        # 텍스트 전체 블록의 수직 중앙을 맞추기 위한 시작 Y 좌표
        total_text_height = line_height * len(lines)
        current_y = start_y - (total_text_height // 2)

        for line in lines:
            # 1. 텍스트 파싱 (*키워드* 분리)
            parts = []
            buffer = ""; is_highlight = False
            for char in line:
                if char == '*':
                    if buffer: parts.append((buffer, is_highlight))
                    buffer = ""; is_highlight = not is_highlight
                else: buffer += char
            if buffer: parts.append((buffer, is_highlight))

            # 2. 수평 중앙 정렬을 위한 X 좌표 계산
            total_w = sum([font.getlength(p[0]) for p in parts])
            current_x = (max_width - total_w) / 2 if align == 'center' else x

            # 3. 글자 그리기
            for part_text, highlight in parts:
                part_w = font.getlength(part_text)
                
                if highlight and highlight_style == 'box':
                    # [스타일 1] 타이틀용 박스 하이라이트 (WriterAgent가 *키워드*로 넘겨주면 적용됨)
                    padding_x = 8; padding_y = 4
                    box_x1 = current_x - padding_x
                    box_y1 = current_y + font_ascender - padding_y
                    box_x2 = current_x + part_w + padding_x
                    box_y2 = current_y + font_descender + padding_y
                    
                    draw.rectangle([(box_x1, box_y1), (box_x2, box_y2)], fill='#FFD700') # 노란 박스
                    draw.text((current_x, current_y), part_text, font=font, fill='black') # 검은 글씨
                    
                elif highlight and highlight_style == 'text':
                    # [스타일 2] 자막용 글자색 하이라이트 (검은 테두리 + 노란 글씨)
                    for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
                        draw.text((current_x+dx, current_y+dy), part_text, font=font, fill='black')
                    draw.text((current_x, current_y), part_text, font=font, fill='#FFFF00')
                    
                else:
                    # [기본] 일반 흰색 글씨 (검은 테두리 포함)
                    for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
                        draw.text((current_x+dx, current_y+dy), part_text, font=font, fill='black')
                    draw.text((current_x, current_y), part_text, font=font, fill='white')

                current_x += part_w
            
            current_y += line_height
            
        return current_y

    def create_layout_clip(self, scene_data, img_path, duration, video_title):
        W, H = 720, 1280
        canvas = Image.new('RGB', (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # 폰트 로드 (실패 시 기본 폰트 사용 알림)
        try: 
            font_title = ImageFont.truetype(FONT_BOLD, 45) # 타이틀: 더 크고 Bold
            font_sub = ImageFont.truetype(FONT_BOLD, 38)   # 자막: 조금 작고 Bold
        except: 
            print("⚠️ Warning: Custom font not found. Using default font (No Bold/Size effect).")
            font_title = ImageFont.load_default(); font_sub = ImageFont.load_default()

        # 1. 이미지 배치
        img_y = 0 # 이미지가 없을 경우를 대비한 초기값
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
            img_y = (H - img.size[1]) // 2
            canvas.paste(img, (0, img_y))

        # 2. 상단 타이틀 (중앙 정렬 & 박스 하이라이트)
        # [수정] Y 좌표 계산: 영상 맨 위(0)부터 이미지 시작(img_y) 사이의 정중앙
        title_y = img_y // 2 if img_y > 0 else 130 # 이미지가 없을 경우 기본값 130 유지
        
        self.draw_text_with_highlight(
            draw, video_title, (W//2, title_y), font_title, W, 'center', 
            line_spacing=1.2, highlight_style='box'
        )
        
        # 3. 로고 배치
        logo_h = 0
        if os.path.exists("assets/logo.png"):
            logo = Image.open("assets/logo.png").convert("RGBA")
            logo.thumbnail((150, 150), Image.LANCZOS)
            logo_h = logo.size[1]
            logo_y = H - logo_h - 30
            canvas.paste(logo, ((W - logo.size[0]) // 2, logo_y), logo)

        # 4. 하단 자막 (중앙 정렬 & 로고 회피 & 글자색 하이라이트)
        narration_text = ""
        if isinstance(scene_data, dict): narration_text = scene_data.get('narration', "")
        elif isinstance(scene_data, str): narration_text = scene_data
            
        # 자막 위치 계산: 이미지 끝과 로고 시작 사이의 정중앙
        image_bottom = img_y + img.size[1]
        logo_top = H - logo_h - 30 if logo_h > 0 else H - 30
        subtitle_center_y = (image_bottom + logo_top) // 2
        
        self.draw_text_with_highlight(
            draw, narration_text, (W//2, subtitle_center_y), font_sub, W, 'center', 
            line_spacing=1.3, highlight_style='text'
        )

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

    # [수정] category 파라미터 추가
    def make_shorts(self, data, category="world"):
        print(f"🎬 [Editor] Editing Video (Category: {category})...")
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
            # create_layout_clip 호출
            clip = self.create_layout_clip(scene, f"images/image_{idx}.png", audio.duration, video_title)
            clips.append(clip.set_audio(audio))

        outro = self.process_special_clip("assets/outro.mp4", "audio/outro.mp3")
        if outro: clips.append(outro)

        final = concatenate_videoclips(clips, method="compose")
        
        # [추가] 카테고리별 파일명 접미사 매핑
        suffix_map = {
            "world": "USWORLD",
            "tech": "TECH",
            "finance": "FINANCE",
            "art": "ARTS",
            "sports": "SPORTS",
            "ent": "ENT"
        }
        suffix = suffix_map.get(category, "USWORLD") # 기본값 USWORLD
        output_filename = f"results/final_shorts_{suffix}.mp4"
        
        final.write_videofile(output_filename, fps=30, codec="libx264", audio_codec="aac", bitrate="5000k", preset="medium")
        print(f"✨ Video Created: {output_filename}")