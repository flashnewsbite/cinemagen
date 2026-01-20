import os
import json
import requests
import edge_tts
import asyncio
from PIL import Image
from config import Config
import random
import google.generativeai as genai

class MediaAgent:
    def __init__(self):
        os.makedirs("images", exist_ok=True)
        os.makedirs("audio", exist_ok=True)

    # Voices (Same maps)
    GEMINI_VOICES = {
        "male": {"1": "Charon", "2": "Puck", "3": "Fenrir"},
        "female": {"1": "Aoede", "2": "Kore", "3": "Kore"}
    }
    EDGE_VOICES = {
        "male": {"1": "en-US-ChristopherNeural", "2": "en-US-GuyNeural", "3": "en-US-EricNeural"},
        "female": {"1": "en-US-MichelleNeural", "2": "en-US-JennyNeural", "3": "en-US-AriaNeural"}
    }

    def search_and_download_image(self, query, filename):
        url = "https://google.serper.dev/images"
        payload = json.dumps({"q": query, "num": 5})
        headers = {'X-API-KEY': Config.SERPER_KEY, 'Content-Type': 'application/json'}
        try:
            resp = requests.post(url, headers=headers, data=payload)
            results = resp.json().get("images", [])
            user_agents = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)']
            for item in results:
                try:
                    headers2 = {'User-Agent': random.choice(user_agents), 'Referer': 'https://www.google.com/'}
                    r = requests.get(item['imageUrl'], headers=headers2, timeout=5, stream=True)
                    if r.status_code == 200:
                        with open(filename, 'wb') as f:
                            for chunk in r.iter_content(1024): f.write(chunk)
                        if os.path.getsize(filename) > 5000:
                            with Image.open(filename) as img: img.verify()
                            return True
                except: continue
        except: pass
        return False

    def get_images(self, scenes):
        print(f"🎨 [Media] Downloading Images ({len(scenes)} scenes)")
        for i, scene in enumerate(scenes):
            idx = i + 1
            if self.search_and_download_image(scene['image_prompt'], f"images/image_{idx}.png"):
                print(f"   ✅ Image {idx} Downloaded")
            else:
                Image.new('RGB', (720, 1280), (20,30,60)).save(f"images/image_{idx}.png")

    def try_gemini_tts(self, text, filename, voice_name):
        max_retries = len(Config.GEMINI_KEYS)
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                # Gemini TTS currently doesn't support easy 'rate' adjustment via simple prompt 
                # effectively in the preview API without SSML.
                # Since user wants 1.2x speed, we might prioritize EdgeTTS if speed is critical,
                # OR we instruct Gemini via prompt. Here we fallback to simple generation.
                # (For strict 1.2x speed control, EdgeTTS is more reliable)
                
                # ... Gemini Logic (Simulated) ...
                raise Exception("Force fallback to EdgeTTS for Speed Control (+20%)")
            except Exception as e:
                if "quota" in str(e).lower(): Config.rotate_key()
                else: break 
        return False

    def get_audio(self, data, gender="female", tone="2"):
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        # [속도 설정] 1.2배 빠르게
        tts_rate = "+20%"
        
        print(f"🎙️ [Media] Audio Generation (Speed: 1.2x)")

        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                # Speed control is best with Edge TTS
                try:
                    communicate = edge_tts.Communicate(text, edge_voice, rate=tts_rate)
                    await communicate.save(filename)
                except Exception as e:
                    print(f"   ❌ TTS Failed: {e}")

            await generate_final(intro_txt, "audio/intro.mp3")
            for i, scene in enumerate(scenes):
                await generate_final(scene['narration'], f"audio/audio_{i+1}.mp3")
            await generate_final(outro_txt, "audio/outro.mp3")

        asyncio.run(_run())