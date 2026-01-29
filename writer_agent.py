import json
import time
import google.generativeai as genai
from config import Config
import os
from datetime import date
import re

class WriterAgent:
    def generate_content(self, context, mode="shorts", source_type="news", duration="2-4 minutes"):
        """
        mode: "shorts" or "long"
        source_type: "news" or "topic"
        duration: "2-4 minutes", "6-10 minutes", etc. (Only used for long mode)
        """
        print(f"✍️ [Writer] Generating Script (Mode: {mode.upper()}, Target: {duration})...")
        
        today_str = date.today().strftime("%Y-%m-%d")

        # =================================================================
        # [UPGRADED] LONG-FORM PROMPT (유튜브 롱폼용)
        # =================================================================
        if mode == "long":
            visual_guide = "Use 'image' type for factual events. Use 'video' type for cinematic backgrounds."
            if source_type == "topic":
                visual_guide = "Prioritize 'video' type (Pexels) for storytelling. Use 'image' only for specific data."

            # [핵심 수정] Language: English Only 강제
            prompt = f"""
            Role: Professional YouTube Documentary Creator.
            Date: {today_str}
            Format: Long-form YouTube Video.
            Target Duration: **{duration}** (Strictly Adhere to this length).
            **LANGUAGE: ENGLISH ONLY** (Even if input is Korean/Foreign, output MUST be in English).
            
            Task:
            1. Write a detailed script based on [Input Context].
            2. **Intro Narration**: Start with a strong hook relevant to the topic, then say "Welcome back to the channel."
            3. **Body**: Divide into logical scenes/chapters.
            4. **Outro Narration**: Summarize the key point in 1 sentence, then ask viewers to "Like, Subscribe, and Comment" for more updates.
            5. **Volume**: Ensure the total narration word count is sufficient for a {duration} video.
            6. **Visual Cues**: Decide whether to use a Stock Video ('video') or a News Image ('image') for each scene.

            [Input Context]
            {context}

            [⚠️ VISUAL RULES]
            - {visual_guide}
            - 'visual_prompt': Search query for Pexels(video) or Google(image). English only.

            [Output Format - JSON Only]
            {{
                "title": "YouTube Video Title (MAX 100 CHARACTERS) - ENGLISH",
                "description": "YouTube Description with hashtags... - ENGLISH",
                "intro_narration": "Hook + Welcome message (English)",
                "outro_narration": "Summary + Call to Action (English)",
                "script": {{
                    "scenes": [
                        {{
                            "narration": "Detailed narration text (English)...",
                            "visual_type": "video", 
                            "visual_prompt": "cinematic view of..." 
                        }},
                        ... (Create enough scenes to fill {duration})
                    ]
                }},
                "metadata": {{
                    "tags": ["tag1 (English)", "tag2 (English)"]
                }}
            }}
            """

        # =================================================================
        # [EXISTING] SHORTS PROMPT (기존 숏폼용)
        # =================================================================
        else:
            prompt = f"""
            Role: Expert News Creator & Social Media Manager.
            Date: {today_str}
            **LANGUAGE: ENGLISH ONLY** (Translate input if necessary).
            
            Task: 
            1. Create a YouTube Shorts script based on [Input Context].
            2. Create optimized metadata.
            3. Generate engaging posts for X, Threads, Instagram, and TikTok.

            [Input Context]
            {context}

            [⚠️ TITLE RULES - CRITICAL]
            1. **LENGTH:** STRICTLY UNDER 100 CHARACTERS (Spaces included).
            2. **VIRAL HOOK ONLY.** (e.g., "Apple Buys OpenAI?", "Bitcoin Crashes!")
            3. NO generic words like "News", "Update", "Daily".
            4. **Language:** English.
            
            [⚠️ POST LENGTH RULES - STRICT]
            1. **X (Twitter)**: MAX 280 Characters (including hashtags).
            2. **Threads**: MAX 500 Characters.

            [Highlighting Rules]
            - Wrap 1-2 key words per sentence in asterisks (*) for yellow highlighting.

            [Output Format - JSON Only]
            {{
                "title": "Viral Title (English, UNDER 100 CHARS)",
                "intro_narration": "Intro (English)...",
                "outro_narration": "Outro (English)...",
                "script": {{
                    "scenes": [
                        {{ "narration": "Narration (English)...", "image_prompt": "Visual..." }}
                    ]
                }},
                "metadata": {{
                    "youtube_title": "Viral Title (English)", 
                    "youtube_description": "English...", "hashtags": "English...",
                    "x_post": "English...", "instagram_post": "English...", "tiktok_post": "English...", "threads_post": "English..."
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
                    request_options={"timeout": 60} 
                )
                text = response.text.strip()
                if text.startswith("```json"): text = text[7:]
                if text.endswith("```"): text = text[:-3]
                
                data = json.loads(text)

                if 'metadata' in data:
                    meta = data['metadata']
                    yt_title = meta.get('youtube_title', data.get('title', ''))
                    if len(yt_title) > 100:
                        meta['youtube_title'] = yt_title[:95].strip() + "..."
                        data['title'] = meta['youtube_title']

                    if not meta.get('threads_post'): meta['threads_post'] = meta.get('x_post', meta.get('youtube_description', ''))
                    if not meta.get('x_post'): meta['x_post'] = meta.get('youtube_description', '')
                    if not meta.get('instagram_post'): meta['instagram_post'] = meta.get('youtube_description', '')
                    if not meta.get('tiktok_post'): meta['tiktok_post'] = meta.get('instagram_post', '')

                    if len(meta['x_post']) > 280: meta['x_post'] = meta['x_post'][:277] + "..."
                    if len(meta['threads_post']) > 500: meta['threads_post'] = meta['threads_post'][:497] + "..."
                
                self.save_metadata_file(data.get('metadata', {}))
                
                return data
            except Exception as e:
                print(f"   ⚠️ Writer Error: {e}")
                Config.rotate_key()
                attempts += 1
                time.sleep(1)
        return None

    def save_metadata_file(self, metadata, folder="results"):
        os.makedirs(folder, exist_ok=True)
        
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
        if metadata.get('x_post') or metadata.get('instagram_post'):
            content += f"""
            
============================================================
📱 SOCIAL MEDIA POSTS (Shorts Only)
============================================================

[X (Twitter) - Max 280]
------------------------------------------------------------
{metadata.get('x_post', 'N/A')}
------------------------------------------------------------

[Threads - Max 500]
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
        
        with open(os.path.join(folder, "social_metadata.txt"), "w", encoding="utf-8") as f:
            f.write(content.strip())
            
        with open(os.path.join(folder, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
            
        print(f"💾 [Writer] Metadata Saved (Mode detected: {'Shorts/SNS' if 'x_post' in metadata else 'Long-Form'})")