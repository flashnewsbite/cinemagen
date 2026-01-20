import json
import time
import google.generativeai as genai
from config import Config
import os
from datetime import date

class WriterAgent:
    def generate_content(self, context, mode="daily"):
        print("✍️ [Writer] Creating script & metadata (English)...")
        
        # [수정] 날짜 포맷 변경: dd-mm-yyyy
        today_str = date.today().strftime("%d-%m-%Y")

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
        1. **Script Narration**: MUST be in **ENGLISH**.
        2. **Image Prompts**: MUST be in **ENGLISH**.
        3. **Metadata**: MUST be in **ENGLISH**.
        
        [Dynamic Intro/Outro Rules]
        - **Intro**: Be witty, mention "Flash News Bite". Connect with today's date ({today_str}) or specific events. (Max 5 sec)
        - **Outro**: Strong Call to Action (CTA). e.g., "Sub or miss out!" (Max 5 sec)

        [Highlighting Rules]
        - Wrap 1-2 key words per sentence in asterisks (*) for yellow highlighting.
        - Example: "The *AI revolution* is here."

        [Output Format - JSON Only]
        {{
            "title": "Short Video Title",
            "intro_narration": "Witty intro text...",
            "outro_narration": "Punchy CTA text...",
            "script": {{
                "scenes": [
                    {{ "narration": "English narration line...", "image_prompt": "Visual description in English..." }}
                ]
            }},
            "metadata": {{
                "youtube_title": "English Title...",
                "youtube_description": "English Description...",
                "hashtags": "#News #Shorts ...",
                "x_post": "English Post...",
                "instagram_post": "English Post...",
                "tiktok_post": "English Post...",
                "threads_post": "English Post..."
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
                return json.loads(response.text)
            
            except Exception as e:
                err_msg = str(e)
                print(f"   ⚠️ Writer Error: {err_msg}")
                
                if "400" in err_msg or "API_KEY_INVALID" in err_msg:
                    print("   ❌ Invalid API Key. Rotating...")
                    Config.rotate_key()
                elif "limit: 0" in err_msg.lower() or "404" in err_msg or "not found" in err_msg:
                    print("   📉 Model unavailable. Switching to 'gemini-1.5-pro' (Safe Mode).")
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
        """Save metadata to text file"""
        path = os.path.join("results", filename)
        content = f"""
==================================================
📢 YOUTUBE SHORTS OPTIMIZATION (ENGLISH)
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
        print(f"✅ Metadata saved: {path}")