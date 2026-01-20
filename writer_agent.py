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
        
        # 날짜 포맷 (dd:mm:yyyy) - 요청하신 포맷 유지
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

        [⚠️ LANGUAGE RULES - CRITICAL]
        - **ALL Output MUST be in ENGLISH.**

        [⏱️ TIMING & CONTENT RULES]
        1. **Intro**: MAX 3 SECONDS. (e.g., "Flash News: AI takes over!")
        2. **Outro**: MAX 3 SECONDS. (e.g., "Sub for more!")
        3. **Narration**: Fast-paced, concise. Max 2 short sentences per scene.

        [Highlighting Rules]
        - Wrap 1-2 key words per sentence in asterisks (*) for yellow highlighting.

        [Output Format - JSON Only]
        {{
            "title": "Short Video Title",
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
                model = genai.GenerativeModel(Config.MODEL_NAME, safety_settings=Config.SAFETY_SETTINGS)
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                
                # [보완] JSON 파싱 전처리 (마크다운 제거)
                text_response = response.text.strip()
                if text_response.startswith("```json"):
                    text_response = text_response[7:]
                if text_response.endswith("```"):
                    text_response = text_response[:-3]
                
                return json.loads(text_response)
            
            except Exception as e:
                err_msg = str(e)
                print(f"   ⚠️ Writer Error: {err_msg}")
                
                if "400" in err_msg or "API_KEY_INVALID" in err_msg:
                    print("   ❌ Invalid API Key. Rotating...")
                    Config.rotate_key()
                elif "limit: 0" in err_msg.lower() or "404" in err_msg or "not found" in err_msg:
                    print("   📉 Model unavailable. Switching to 'gemini-1.5-pro'.")
                    Config.MODEL_NAME = "models/gemini-1.5-pro"
                elif "429" in err_msg or "quota" in err_msg.lower():
                    print("   ⏳ Quota Exceeded. Rotating key...")
                    Config.rotate_key()
                elif "403" in err_msg:
                     print("   ❌ Key Suspended. Rotating key...")
                     Config.rotate_key()

                attempts += 1
                time.sleep(2)
                
        return None

    def save_metadata_file(self, metadata, filename="social_metadata.txt"):
        """Save metadata in a CLEAN, readable format"""
        path = os.path.join("results", filename)
        
        # 깔끔한 포맷팅 (f-string 사용)
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
            with open(path, "w", encoding="utf-8") as f:
                f.write(content.strip())
            print(f"✅ Metadata saved cleanly: {path}")
        except Exception as e:
            print(f"❌ Failed to save metadata: {e}")