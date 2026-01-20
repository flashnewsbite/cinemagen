import json
import time
import google.generativeai as genai
from config import Config
import os

class WriterAgent:
    def generate_content(self, context, mode="daily"):
        print("✍️ [Writer] 대본 및 소셜 메타데이터 작성 중...")
        
        # [디버깅] 실제 로드된 모델 이름 출력 (여기서 1..5가 나오는지 1.5가 나오는지 확인)
        print(f"   🤖 사용 모델: {Config.MODEL_NAME}") 

        topic_instruction = "Summarize today's top 3-4 key news events." if mode == "daily" else "Summarize this specific article."
        
        prompt = f"""
        Role: Expert News Creator & Social Media Manager.
        Task: 
        1. Create a engaging YouTube Shorts script (approx 50-60 seconds).
        2. Create optimized metadata for social media (YouTube, X, IG, TikTok).

        [Input Context]
        {context}

        [Script Requirements]
        - Language: Korean (Narration), English (Image Prompts)
        - Structure: Hook -> Key Point 1 -> Key Point 2 -> Conclusion/CTA.
        - Tone: Professional yet engaging.
        - Scenes: 6-10 scenes.

        [Social Media Output Requirements]
        1. YouTube Title: Catchy, under 100 chars, main keywords.
        2. YouTube Description: Max 2000 chars, Strong Hook + Summary + Call to Action (CTA).
        3. Hashtags: Mix of #Shorts, news keywords, trending tags.
        4. Social Posts (X, IG, TikTok, Threads): Tailored post text with hashtags & emojis.

        [Output Format - JSON Only]
        {{
            "script": {{
                "scenes": [
                    {{ "narration": "Korean text...", "image_prompt": "Visual description..." }}
                ]
            }},
            "metadata": {{
                "youtube_title": "...",
                "youtube_description": "...",
                "hashtags": "#...",
                "x_post": "...",
                "instagram_post": "...",
                "tiktok_post": "...",
                "threads_post": "..."
            }}
        }}
        """

        attempts = 0
        while attempts < len(Config.GEMINI_KEYS) * 2:
            key = Config.get_current_key()
            try:
                genai.configure(api_key=key)
                
                # [핵심] 여기서 Config.MODEL_NAME을 확실하게 사용
                model = genai.GenerativeModel(Config.MODEL_NAME, safety_settings=Config.SAFETY_SETTINGS)
                
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                return json.loads(response.text)
            except Exception as e:
                print(f"   ⚠️ Writer Error: {e}")
                if "429" in str(e) or "RESOURCE" in str(e):
                    Config.rotate_key()
                # 404 모델 에러가 나면 1.0 Pro로 자동 전환 시도
                elif "404" in str(e) or "not found" in str(e):
                    print("   ⚠️ 모델을 찾을 수 없음. 'gemini-pro' (1.0)으로 변경하여 재시도합니다.")
                    Config.MODEL_NAME = "gemini-pro"
                attempts += 1
                time.sleep(2)
        return None

    def save_metadata_file(self, metadata, filename="social_metadata.txt"):
        """결과 폴더에 텍스트 파일 저장"""
        path = os.path.join("results", filename)
        content = f"""
==================================================
📢 YOUTUBE SHORTS OPTIMIZATION
==================================================

[TITLE]
{metadata.get('youtube_title')}

[DESCRIPTION]
{metadata.get('youtube_description')}

[HASHTAGS]
{metadata.get('hashtags')}


==================================================
📱 SOCIAL MEDIA POSTS (Copy & Paste)
==================================================

[X.com / Twitter]
--------------------------------------------------
{metadata.get('x_post')}
--------------------------------------------------

[Instagram]
--------------------------------------------------
{metadata.get('instagram_post')}
--------------------------------------------------

[TikTok]
--------------------------------------------------
{metadata.get('tiktok_post')}
--------------------------------------------------

[Threads]
--------------------------------------------------
{metadata.get('threads_post')}
--------------------------------------------------
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 메타데이터 저장 완료: {path}")