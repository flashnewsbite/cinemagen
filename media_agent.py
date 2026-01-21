import os
import json
import requests
import edge_tts
import asyncio
from PIL import Image
from config import Config
import random
import base64

class MediaAgent:
    def __init__(self):
        os.makedirs("images", exist_ok=True)
        os.makedirs("audio", exist_ok=True)

    # Gemini Voices (Backup)
    GEMINI_VOICES = {
        "male": {"1": "Charon", "2": "Puck", "3": "Fenrir"},
        "female": {"1": "Aoede", "2": "Kore", "3": "Leda"}
    }
    # Edge TTS Voices (Main)
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

    # [NEW] Edge TTS 함수 분리
    async def try_edge_tts(self, text, filename, voice_name):
        try:
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(filename)
            # 파일이 정상적으로 생성되었는지 확인
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return True
        except Exception as e:
            print(f"   ⚠️ Edge TTS Failed: {e}")
        return False

    def try_gemini_tts(self, text, filename, voice_name):
        """
        Gemini 2.0 Flash Audio Generation (Backup)
        """
        max_retries = len(Config.GEMINI_KEYS)
        
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/{Config.TTS_MODEL_NAME}:generateContent?key={key}"
                
                payload = {
                    "contents": [{"parts": [{"text": text}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": voice_name}
                            }
                        }
                    }
                }
                
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code == 429:
                    print(f"   ⚠️ Gemini TTS Quota Limit (Key #{Config.current_key_idx+1}) -> Rotating...")
                    Config.rotate_key()
                    continue
                
                if response.status_code != 200:
                    raise Exception(f"API Error {response.status_code}: {response.text}")

                try:
                    resp_json = response.json()
                    if 'candidates' in resp_json and resp_json['candidates']:
                        part = resp_json['candidates'][0]['content']['parts'][0]
                        if 'inlineData' in part and 'data' in part['inlineData']:
                            b64_audio = part['inlineData']['data']
                            audio_data = base64.b64decode(b64_audio)
                            with open(filename, "wb") as f:
                                f.write(audio_data)
                            return True
                    raise Exception("No inlineData (audio) found in response")
                except Exception as parse_err:
                    raise Exception(f"Parse Error: {parse_err}")

            except Exception as e:
                print(f"   ⚠️ Gemini TTS Attempt Failed: {e}")
                if "429" in str(e) or "Quota" in str(e):
                    Config.rotate_key()
                else:
                    break 
        
        return False

    def get_audio(self, data, gender="female", tone="2"):
        # 1. 목소리 설정
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore")
        
        print(f"🎙️ [Media] Audio Generation Strategy:")
        print(f"   1️⃣ Primary: Edge TTS (Voice: {edge_voice})")
        print(f"   2️⃣ Backup : Gemini 2.0 Flash (Voice: {gemini_voice})")

        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                # [수정됨] 1순위: Edge TTS 시도
                if await self.try_edge_tts(text, filename, edge_voice):
                    print(f"   ✅ Edge TTS Success: {filename}")
                    return

                # [수정됨] 2순위: 실패 시 Gemini TTS 시도 (백업)
                print(f"   ⚠️ Edge TTS failed. Switching to Gemini Backup...")
                if self.try_gemini_tts(text, filename, gemini_voice):
                    print(f"   ✅ Gemini TTS (Backup) Success: {filename}")
                    return

                print(f"   ❌ All TTS Failed for {filename}")

            # Intro
            await generate_final(intro_txt, "audio/intro.mp3")
            
            # Scenes
            for i, scene in enumerate(scenes):
                await generate_final(scene['narration'], f"audio/audio_{i+1}.mp3")
                
            # Outro
            await generate_final(outro_txt, "audio/outro.mp3")

        asyncio.run(_run())