import json
import time
import google.generativeai as genai
from config import Config
import os
from datetime import date
import re

class WriterAgent:
    def generate_content(self, context, mode="daily"):
        print("✍️ [Writer] Creating script & metadata (English)...")
        
        today_str = date.today().strftime("%d:%m:%Y")

        prompt = f"""
        Role: Expert News Creator & Social Media Manager for a Global Audience.
        Date: {today_str}
        
        Task: 
        1. Create a YouTube Shorts script based on [Input Context].
        2. Create optimized metadata.
        3. Create Dynamic Intro/Outro Narrations.

        [Input Context]
        {context}

        [⚠️ TITLE RULES - CRITICAL]
        1. **VIRAL HOOK ONLY:** The title MUST be specific and shocking. (e.g., "Apple Buys OpenAI?", "Bitcoin Crashes!", "New AI King?")
        2. **NO GENERIC WORDS:** STRICTLY FORBIDDEN to use: "News", "Update", "Digest", "Daily", "Flash", "Report", "Summaries".
        3. **NO CHANNEL NAME:** Do not include "Flash News Bite" or any branding.
        4. **NO DATES:** Do not include the date (e.g., -01-22).
        5. **LENGTH:** MAX 6-8 Words. Short & Punchy.

        [⚠️ LANGUAGE RULES]
        - **ALL Output MUST be in ENGLISH.**

        [⏱️ TIMING & CONTENT RULES]
        1. **Intro**: MAX 3 SECONDS. (e.g., "You won't believe this.")
        2. **Outro**: MAX 3 SECONDS. (e.g., "Subscribe for more.")
        3. **Narration**: Fast-paced, concise. Max 2 short sentences per scene.

        [Highlighting Rules]
        - Wrap 1-2 key words per sentence in asterisks (*) for yellow highlighting.

        [Output Format - JSON Only]
        {{
            "title": "Specific & Viral Title (e.g. Apple & Google Merger?)",
            "intro_narration": "Very short intro...",
            "outro_narration": "Very short outro...",
            "script": {{
                "scenes": [
                    {{ "narration": "Narration text...", "image_prompt": "Visual description..." }}
                ]
            }},
            "metadata": {{
                "youtube_title": "...", "youtube_description": "...", "hashtags": "...",
                "x_post": "...", "instagram_post": "...", "tiktok_post": "...", "threads_post": "..."
            }}
        }}
        """

        max_attempts = len(Config.GEMINI_KEYS) * 2
        attempts = 0
        
        while attempts < max_attempts:
            key = Config.get_current_key()
            if not key:
                print("❌ No valid API keys available.")
                break

            print(f"   🤖 Try #{attempts+1} | Model: {Config.MODEL_NAME} | Key: ...{key[-4:]}")
            
            try:
                genai.configure(api_key=key)
                # 안전 설정이 Config에 없다면 기본값 사용 (코드 호환성 유지)
                safety = getattr(Config, 'SAFETY_SETTINGS', None)
                model = genai.GenerativeModel(Config.MODEL_NAME, safety_settings=safety)
                
                # [타임아웃 설정] 15초 내 응답 없으면 재시도
                response = model.generate_content(
                    prompt, 
                    generation_config={"response_mime_type": "application/json"},
                    request_options={"timeout": 15} 
                )
                
                text_response = response.text.strip()
                # Markdown 코드 블록 제거
                if text_response.startswith("```json"):
                    text_response = text_response[7:]
                if text_response.endswith("```"):
                    text_response = text_response[:-3]
                
                data = json.loads(text_response)
                
                # 성공 시 메타데이터 저장 (JSON + TXT)
                if 'metadata' in data:
                    self.save_metadata_file(data['metadata'])
                
                return data
            
            except Exception as e:
                err_msg = str(e)
                print(f"   ⚠️ Writer Error: {err_msg}")
                
                # 에러 유형별 키 로테이션 처리
                if any(x in err_msg for x in ["400", "API_KEY_INVALID", "403"]):
                    print("   ❌ Invalid/Suspended API Key. Rotating...")
                    Config.rotate_key()
                elif any(x in err_msg.lower() for x in ["limit: 0", "429", "quota", "resourceexhausted"]):
                    print("   ⏳ Quota Exceeded. Rotating key...")
                    Config.rotate_key()
                elif "deadline" in err_msg.lower() or "timeout" in err_msg.lower():
                     print("   ⏰ Timeout. Google server is slow. Rotating key & Retrying...")
                     Config.rotate_key()
                elif "not found" in err_msg.lower() or "404" in err_msg:
                    print("   📉 Model unavailable. Switching to 'gemini-1.5-pro'.")
                    Config.MODEL_NAME = "models/gemini-1.5-pro"
                else:
                    # 알 수 없는 에러라도 일단 키를 바꿔서 재시도하는 것이 안전함
                    print("   ⚠️ Unknown error. Rotating key just in case...")
                    Config.rotate_key()

                attempts += 1
                time.sleep(2)
                
        return None

    def save_metadata_file(self, metadata, folder="results"):
        """
        Saves metadata in two formats:
        1. metadata.json (For Automation Bot)
        2. social_metadata.txt (For Human Review)
        """
        os.makedirs(folder, exist_ok=True)

        # [1] 기계용 JSON 저장 (봇이 읽을 파일)
        json_path = os.path.join(folder, "metadata.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Failed to save JSON metadata: {e}")

        # [2] 사람용 TXT 저장 (눈으로 확인용)
        txt_path = os.path.join(folder, "social_metadata.txt")
        content = f"""
============================================================
🎬 YOUTUBE SHORTS METADATA
============================================================

[TITLE]
{metadata.get('youtube_title', 'N/A')}

[DESCRIPTION]
{metadata.get('youtube_description', 'N/A')}

[HASHTAGS]
{metadata.get('hashtags', 'N/A')}


============================================================
📱 SOCIAL MEDIA POSTS (Copy & Paste)
============================================================

[X (Twitter)]
------------------------------------------------------------
{metadata.get('x_post', 'N/A')}
------------------------------------------------------------

[Instagram]
------------------------------------------------------------
{metadata.get('instagram_post', 'N/A')}
------------------------------------------------------------

[TikTok]
------------------------------------------------------------
{metadata.get('tiktok_post', 'N/A')}
------------------------------------------------------------

[Threads]
------------------------------------------------------------
{metadata.get('threads_post', 'N/A')}
------------------------------------------------------------
"""
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(content.strip())
            print(f"💾 [Writer] Metadata saved: {json_path} & {txt_path}")
        except Exception as e:
            print(f"❌ Failed to save TXT metadata: {e}")