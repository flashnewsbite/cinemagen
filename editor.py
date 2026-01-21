import os
from PIL import Image, ImageFont, ImageDraw
# PIL.Image.ANTIALIAS가 최신 버전에서 삭제되어 LANCZOS로 대체
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
from moviepy.editor import *
import numpy as np
import textwrap

# 폰트 설정 (Windows 기준 Arial Bold)
# * 주의: Mac이나 Linux 사용 시 시스템에 맞는 폰트 경로로 변경해야 합니다.
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"

class Editor:
    def __init__(self):
        os.makedirs("results", exist_ok=True)

    def draw_text_with_highlight(self, draw, text_lines, position, font, max_width, align='center', line_spacing=1.2, highlight_style='text'):
        """
        text_lines: 이미 분할된 줄(list of strings)을 직접 받아 출력
        position: (x, y) 좌표. y는 텍스트 블록의 수직 중앙 지점
        """
        x, start_y = position
        
        # 폰트 높이 및 라인 간격 계산
        try:
            bbox_sample = font.getbbox("Ay")
            font_ascender = bbox_sample[1]
            font_descender = bbox_sample[3]
        except:
            # 구버전 PIL 대응
            font_ascender = 0
            font_descender = 20

        font_height = font_descender - font_ascender
        line_height = int(font_height * line_spacing)
        
        # 전체 텍스트 블록의 높이를 계산하여 수직 중앙 정렬 보정
        total_text_height = line_height * len(text_lines)
        current_y = start_y - (total_text_height // 2)

        for line in text_lines:
            # 1. 텍스트 파싱 (*하이라이트* 분리)
            parts = []
            buffer = ""; is_highlight = False
            for char in line:
                if char == '*':
                    if buffer: parts.append((buffer, is_highlight))
                    buffer = ""; is_highlight = not is_highlight
                else: buffer += char
            if buffer: parts.append((buffer, is_highlight))

            # 2. 수평 중앙 정렬을 위한 X 좌표 계산 (W=720 기준)
            total_w = sum([font.getlength(p[0]) for p in parts])
            current_x = (max_width - total_w) / 2 if align == 'center' else x

            # 3. 각 부분 그리기
            for part_text, highlight in parts:
                part_w = font.getlength(part_text)
                
                if highlight and highlight_style == 'box':
                    # 타이틀용 노란 박스 하이라이트
                    padding_x = 8; padding_y = 4
                    box_x1 = current_x - padding_x
                    box_y1 = current_y + font_ascender - padding_y
                    box_x2 = current_x + part_w + padding_x
                    box_y2 = current_y + font_descender + padding_y
                    draw.rectangle([(box_x1, box_y1), (box_x2, box_y2)], fill='#FFD700')
                    draw.text((current_x, current_y), part_text, font=font, fill='black')
                    
                elif highlight and highlight_style == 'text':
                    # 자막용 노란 글씨 하이라이트 (테두리 포함)
                    for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
                        draw.text((current_x+dx, current_y+dy), part_text, font=font, fill='black')
                    draw.text((current_x, current_y), part_text, font=font, fill='#FFFF00')
                    
                else:
                    # 일반 흰색 글씨 (테두리 포함)
                    for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
                        draw.text((current_x+dx, current_y+dy), part_text, font=font, fill='black')
                    draw.text((current_x, current_y), part_text, font=font, fill='white')

                current_x += part_w
            
            current_y += line_height

    def create_layout_clip(self, narration_lines, img_path, duration, video_title):
        W, H = 720, 1280
        canvas = Image.new('RGB', (W, H), (0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        try: 
            font_title = ImageFont.truetype(FONT_BOLD, 45)
            font_sub = ImageFont.truetype(FONT_BOLD, 38)
        except: 
            # 폰트 로드 실패 시 기본 폰트 사용 (경고 메시지 출력 권장)
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        # 1. 이미지 배치 (이미지 높이와 Y좌표를 먼저 구해야 타이틀 위치를 잡을 수 있음)
        img_y = 0
        img_final_h = 0
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
            
            # 해상도에 맞춰 리사이즈
            img = img.resize((W, int(W/target_ratio)), Image.LANCZOS)
            img_final_h = img.size[1]
            
            # 이미지를 화면 수직 중앙에 배치
            img_y = (H - img_final_h) // 2
            canvas.paste(img, (0, img_y))

        # 2. 상단 타이틀 배치 (수정됨: 상단 여백의 정중앙)
        # 0부터 img_y(이미지 시작점) 사이의 중간 지점 계산
        if img_y > 0:
            title_center_y = img_y // 2
        else:
            title_center_y = 130 # 이미지가 꽉 찼거나 없을 경우 기본값

        title_lines = textwrap.wrap(video_title, width=25)
        self.draw_text_with_highlight(
            draw, 
            title_lines, 
            (W//2, title_center_y), 
            font_title, 
            W, 
            'center', 
            highlight_style='box' # 타이틀은 노란 박스 스타일
        )
        
        # 3. 로고 배치
        logo_h = 0
        if os.path.exists("assets/logo.png"):
            logo = Image.open("assets/logo.png").convert("RGBA")
            logo.thumbnail((150, 150), Image.LANCZOS)
            logo_h = logo.size[1]
            logo_y = H - logo_h - 30
            canvas.paste(logo, ((W - logo.size[0]) // 2, logo_y), logo)

        # 4. 하단 자막 배치 (이미지 끝 ~ 로고 시작 사이의 정중앙)
        image_bottom = img_y + img_final_h
        logo_top = H - logo_h - 30 if logo_h > 0 else H - 30
        subtitle_center_y = (image_bottom + logo_top) // 2
        
        self.draw_text_with_highlight(
            draw, 
            narration_lines, 
            (W//2, subtitle_center_y), 
            font_sub, 
            W, 
            'center', 
            highlight_style='text' # 자막은 노란 글씨 스타일
        )

        return ImageClip(np.array(canvas)).set_duration(duration)

    def process_special_clip(self, video_path, audio_path):
        # 1. 비디오 파일 존재 여부 확인
        if not os.path.exists(video_path):
            print(f"   ⚠️ [Skip] Special Clip Video missing: {video_path}")
            return None
            
        video = VideoFileClip(video_path).resize(width=720)
        
        # 2. 오디오 파일 존재 여부 확인
        if os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                # 오디오가 비디오보다 길면 비디오 마지막 화면을 멈춰서(Freeze) 길이를 맞춤
                if audio.duration > video.duration:
                    # [수정] 'end' 대신 정확한 시간값(float) 사용으로 에러 해결
                    last_frame_time = max(0, video.duration - 0.1)
                    freeze = video.to_ImageClip(t=last_frame_time).set_duration(audio.duration - video.duration)
                    video = concatenate_videoclips([video, freeze])
                
                return video.set_audio(audio)
            except Exception as e:
                print(f"   ⚠️ [Error] Failed to load audio {audio_path}: {e}")
                return video 
        else:
            print(f"   ⚠️ [Info] Audio missing for {video_path}. Using silent video.")
            return video

    def make_shorts(self, data, category="world"):
        print(f"🎬 [Editor] Editing Video with Balanced Layout (Category: {category})...")
        scenes = data['script']['scenes']
        video_title = data.get('title', "News Update")
        clips = []
        
        # Intro
        intro = self.process_special_clip("assets/intro.mp4", "audio/intro.mp3")
        if intro: clips.append(intro)

        for i, scene in enumerate(scenes):
            idx = i + 1
            aud_path = f"audio/audio_{idx}.mp3"
            img_path = f"images/image_{idx}.png"
            if not os.path.exists(aud_path): continue
            
            full_audio = AudioFileClip(aud_path)
            full_duration = full_audio.duration
            
            narration_text = scene.get('narration', "")
            # 전체 나레이션을 줄 단위로 분리 (30자 기준)
            all_lines = textwrap.wrap(narration_text, width=30)
            total_lines = len(all_lines)
            
            # --- 지능형 자막 분할 (Balanced Pagination) ---
            if total_lines <= 4:
                pages = [all_lines]
            else:
                # 필요한 페이지 수 계산
                num_pages = (total_lines + 3) // 4 
                # 한 페이지당 기본 줄 수
                base_lines = total_lines // num_pages
                # 남는 줄 수 (앞 페이지부터 +1씩 배분)
                extra_lines = total_lines % num_pages
                
                pages = []
                current_start = 0
                for p in range(num_pages):
                    count = base_lines + (1 if p < extra_lines else 0)
                    pages.append(all_lines[current_start : current_start + count])
                    current_start += count
            # ---------------------------------------------
            
            num_pages = len(pages)
            duration_per_page = full_duration / num_pages
            
            for p_idx, page_lines in enumerate(pages):
                start_t = p_idx * duration_per_page
                end_t = min((p_idx + 1) * duration_per_page, full_duration)
                
                # 오디오 클립 자르기
                sub_audio = full_audio.subclip(start_t, end_t)
                
                # 클립 생성 (동일 이미지 사용)
                clip = self.create_layout_clip(page_lines, img_path, sub_audio.duration, video_title)
                clips.append(clip.set_audio(sub_audio))

        # Outro
        outro = self.process_special_clip("assets/outro.mp4", "audio/outro.mp3")
        if outro: clips.append(outro)

        # 최종 병합
        final = concatenate_videoclips(clips, method="compose")
        
        suffix_map = {"world": "USWORLD", "tech": "TECH", "finance": "FINANCE", "art": "ARTS", "sports": "SPORTS", "ent": "ENT"}
        suffix = suffix_map.get(category, "USWORLD")
        output_filename = f"results/final_shorts_{suffix}.mp4"
        
        final.write_videofile(output_filename, fps=30, codec="libx264", audio_codec="aac", bitrate="5000k", preset="medium")
        print(f"✨ Video Created: {output_filename}")