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

    # Gemini Voices (Gemini 2.0 Flash Exp에서 사용 가능)
    GEMINI_VOICES = {
        "male": {"1": "Charon", "2": "Puck", "3": "Fenrir"},
        "female": {"1": "Aoede", "2": "Kore", "3": "Leda"}
    }
    # Edge TTS Voices (백업용)
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
        """
        Gemini 2.0 Flash Audio Generation
        [수정사항] responseMimeType 대신 responseModalities 사용
        """
        max_retries = len(Config.GEMINI_KEYS)
        
        for attempt in range(max_retries):
            key = Config.get_current_key()
            try:
                # API Endpoint
                url = f"https://generativelanguage.googleapis.com/v1beta/{Config.TTS_MODEL_NAME}:generateContent?key={key}"
                
                # [핵심 수정] 오디오 생성 전용 Payload 구조
                payload = {
                    "contents": [{
                        "parts": [{"text": text}]
                    }],
                    "generationConfig": {
                        # 여기가 중요합니다! 오디오 모드로 명시
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": voice_name
                                }
                            }
                        }
                    }
                }
                
                # REST API 요청
                response = requests.post(url, json=payload, timeout=10)
                
                # 쿼터 초과(429) 체크
                if response.status_code == 429:
                    print(f"   ⚠️ Gemini TTS Quota Limit (Key #{Config.current_key_idx+1}) -> Rotating...")
                    Config.rotate_key()
                    continue
                
                if response.status_code != 200:
                    raise Exception(f"API Error {response.status_code}: {response.text}")

                # 오디오 데이터 디코딩
                try:
                    resp_json = response.json()
                    # 응답에서 Base64 오디오 추출
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
                    break # 키 문제가 아니면 반복 중단
        
        return False

    def get_audio(self, data, gender="female", tone="2"):
        gemini_voice = self.GEMINI_VOICES.get(gender).get(tone, "Kore") # Gemini Voice 우선
        edge_voice = self.EDGE_VOICES.get(gender).get(tone, "en-US-JennyNeural")
        
        print(f"🎙️ [Media] Audio Generation Strategy:")
        print(f"   1️⃣ Primary: Gemini 2.0 Flash (Voice: {gemini_voice})")
        print(f"   2️⃣ Backup : Edge TTS (Voice: {edge_voice})")

        intro_txt = data.get('intro_narration', "Welcome.")
        outro_txt = data.get('outro_narration', "Subscribe.")
        scenes = data['script']['scenes']

        async def _run():
            async def generate_final(text, filename):
                # 1. Gemini 시도 (수정된 로직)
                if self.try_gemini_tts(text, filename, gemini_voice):
                    print(f"   ✅ Gemini TTS Success: {filename}")
                    return

                # 2. 실패 시 Edge TTS (백업)
                try:
                    print(f"   ⚠️ Switching to Edge TTS Backup...")
                    communicate = edge_tts.Communicate(text, edge_voice)
                    await communicate.save(filename)
                    print(f"   ✅ Edge TTS Success: {filename}")
                except Exception as e:
                    print(f"   ❌ All TTS Failed: {e}")

            # Intro
            await generate_final(intro_txt, "audio/intro.mp3")
            
            # Scenes
            for i, scene in enumerate(scenes):
                await generate_final(scene['narration'], f"audio/audio_{i+1}.mp3")
                
            # Outro
            await generate_final(outro_txt, "audio/outro.mp3")

        asyncio.run(_run())