import json
import time
import google.generativeai as genai
from config import Config
import os
from datetime import date
import re

class WriterAgent:
    def generate_content(self, context, mode="shorts", source_type="news"):
        """
        mode: "shorts" or "long"
        source_type: "news" or "topic"
        """
        print(f"✍️ [Writer] Generating Script (Mode: {mode.upper()})...")
        
        today_str = date.today().strftime("%Y-%m-%d")

        # =================================================================
        # [NEW] LONG-FORM PROMPT (유튜브 롱폼용)
        # =================================================================
        if mode == "long":
            visual_guide = "Use 'image' type for factual events. Use 'video' type for cinematic backgrounds."
            if source_type == "topic":
                visual_guide = "Prioritize 'video' type (Pexels) for storytelling. Use 'image' only for specific data."

            prompt = f"""
            Role: Professional YouTube Documentary Creator.
            Date: {today_str}
            Format: Long-form YouTube Video (Target: 2-3 minutes).
            
            Task:
            1. Write a script based on [Input Context].
            2. Structure: Intro (Hook) -> Body (3-4 Key Points) -> Conclusion.
            3. **Visual Cues**: Decide whether to use a Stock Video ('video') or a News Image ('image') for each scene.
            4. **Narration**: Max 2 sentences per scene.

            [Input Context]
            {context}

            [⚠️ VISUAL RULES]
            - {visual_guide}
            - 'visual_prompt': Search query for Pexels(video) or Google(image). English only.

            [Output Format - JSON Only]
            {{
                "title": "YouTube Video Title",
                "description": "YouTube Description with hashtags...",
                "script": {{
                    "scenes": [
                        {{
                            "narration": "Narration text...",
                            "visual_type": "video", 
                            "visual_prompt": "cinematic view of..." 
                        }},
                        ... (Create enough scenes for 2+ mins)
                    ]
                }},
                "metadata": {{
                    "tags": ["tag1", "tag2"]
                }}
            }}
            """

        # =================================================================
        # [EXISTING] SHORTS PROMPT (기존 숏폼용 - SNS 포스팅 포함)
        # =================================================================
        else:
            prompt = f"""
            Role: Expert News Creator & Social Media Manager.
            Date: {today_str}
            
            Task: 
            1. Create a YouTube Shorts script based on [Input Context].
            2. Create optimized metadata.
            3. Generate engaging posts for X, Threads, Instagram, and TikTok.

            [Input Context]
            {context}

            [⚠️ TITLE RULES]
            1. VIRAL HOOK ONLY. Max 6-8 Words.
            2. NO generic words.
            
            [Highlighting Rules]
            - Wrap 1-2 key words per sentence in asterisks (*) for yellow highlighting.

            [Output Format - JSON Only]
            {{
                "title": "Viral Title",
                "intro_narration": "Intro...",
                "outro_narration": "Outro...",
                "script": {{
                    "scenes": [
                        {{ "narration": "Narration...", "image_prompt": "Visual..." }}
                    ]
                }},
                "metadata": {{
                    "youtube_title": "...", "youtube_description": "...", "hashtags": "...",
                    "x_post": "...", "instagram_post": "...", "tiktok_post": "...", "threads_post": "..."
                }}
            }}
            """

        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        max_attempts = len(Config.GEMINI_KEYS) * 2
        attempts = 0
        
        while attempts < max_attempts:
            key = Config.get_current_key()
            if not key: break
            
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(Config.MODEL_NAME)
                response = model.generate_content(
                    prompt, 
                    generation_config={"response_mime_type": "application/json"},
                    request_options={"timeout": 20}
                )
                text = response.text.strip()
                if text.startswith("```json"): text = text[7:]
                if text.endswith("```"): text = text[:-3]
                
                data = json.loads(text)

                # [안전장치] 숏폼 모드일 때 SNS 필드 누락 방지 (기존 코드의 안전장치 복원)
                if 'metadata' in data:
                    meta = data['metadata']
                    # 숏폼 필수 필드들이 비어있으면 채워넣기
                    if not meta.get('threads_post'): meta['threads_post'] = meta.get('x_post', '')
                    if not meta.get('x_post'): meta['x_post'] = meta.get('youtube_description', '')[:280]
                    if not meta.get('instagram_post'): meta['instagram_post'] = meta.get('youtube_description', '')
                    if not meta.get('tiktok_post'): meta['tiktok_post'] = meta.get('instagram_post', '')
                
                # 파일 저장
                self.save_metadata_file(data.get('metadata', {}))
                
                return data
            except Exception as e:
                print(f"   ⚠️ Writer Error: {e}")
                Config.rotate_key()
                attempts += 1
                time.sleep(1)
        return None

    def save_metadata_file(self, metadata, folder="results"):
        """
        [UPGRADED] 숏폼(SNS 포함)과 롱폼(기본 정보만)을 모두 완벽하게 저장하는 함수
        """
        os.makedirs(folder, exist_ok=True)
        
        # 1. 공통 정보
        title = metadata.get('youtube_title', metadata.get('title', 'N/A'))
        desc = metadata.get('youtube_description', metadata.get('description', 'N/A'))
        
        content = f"""
============================================================
🎬 VIDEO METADATA
============================================================
[TITLE]
{title}

[DESCRIPTION]
{desc}
"""
        # 2. 숏폼일 경우 (SNS 정보가 있으면 추가)
        if metadata.get('x_post') or metadata.get('instagram_post'):
            content += f"""
            
============================================================
📱 SOCIAL MEDIA POSTS (Shorts Only)
============================================================

[X (Twitter)]
------------------------------------------------------------
{metadata.get('x_post', 'N/A')}
------------------------------------------------------------

[Threads]
------------------------------------------------------------
{metadata.get('threads_post', 'N/A')}
------------------------------------------------------------

[Instagram]
------------------------------------------------------------
{metadata.get('instagram_post', 'N/A')}
------------------------------------------------------------

[TikTok]
------------------------------------------------------------
{metadata.get('tiktok_post', 'N/A')}
------------------------------------------------------------
"""
        
        # 텍스트 파일 저장
        with open(os.path.join(folder, "social_metadata.txt"), "w", encoding="utf-8") as f:
            f.write(content.strip())
            
        # JSON 파일 저장 (자동화용)
        with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
            
        print(f"💾 [Writer] Metadata Saved (Mode detected: {'Shorts/SNS' if 'x_post' in metadata else 'Long-Form'})")