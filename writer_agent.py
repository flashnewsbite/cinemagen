import json
import time
import google.generativeai as genai
from config import Config
import os
from datetime import date

class WriterAgent:
    def generate_content(self, context, mode="daily"):
        print("✍️ [Writer] Creating script & metadata (English)...")
        today_str = date.today().strftime("%d:%m:%Y")

        prompt = f"""
        Role: Expert News Creator for Fast-Paced Shorts.
        Date: {today_str}
        
        Task: 
        1. Create a YouTube Shorts script based on [Input Context].
        2. Create metadata.
        3. Create Dynamic Intro/Outro.

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
            "title": "Short Title",
            "intro_narration": "Very short intro...",
            "outro_narration": "Very short outro...",
            "script": {{
                "scenes": [
                    {{ 
                        "narration": "Narration text here...", 
                        "image_prompt": "Visual description..." 
                    }}
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
                return json.loads(response.text)
            
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
        path = os.path.join("results", filename)
        with open(path, "w", encoding="utf-8") as f: f.write(str(metadata))
        print(f"✅ Metadata saved: {path}")